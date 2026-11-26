"""Features that run in PLSI; the journal keeps their records as written."""

from __future__ import annotations

from labjournal.errors import ValidationError

SITE = "https://longevitygrok.si/"


def note(feature: str) -> str:
    return f"{feature} runs in PLSI, and your journal moves over with you: {SITE}"


def block(feature: str) -> dict:
    return {"in_plsi": note(feature)}


def bank() -> dict:
    raise ValidationError(note("The cell bank"), code="IN_PLSI", hint=SITE)
