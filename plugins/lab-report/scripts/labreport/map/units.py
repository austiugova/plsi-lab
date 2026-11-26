"""Unit scaling into a coordinate's canonical unit: identity, a sourced map conversion, or a generic UCUM
prefix/volume scale (mg/dL -> g/L, 10*3/uL -> 10*9/L). Spellings are compared after `normalize_unit`. Never a
conversion between kinds of quantity without a sourced factor."""

from __future__ import annotations

import re
from typing import Any

from labreport.life.normalize import UNIT_BASES, UNIT_PREFIXES, normalize_unit as normalize
from labreport.map.models import Conversion, MapCoordinate


_SUPER = str.maketrans("0123456789", "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079")


def display(unit: str | None) -> str:
    """A UCUM unit as people read it: mm[Hg] -> mmHg, 10*9/L -> \u00d710\u2079/L, umol/L -> \u00b5mol/L, m[IU]/L -> mIU/L."""
    if not unit:
        return ""
    u = re.sub(r"10\*(\d+)", lambda m: "\u00d710" + m[1].translate(_SUPER), unit)
    u = re.sub(r"(?<![A-Za-z])u(?=g|L|mol|\[IU\]|kat)", "\u00b5", u)
    return u.replace("[Hg]", "Hg").replace("[IU]", "IU").replace("{", "").replace("}", "").replace("_", " ")


KAT_IN_U = 6e7  # enzyme activity: 1 kat = 1 mol/s = 6e7 umol/min = 6e7 U, by definition (SI)
# time in seconds, by definition (UCUM: mo and a are the mean Julian month and year)
TIME = {"ms": 1e-3, "s": 1.0, "min": 60.0, "h": 3600.0, "d": 86400.0, "wk": 604800.0, "mo": 2629800.0, "a": 31557600.0}


def _sig(x: float) -> float:
    return float(f"{x:.12g}")


def _term(t: str) -> tuple[str, float] | None:
    """One side of a UCUM unit -> (base, scale): mg -> (g, 1e-3), 10*3 -> (#, 1e3), % -> ('', 0.01), ukat -> (U, 60)."""
    if m := re.fullmatch(r"10\*(\d+)", t):
        return "#", 10.0 ** int(m.group(1))
    if t in ("", "1", "%"):
        return "", 0.01 if t == "%" else 1.0
    if t in TIME:
        return "time", TIME[t]
    for base in UNIT_BASES:
        if t.endswith(base) and t[: -len(base)] in UNIT_PREFIXES:
            scale = UNIT_PREFIXES[t[: -len(base)]]
            return ("U", scale * KAT_IN_U) if base == "kat" else (base, scale)
    return None


def _scale(unit: str) -> tuple[tuple[str, str], float] | None:
    num, _, den = unit.partition("/")
    a, b = _term(num), _term(den) if den else ("", 1.0)
    if num == "" and b and b[0] == "L":  # "/uL" counts per volume, as "10*3/uL" does
        a = ("#", 1.0)
    return ((a[0], b[0]), a[1] / b[1]) if a and b and "/" not in den else None


def _same(a: str | None, b: str | None) -> bool:
    """One unit in two spellings: equal after `normalize`, or with the same denominators in another order
    (mL/kg/min = mL/min/kg); a unit in braces is compared as written."""
    if a is None or b is None:
        return a == b
    if a == b:
        return True
    if "{" in a + b:
        return False
    (na, *da), (nb, *db) = a.split("/"), b.split("/")
    return na == nb and sorted(da) == sorted(db)


def _apply(value: float, conv: Conversion, unit: str | None) -> tuple[float, dict[str, Any]]:
    out = {"from_unit": unit, "factor": conv.factor, **({"offset": conv.offset} if conv.offset else {})}
    return _sig(value * conv.factor + conv.offset), out


def to_canonical(value: float, unit: str | None, c: MapCoordinate) -> tuple[float, dict[str, Any] | None]:
    """value in `unit` -> the coordinate's canonical unit, comparing spellings after `normalize`: identity, a sourced
    conversion (scale, or scale and offset), a sourced scale with a prefix shift (umol/L through a sourced mmol/L), or
    a generic UCUM scale. A value with no unit counts only on a unitless coordinate (`1`) or through a sourced
    conversion from "". ValueError otherwise."""
    if unit == c.unit:
        return value, None
    given, canonical = normalize(unit), normalize(c.unit)
    if given is None:
        if canonical == "1":
            return value, {"from_unit": None, "factor": 1.0, "spelling": "1"}
        for conv in c.conversions:
            if normalize(conv.from_unit) is None:
                return _apply(value, conv, None)
        raise ValueError(f"no unit reported (canonical {c.unit})")
    if _same(given, canonical):
        return value, {"from_unit": unit, "factor": 1.0, "spelling": canonical}
    for conv in c.conversions:
        if _same(normalize(conv.from_unit), given):
            return _apply(value, conv, unit)
    a = _scale(given)
    for conv in c.conversions:
        b = _scale(source) if (source := normalize(conv.from_unit)) else None  # "" is only for a value with no unit
        if a and b and a[0] == b[0] and not conv.offset:
            factor = _sig(a[1] / b[1] * conv.factor)
            return _sig(value * factor), {"from_unit": unit, "factor": factor, "via": conv.from_unit}
    b = _scale(canonical) if canonical else None
    if a and b and a[0] == b[0]:
        factor = _sig(a[1] / b[1])
        return _sig(value * factor), {"from_unit": unit, "factor": factor}
    raise ValueError(f"cannot convert {unit} to {c.unit} (no generic scale or sourced conversion)")


# one-character slips OCR and typing make in a unit; a reading is only ever offered, never applied by code
_SLIPS = (("1", "l"), ("I", "l"), ("|", "l"), ("0", "o"), ("rn", "m"))


