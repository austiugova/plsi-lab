"""Proactive blocking screening: each drug or supplement action against its openFDA label (ingredient via plsi.rxnav),
in the care context of plsi.map.mapper.context()."""

from __future__ import annotations

import re
from typing import Any

from pydantic import RootModel

from medcheck import rxnav
from medcheck.models import CAP_LABEL, SourceRef, sanitize_external
from medcheck.policy.evidence import cite_url, label_query, label_title
from medcheck.policy.models import ActionInput, Finding
from medcheck.vocab import ActionCategory, Severity, SourceKind

SCREEN_MAX_AGE_DAYS = 7
LABEL_SECTIONS = (
    "boxed_warning", "contraindications", "warnings_and_cautions", "warnings",
    "precautions", "drug_interactions", "use_in_specific_populations",
)
SCREENED = (ActionCategory.DRUG, ActionCategory.SUPPLEMENT)
NO_LABEL_SUPPLEMENT = "no regulatory label; Grok must cite literature and the user must acknowledge"
EXCERPT_RADIUS = 300  # characters of label text kept on each side of a hit
AddedFindings = RootModel[dict[str, list[Finding]]]


def _ingredient(action: ActionInput) -> str | None:
    """RxNorm ingredient name: the action's code, else RxNav approximateTerm -> related IN/PIN."""
    if action.code and action.code.display:
        return action.code.display
    rxcui = action.code.code if action.code else next(iter(rxnav.candidates(action.description, min_score=None)), None)
    if rxcui is None:
        return None
    found = rxnav.ingredients(rxcui)
    return next((p["name"] for p in found.get("IN") or found.get("PIN") or []), None)


def _label(name: str) -> dict[str, Any] | None:
    """Newest openFDA label by substance_name.exact, then generic_name.exact (uppercase); a label without a set_id
    cannot be cited and is skipped."""
    for field in ("substance_name", "generic_name"):
        found = label_query(f'openfda.{field}.exact:"{name.upper()}"', 5, sort="effective_time:desc").get("results") or []
        if results := [r for r in found if r.get("set_id")]:
            return max(results, key=lambda r: str(r.get("effective_time", "")))
    return None


def _label_findings(label: dict[str, Any], terms: list[str]) -> list[Finding]:
    set_id = label["set_id"]
    src = SourceRef(kind=SourceKind.LABEL, id=set_id, title=label_title(label), url=cite_url(SourceKind.LABEL, set_id))
    findings = []
    for section in LABEL_SECTIONS:
        text = "\n".join(label.get(section) or [])
        if not text:
            continue
        if section == "boxed_warning":
            findings.append(Finding(severity=Severity.CAUTION, summary="label has a boxed warning", source=src,
                                    excerpt=sanitize_external(text, CAP_LABEL, f"openfda:{section}")))
        for term in terms:
            if hit := re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE):
                start = max(0, hit.start() - EXCERPT_RADIUS)
                severity = Severity.BLOCK if section == "contraindications" else Severity.CAUTION
                findings.append(Finding(severity=severity, summary=f"{section} mentions {term!r}", source=src,
                                        excerpt=sanitize_external(text[start:hit.end() + EXCERPT_RADIUS], CAP_LABEL, f"openfda:{section}")))
    return findings


