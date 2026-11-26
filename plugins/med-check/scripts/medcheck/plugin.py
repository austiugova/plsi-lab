"""Med & Supplement Check commands: FDA label warnings that name the person's other items, quoted with the label link."""

from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any

from medcheck import errors
from medcheck.cmdspec import FILE, Cmd
from medcheck.files import load_json
from medcheck.policy import screen

SITE = "https://longevitygrok.si/"
PLAN = f"Checking a whole plan before any change (the Forecaster), against your full record, runs in PLSI: {SITE}"
NO_LABEL = {"supplement": "no FDA label: supplements are not FDA-labelled, so check this one with your pharmacist or clinician",
            "drug": "no FDA label found for this name: check the spelling or the active ingredient"}


def _variants(word: str) -> set[str]:
    """A name as labels may spell it: without a trailing 'extract', 'St.' with and without the full stop."""
    w = re.sub(r"\s+extract$", "", word.lower().strip()).replace("’", "'")
    out = {w, re.sub(r"\bst\.\s*", "st ", w), re.sub(r"\bst\s+", "st. ", w)}
    return out | {v.replace("'", "’") for v in out}


def _terms(items: list[dict[str, Any]], context: list[str]) -> dict[int, list[str]]:
    """For each item, the words to look for in its label: every other item (name and ingredient) and the context."""
    words = [set().union(*(_variants(w) for w in (i["name"], i.get("ingredient")) if w)) for i in items]
    ctx = {c.lower().strip() for c in context}
    if any(i["kind"] == "supplement" for i in items):
        ctx |= {"botanical", "herbal"}  # labels warn about herbal products as a group
    return {n: sorted(t for t in set().union(*(w for m, w in enumerate(words) if m != n), ctx) if len(t) >= 3)
            for n in range(len(items))}


def _finding(f: Any) -> dict[str, Any]:
    return {"severity": f.severity.value, "summary": f.summary, "excerpt": f.excerpt.text if f.excerpt else None}


def check(file: str) -> dict[str, Any]:
    """`check --file items.json`: {items: [{name, kind: drug|supplement}], conditions: [...], allergies: [...]}."""
    doc = load_json(file)
    items = doc.get("items") if isinstance(doc, dict) else None
    if not isinstance(items, list) or not items or not all(isinstance(i, dict) and i.get("name") for i in items):
        raise errors.ValidationError("give a list of items with a name each", code="CHECK_INPUT",
                                     hint='{"items": [{"name": "warfarin", "kind": "drug"}, {"name": "fish oil", "kind": "supplement"}]}')
    for i in items:
        i["kind"] = "supplement" if str(i.get("kind", "drug")).lower() == "supplement" else "drug"
        i["ingredient"] = screen._ingredient(SimpleNamespace(code=None, description=i["name"]))
    context = [*doc.get("conditions", []), *doc.get("allergies", [])]
    terms = _terms(items, context)
    rows = []
    for n, item in enumerate(items):
        row = {"name": item["name"], "kind": item["kind"], "ingredient": item["ingredient"]}
        label = screen._label(item["ingredient"]) if item["ingredient"] else None
        if label is None:
            rows.append({**row, "label": None, "note": NO_LABEL[item["kind"]], "findings": []})
            continue
        found = screen._label_findings(label, terms[n])
        rows.append({**row, "label": {"title": screen.label_title(label), "set_id": label["set_id"],
                                      "url": screen.cite_url(screen.SourceKind.LABEL, label["set_id"]),
                                      "updated": label.get("effective_time")},
                     "findings": [_finding(f) for f in found]})
    flagged = [r["name"] for r in rows if any(f["severity"] == "block" for f in r["findings"])]
    return {"items": rows, "contraindication_mentions": flagged, "searched_for": sorted(set().union(*terms.values())),
            "in_plsi": PLAN}


COMMANDS: dict[str, Cmd] = {
    "check": Cmd("medcheck.plugin:check", (FILE,),
                 "each medicine's FDA label read for the other medicines, supplements, conditions and allergies"),
}
