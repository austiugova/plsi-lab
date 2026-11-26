"""The record vocabulary: events and observations, their codes and origins, the person's own facts, and the
map coordinates and comparisons derived from them."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["CodeSystem", "Sex"]


class CodeSystem(StrEnum):
    LOINC = "loinc"
    RXNORM = "rxnorm"
    SNOMED = "snomed"
    ICD10CM = "icd10cm"
    CPG = "cpg"
    FREE = "free"


class Sex(StrEnum):
    M = "M"
    F = "F"
    X = "X"
    UNKNOWN = "unknown"


