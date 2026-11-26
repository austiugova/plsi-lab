"""The record vocabulary: events and observations, their codes and origins, the person's own facts, and the
map coordinates and comparisons derived from them."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["EventType", "ObservationKind", "ClinicalStatus", "CodeSystem", "Sex", "Ethnicity", "CoordinateKind", "ValueStatus", "Comparator", "DeriveEngine", "MatchKind", "Direction"]


class EventType(StrEnum):
    OBSERVATION = "observation"
    RETRACTION = "retraction"
    SCREENING = "screening"
    PLAN = "plan"
    PLAN_STATUS = "plan_status"
    PREDICTION_SCORE = "prediction_score"


class ObservationKind(StrEnum):
    MEASUREMENT = "measurement"
    MEDICATION = "medication"
    CONDITION = "condition"
    ALLERGY = "allergy"
    INTERVENTION = "intervention"
    SYMPTOM = "symptom"
    LIFESTYLE = "lifestyle"
    ARTIFACT = "artifact"
    NOTE = "note"
    GOAL = "goal"  # what the user wants to reach, e.g. "run 10 km"; resolved when reached or dropped
    PREFERENCE = "preference"  # standing choices and constraints: diet, budget band, schedule


class ClinicalStatus(StrEnum):
    ACTIVE = "active"
    STOPPED = "stopped"
    RESOLVED = "resolved"
    UNKNOWN = "unknown"


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


class Ethnicity(StrEnum):
    EUROPEAN = "european"
    AFRICAN = "african"
    MIDDLE_EASTERN = "middle_eastern"
    SOUTH_ASIAN = "south_asian"
    EAST_ASIAN = "east_asian"
    SOUTHEAST_ASIAN = "southeast_asian"
    LATIN_AMERICAN = "latin_american"
    OTHER = "other"


class CoordinateKind(StrEnum):
    MEASURED = "measured"
    DERIVED = "derived"
    SET = "set"


class ValueStatus(StrEnum):
    PRESENT = "present"
    STALE = "stale"
    MISSING = "missing"
    ERROR = "error"


class Comparator(StrEnum):
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="


class DeriveEngine(StrEnum):
    NATIVE = "native"  # built-in formulas (plsi.map.derive)
    EXPR = "expr"  # a safe formula written in the map (plsi.map.formula)
    EXTENSION = "extension"  # an installed deriver extension (plsi.extensions); model = extension id
    BIOLEARN = "biolearn"


class MatchKind(StrEnum):
    CODE = "code"
    DERIVED = "derived"


class Direction(StrEnum):
    UP = "up"
    DOWN = "down"
    NONE = "none"


