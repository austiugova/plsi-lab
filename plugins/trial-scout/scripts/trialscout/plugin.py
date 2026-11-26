"""Trial Scout commands: recruiting studies from ClinicalTrials.gov, with age and sex checked against eligibility."""

from __future__ import annotations

import re
from typing import Any

from trialscout import errors
from trialscout.cmdspec import A, Cmd
from trialscout.models import CAP_ABSTRACT, CAP_LABEL, external_str
from trialscout.policy import ctgov

SITE = "https://longevitygrok.si/"
OPEN = "RECRUITING,NOT_YET_RECRUITING"
MATCH = f"Matching trials to your own record, and alerts when new ones open, run in PLSI: {SITE}"
UNITS = {"year": 1.0, "month": 1 / 12, "week": 1 / 52.18, "day": 1 / 365.25}


def _years(text: str | None) -> float | None:
    """'18 Years', '6 Months' -> years; None when the registry gives no limit."""
    m = re.match(r"\s*(\d+(?:\.\d+)?)\s*(year|month|week|day)", (text or "").lower())
    return float(m.group(1)) * UNITS[m.group(2)] if m else None


def _eligibility(raw: dict[str, Any]) -> dict[str, Any]:
    e = (raw.get("protocolSection") or {}).get("eligibilityModule") or {}
    return {"min_age": external_str(e.get("minimumAge")) or None, "max_age": external_str(e.get("maximumAge")) or None,
            "sex": external_str(e.get("sex")) or "ALL", "healthy_volunteers": e.get("healthyVolunteers")}


def _fit(el: dict[str, Any], age: float | None, sex: str | None) -> dict[str, str]:
    """Age and sex against the registry's limits: meets, fails or unknown (never guessed)."""
    out = {}
    if age is not None:
        low, high = _years(el["min_age"]), _years(el["max_age"])
        out["age"] = "fails" if (low is not None and age < low) or (high is not None and age > high) else "meets"
    if sex:
        allowed = el["sex"].upper()
        out["sex"] = "unknown" if sex == "X" else "meets" if allowed in ("ALL", "") or allowed[0] == sex else "fails"
    return out


def _sites(raw: dict[str, Any], near: str | None, limit: int = 5) -> list[dict[str, Any]]:
    locs = ((raw.get("protocolSection") or {}).get("contactsLocationsModule") or {}).get("locations") or []
    rows = [{"facility": external_str(x.get("facility")), "city": external_str(x.get("city")),
             "country": external_str(x.get("country")), "status": external_str(x.get("status")) or None} for x in locs]
    if near:
        words = {w for w in re.split(r"[^a-z]+", near.lower()) if len(w) > 2}
        rows.sort(key=lambda r: -len(words & set(re.split(r"[^a-z]+", f"{r['city']} {r['country']}".lower()))))
    return rows[:limit]


def _link(nct: str) -> str:
    return f"https://clinicaltrials.gov/study/{nct}"


def search(condition: str, term: str | None = None, location: str | None = None, status: str = OPEN,
           age: float | None = None, sex: str | None = None, limit: int = 15) -> dict[str, Any]:
    """`search --condition ...`: studies in the registry's own words, each with its age and sex fit."""
    params = {"query.cond": condition, "filter.overallStatus": status, "pageSize": max(1, min(limit, 50)),
              "countTotal": "true"}
    if term:
        params["query.term"] = term
    if location:
        params["query.locn"] = location
    reply = ctgov.studies(params)
    rows = []
    for raw in reply.get("studies", []):
        study = ctgov.record(raw)
        el = _eligibility(raw)
        rows.append({**{k: study[k] for k in ("nct", "title", "status", "phases", "conditions", "sponsor", "enrollment")},
                     "interventions": [i["name"] for i in study["interventions"]], "eligibility": el,
                     "fit": _fit(el, age, sex), "sites": _sites(raw, location, 3), "link": _link(study["nct"])})
    kept = [r for r in rows if "fails" not in r["fit"].values()]
    return {"total": reply.get("totalCount"), "shown": len(kept), "dropped_by_fit": len(rows) - len(kept),
            "studies": kept, "in_plsi": MATCH}


def show(nct: str) -> dict[str, Any]:
    """`show --nct NCT...`: one study with its full eligibility text, sites and contacts as the registry gives them."""
    if not re.fullmatch(r"NCT\d{8}", nct.strip().upper()):
        raise errors.ValidationError(f"{nct!r} is not an NCT id", code="NCT_ID", hint="NCT followed by 8 digits")
    raw = ctgov.study(nct.strip().upper(), "protocolSection,hasResults")
    if not raw:
        raise errors.NotFound(f"{nct} is not in ClinicalTrials.gov", code="NCT_NOT_FOUND")
    study = ctgov.record(raw)
    section = raw.get("protocolSection") or {}
    el = section.get("eligibilityModule") or {}
    contacts = (section.get("contactsLocationsModule") or {}).get("centralContacts") or []
    return {**study, "summary": external_str((section.get("descriptionModule") or {}).get("briefSummary"), CAP_ABSTRACT),
            "eligibility": {**_eligibility(raw), "criteria": external_str(el.get("eligibilityCriteria"), CAP_LABEL)},
            "sites": _sites(raw, None, 50),
            "contacts": [{"name": external_str(c.get("name")), "role": external_str(c.get("role")),
                          "phone": external_str(c.get("phone")), "email": external_str(c.get("email"))} for c in contacts],
            "link": _link(study["nct"])}


COMMANDS: dict[str, Cmd] = {
    "search": Cmd("trialscout.plugin:search",
                  (A("--condition", required=True, help="the condition or topic, e.g. 'type 2 diabetes'"),
                   A("--term", help="more words: a marker, an outcome, 'healthy volunteers'"),
                   A("--location", help="city, region or country to search near"),
                   A("--status", default=OPEN, help=f"registry statuses, comma-separated (default {OPEN})"),
                   A("--age", type=float, help="the person's age in years: studies whose limits exclude it are left out"),
                   A("--sex", choices=["F", "M", "X"], help="F, M or X: studies limited to the other sex are left out"),
                   A("--limit", type=int, default=15, help="studies to fetch (max 50)")),
                  "recruiting studies for a condition, with age and sex checked", ("show --nct <NCT id>",)),
    "show": Cmd("trialscout.plugin:show", (A("--nct", required=True, help="NCT id"),),
                "one study: eligibility criteria, sites, contacts, registry link"),
}
