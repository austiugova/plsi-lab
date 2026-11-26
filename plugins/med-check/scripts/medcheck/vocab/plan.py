"""The plan vocabulary: action categories, plan states and decisions, and the policy gates and skill-lint rules."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["ActionCategory", "PlanState", "CLOSED_PLAN_STATES", "PlanDecision"]


class ActionCategory(StrEnum):
    DRUG = "drug"
    SUPPLEMENT = "supplement"
    DIET = "diet"
    EXERCISE = "exercise"
    SLEEP = "sleep"
    TEST = "test"
    OTHER = "other"


class PlanState(StrEnum):
    PROPOSED = "proposed"
    ADOPTED = "adopted"
    COMPLETED = "completed"
    STOPPED = "stopped"
    SUPERSEDED = "superseded"


CLOSED_PLAN_STATES = frozenset({PlanState.STOPPED, PlanState.SUPERSEDED})  # no longer live: past, never charted


class PlanDecision(StrEnum):
    ADOPT = "adopt"
    CONTINUE = "continue"
    MODIFY = "modify"
    STOP = "stop"
    COMPLETE = "complete"


