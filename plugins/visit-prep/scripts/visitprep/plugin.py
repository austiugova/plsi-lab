"""Visit Prep commands: results and their change since the last report, and one printable page for the visit."""

from __future__ import annotations

import datetime as dt
import html
import os
from pathlib import Path
from typing import Any

from visitprep import errors
from visitprep.cmdspec import FILE, Cmd
from visitprep.files import atomic_write_text, load_json
from visitprep.paths import home_dir

SITE = "https://longevitygrok.si/"
RECORD = f"The full record, the clinic dashboard and messages to the physician run in PLSI: {SITE}"


def _lab_reports() -> list[dict[str, Any]]:
    folder = Path(os.environ.get("LABREPORT_HOME") or "~/lab-report").expanduser() / "reports" / "summaries"
    return [load_json(p) for p in sorted(folder.glob("*.json"))] if folder.is_dir() else []


def pull() -> dict[str, Any]:
    """The latest Lab Report results, each with the change from the report before it (canonical units)."""
    reports = _lab_reports()
    if not reports:
        return {"results": [], "note": "no Lab Report results on this computer: give the results by hand"}
    last, before = reports[-1], (reports[-2] if len(reports) > 1 else None)
    earlier = {r["marker"]: r for r in (before or {}).get("rows", []) if r.get("canonical") is not None}
    rows = []
    for r in last["rows"]:
        row = {"marker": r.get("label") or r["marker"], "value": r["value"], "unit": r.get("unit"),
               "lab_position": r.get("lab_position"), "date": last["date"]}
        prev = earlier.get(r["marker"])
        if prev and r.get("canonical") is not None:
            same = prev.get("unit") == r.get("unit")  # the change in the unit the reports used, else canonical
            change = r["value"] - prev["value"] if same else r["canonical"] - prev["canonical"]
            row |= {"previous": prev["value"], "previous_unit": prev.get("unit"), "previous_date": before["date"],
                    "change": float(f"{change:.4g}"), "change_unit": r.get("unit") if same else r.get("canonical_unit")}
        rows.append(row)
    age = last.get("age") or {}
    return {"date": last["date"], "previous_date": before["date"] if before else None, "results": rows,
            "blood_age": age.get("blood_age"), "age": age.get("age")}


def _change(r: dict[str, Any]) -> str:
    if "change" not in r:
        return ""
    return f"{r['change']:+g} {r.get('change_unit') or ''} since {r.get('previous_date') or 'the last report'}"


def _list(items: list[Any]) -> str:
    return "".join(f"<li>{html.escape(str(i))}</li>" for i in items) or "<li class=muted>none given</li>"


def page(file: str) -> dict[str, Any]:
    """`page --file visit.json`: one printable page for the visit (patient's or physician's view)."""
    v = load_json(file)
    hint = '{"visit_date": "YYYY-MM-DD", "for": "patient", "reason": "...", "questions": ["..."]}'
    try:
        day = dt.date.fromisoformat(str(v["visit_date"]))
    except (TypeError, KeyError, ValueError):
        raise errors.ValidationError("the visit needs visit_date as YYYY-MM-DD", code="VISIT_INPUT", hint=hint) from None
    who = "physician" if v.get("for") == "physician" else "patient"
    e = html.escape
    results = v.get("results") or []
    rows = "".join(
        f"<tr><td>{e(str(r.get('marker')))}</td><td>{e(str(r.get('value')))} {e(str(r.get('unit') or ''))}</td>"
        f"<td>{e(str(r.get('lab_position') or ''))}</td>"
        f"<td>{e(_change(r))}</td></tr>"
        for r in results)
    table = (f"<table><tr><th>Result</th><th>Value</th><th>vs lab range</th><th>Change</th></tr>{rows}</table>"
             if rows else "<p class=muted>No results given.</p>")
    title = "Visit brief" if who == "physician" else "For my visit"
    asks = "To cover" if who == "physician" else "My questions"
    body = f"""<!doctype html><meta charset=utf-8><title>{e(title)} {day.isoformat()}</title>
<style>body{{font:14px system-ui;margin:1.5rem auto;max-width:760px;color:#16201b}}h1{{font-size:22px;margin:0}}
h2{{font-size:15px;color:#0f7a4f;border-bottom:2px solid #0f7a4f;padding-bottom:2px;margin:1.2rem 0 .4rem}}
table{{width:100%;border-collapse:collapse}}td,th{{padding:.3rem;border-bottom:1px solid #e3e8e5;text-align:left}}
.muted,footer{{color:#5c6b63}}.lines div{{border-bottom:1px solid #c9d3cd;height:1.8rem}}footer{{font-size:12px;margin-top:1.5rem}}
@media print{{body{{margin:0}}footer a{{color:inherit}}}}</style>
<h1>{e(title)} · {day.isoformat()}</h1><p class=muted>{e(str(v.get('label') or ''))}{' · last visit ' + e(str(v['last_visit'])) if v.get('last_visit') else ''}</p>
<h2>Reason for the visit</h2><p>{e(str(v.get('reason') or ''))}</p>
<h2>What changed since the last visit</h2><ul>{_list(v.get('changes') or [])}</ul>
<h2>Results</h2>{table}
<h2>Medicines and supplements</h2><ul>{_list(v.get('medicines') or [])}</ul>
<h2>{e(asks)}</h2><ol>{_list(v.get('questions') or [])}</ol>
<h2>Notes from the visit</h2><div class=lines>{'<div></div>' * 6}</div>
<footer>Generated automatically by AI and not reviewed by a clinician. Check with your clinician before acting on it.<br>
Made with the Visit Prep plugin · the full record runs in <a href="{SITE}">PLSI</a></footer>"""
    path = home_dir() / "visits" / f"{day.isoformat()}-{who}.html"
    atomic_write_text(path, body)
    return {"path": str(path), "for": who, "results": len(results), "questions": len(v.get("questions") or []),
            "in_plsi": RECORD}


COMMANDS: dict[str, Cmd] = {
    "pull": Cmd("visitprep.plugin:pull", (), "the latest Lab Report results with their change since the report before"),
    "page": Cmd("visitprep.plugin:page", (FILE,), "one printable page for the visit (patient's or physician's view)"),
}
