"""Safe formulas for derived coordinates (`derive: {engine: expr, formula: ...}`).

A formula is one arithmetic expression over the coordinate's inputs plus the context variables `age` (years at the
draw), `female` and `male` (1 or 0). Allowed: numbers, + - * / **, unary -, comparisons, and the functions below.
The expression is parsed with `ast` and walked here; nothing is ever passed to eval/exec.
"""

from __future__ import annotations

import ast
import math
import operator
from collections.abc import Callable
from functools import lru_cache
from typing import Any

MAX_LENGTH = 500
CONTEXT = frozenset({"age", "female", "male"})
FUNCTIONS: dict[str, Callable[..., Any]] = {
    "log": math.log, "ln": math.log, "log10": math.log10, "exp": math.exp, "sqrt": math.sqrt,
    "abs": abs, "min": min, "max": max, "where": lambda cond, a, b: a if cond else b,
}
NON_MONOTONE = frozenset({"abs", "min", "max", "where"})  # with comparisons: a censored input cannot be bounded
_BINARY: dict[type, Callable[[Any, Any], Any]] = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow}
_COMPARE: dict[type, Callable[[Any, Any], bool]] = {ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge, ast.Eq: operator.eq, ast.NotEq: operator.ne}


@lru_cache(maxsize=256)
def parse(formula: str) -> ast.expr:
    """Parse and check a formula; raises ValueError naming the first disallowed construct."""
    if len(formula) > MAX_LENGTH:
        raise ValueError(f"formula longer than {MAX_LENGTH} characters")
    try:
        tree = ast.parse(formula, mode="eval").body
    except SyntaxError as exc:
        raise ValueError(f"formula is not a valid expression: {exc.msg}") from None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS or node.keywords:
                raise ValueError(f"only these functions are allowed: {', '.join(sorted(FUNCTIONS))}")
        elif isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)) or isinstance(node.value, bool):
                raise ValueError("only numeric constants are allowed")
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in _BINARY:
                raise ValueError(f"operator {type(node.op).__name__} is not allowed")
        elif isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, (ast.USub, ast.UAdd)):
                raise ValueError(f"operator {type(node.op).__name__} is not allowed")
        elif isinstance(node, ast.Compare):
            if any(type(op) not in _COMPARE for op in node.ops):
                raise ValueError("only <, <=, >, >=, ==, != comparisons are allowed")
        elif not isinstance(node, (ast.Name, ast.Load, *_BINARY, *_COMPARE, ast.USub, ast.UAdd)):
            raise ValueError(f"{type(node).__name__} is not allowed in a formula")
    return tree


def variables(formula: str) -> set[str]:
    """Names the formula reads, excluding function names."""
    tree = parse(formula)
    called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call)}  # type: ignore[union-attr]
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} - called


def _walk(node: ast.expr, env: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return float(node.value)  # float powers overflow (OverflowError) instead of growing big integers
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise ValueError(f"unknown variable {node.id!r}")
        return env[node.id]
    if isinstance(node, ast.UnaryOp):
        return -_walk(node.operand, env) if isinstance(node.op, ast.USub) else _walk(node.operand, env)
    if isinstance(node, ast.BinOp):
        return _BINARY[type(node.op)](_walk(node.left, env), _walk(node.right, env))
    if isinstance(node, ast.Compare):
        left, ok = _walk(node.left, env), True
        for op, right_node in zip(node.ops, node.comparators, strict=True):
            right = _walk(right_node, env)
            ok = ok and _COMPARE[type(op)](left, right)
            left = right
        return ok
    if isinstance(node, ast.Call):
        return FUNCTIONS[node.func.id](*(_walk(a, env) for a in node.args))  # type: ignore[union-attr]
    raise ValueError(f"{type(node).__name__} is not allowed in a formula")


