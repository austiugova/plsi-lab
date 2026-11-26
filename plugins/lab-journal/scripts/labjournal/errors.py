"""Error types (CLI exit codes), gate violations, and warnings collected into the CLI envelope."""

from __future__ import annotations


class JournalError(Exception):
    """Base error. `code` goes into the envelope; `exit_code` 1 = refused, 2 = usage, 3 = environment."""

    code = "ERROR"
    exit_code = 1

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        hint: str | None = None,
        violations: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or type(self).code
        self.hint = hint
        self.violations = violations


class ValidationError(JournalError):
    code = "VALIDATION_ERROR"


class NotFound(JournalError):
    code = "NOT_FOUND"


class UsageError(JournalError):
    code = "USAGE"
    exit_code = 2


class EnvironmentProblem(JournalError):
    exit_code = 3


CLOCKS_EXTRA = "plsi clocks install"  # the clocks extra's packages only (biolearn, pandas), never plsi itself


class InstanceLocked(EnvironmentProblem):
    code = "INSTANCE_LOCKED"


def violation(path: str, rule: str, message: str, hint: str = "") -> dict[str, str]:
    return {"path": path, "rule": rule, "message": message, "hint": hint}


_WARNINGS: list[dict[str, str]] = []


def warn(code: str, message: str) -> None:
    _WARNINGS.append({"code": code, "message": message})


def drain_warnings() -> list[dict[str, str]]:
    out = list(_WARNINGS)
    _WARNINGS.clear()
    return out
