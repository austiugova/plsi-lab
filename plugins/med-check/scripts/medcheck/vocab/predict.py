"""The prediction vocabulary: what a prediction targets, how a score turned out, and when one comes due."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["PredictionTarget", "ScoreStatus"]


class PredictionTarget(StrEnum):
    LEVEL = "level"
    CHANGE_FROM_BASELINE = "change_from_baseline"


class ScoreStatus(StrEnum):
    SCORED = "scored"
    MISSED = "missed"
    VOID = "void"


