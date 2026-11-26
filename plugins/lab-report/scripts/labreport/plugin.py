"""Lab Report commands: a blood test read against PLSI's maps, its blood-test age, and the report kept for PLSI."""

from __future__ import annotations

import datetime as dt
import html
from pathlib import Path
from typing import Any

from labreport import errors
from labreport.cmdspec import FILE, A, Cmd, iso_date
from labreport.files import atomic_write_json, atomic_write_text, load_json
from labreport.life.models import ObservationInput
from labreport.map import calc, registry, units
from labreport.models import parse
from labreport.paths import home_dir
from labreport.vocab import Sex

MAPS = ('blood_phenoage', 'routine_blood', 'cardiometabolic', 'hormones')
AGE_MAP = "blood_phenoage"
SITE = "https://longevitygrok.si/"
TREND = f"How these values move over time (the trajectory) runs in PLSI, and your reports move over with you: {SITE}"


def _coordinates() -> dict[str, tuple[str, Any]]:
    out: dict[str, tuple[str, Any]] = {}
    for map_id in MAPS:
        for c in registry.get(map_id).coordinates:
            if c.kind.value == "measured" and c.id not in out:
                out[c.id] = (map_id, c)
    return out


def _find(name: str, known: dict[str, tuple[str, Any]]) -> tuple[str, Any] | None:
    key = name.strip().lower()
    return known.get(key) or next((v for v in known.values() if v[1].label.lower() == key), None)


def markers() -> dict[str, Any]:
    """Every marker the report reads: its id, name, unit and the other units it converts from."""
    rows = [{"marker": cid, "label": c.label, "unit": c.unit, "converts_from": [v.from_unit for v in c.conversions],
             "map_range": bool(c.ranges), "blood_age_input": map_id == AGE_MAP}
            for cid, (map_id, c) in _coordinates().items()]
    return {"markers": rows}


def _position(value: float, low: float | None, high: float | None) -> str | None:
    if low is None and high is None:
        return None
    return "below" if low is not None and value < low else "above" if high is not None and value > high else "within"


def _row(item: dict[str, Any], known: dict[str, tuple[str, Any]], sex: Sex) -> dict[str, Any]:
    found = _find(str(item.get("marker", "")), known)
    value, unit = float(item["value"]), item.get("unit")
    row: dict[str, Any] = {"marker": item.get("marker"), "value": value, "unit": unit,
                           "lab_range": [item.get("ref_low"), item.get("ref_high")],
                           "lab_position": _position(value, item.get("ref_low"), item.get("ref_high"))}
    if not found:
        return {**row, "known": False}
    map_id, c = found
    try:
        canonical, how = units.to_canonical(value, unit, c)
    except ValueError as e:
        return {**row, "known": True, "marker": c.id, "label": c.label, "unit_problem": str(e)}
    row |= {"known": True, "marker": c.id, "label": c.label, "map": map_id, "canonical": canonical,
            "canonical_unit": c.unit, "converted": how}
    if fits := c.best_ranges(sex, None):
        r = fits[0]
        row |= {"map_range": [r.low, r.high], "map_position": _position(canonical, r.low, r.high),
                "map_range_source": r.source.model_dump(mode="json")}
    return row


def _age(rows: list[dict[str, Any]], birth_year: int | None, sex: Sex, day: dt.date) -> dict[str, Any] | None:
    inputs = {r["marker"]: r["canonical"] for r in rows if r.get("map") == AGE_MAP and "canonical" in r and not r.get("repeat")}
    need = set(registry.coordinate(registry.get(AGE_MAP), "phenoage").derive.inputs)
    if birth_year is None or not need <= inputs.keys():
        return {"missing": sorted(need - inputs.keys()), "birth_year_needed": birth_year is None}
    at = dt.datetime(day.year, day.month, day.day, 12, tzinfo=dt.timezone.utc)
    sets = [f"{k}={v}" for k, v in inputs.items() if k in need]
    age = calc.compute(AGE_MAP, "phenoage", set_values=sets, birth_year=birth_year, sex=sex.value, at=at)["value"]
    years = calc.compute(AGE_MAP, "chronological_age", set_values=sets, birth_year=birth_year, sex=sex.value, at=at)["value"]
    return {"blood_age": round(age, 1), "age": round(years, 1), "difference": round(age - years, 1),
            "source": "Levine ME et al. 2018, Aging (doi 10.18632/aging.101414)"}


def _observations(rows: list[dict[str, Any]], items: list[dict[str, Any]], day: dt.date) -> list[dict[str, Any]]:
    """The report in PLSI's import format (`plsi ingest --file`)."""
    out = []
    for row, item in zip(rows, items):
        if not row.get("known") or "unit_problem" in row:
            continue
        code = registry.coordinate(registry.get(row["map"]), row["marker"]).accepts.codes[0]
        obs = {"kind": "measurement", "code": code.model_dump(mode="json"), "original_text": str(item.get("printed") or row["label"]),
               "value_quantity": row["value"], "unit": row["unit"], "effective_at": f"{day.isoformat()}T12:00:00Z",
               "effective_basis": "document", "origin": {"kind": "user_upload"}}
        obs |= {k: item[k] for k in ("ref_low", "ref_high") if item.get(k) is not None}
        out.append(parse(ObservationInput, obs).dump())
    return out


def _reports() -> Path:
    return home_dir() / "reports"


HINT = '{"date": "YYYY-MM-DD", "birth_year": 1980, "sex": "F", "values": [{"marker": "glucose", "value": 5.1, "unit": "mmol/L"}]}'


def _invalid(message: str) -> errors.ValidationError:
    return errors.ValidationError(message, code="REPORT_INPUT", hint=HINT)


def _report(doc: Any) -> dict[str, Any]:
    """The report as read, or one error naming what is wrong."""
    if not isinstance(doc, dict) or not isinstance(doc.get("values"), list) or not doc["values"]:
        raise _invalid("the report needs date, sex and a list of values")
    try:
        iso_date(str(doc.get("date")))
    except ValueError:
        raise _invalid(f"date {doc.get('date')!r}: give the draw date as YYYY-MM-DD") from None
    if (doc.get("sex") or "unknown") not in {s.value for s in Sex}:
        raise _invalid(f"sex {doc.get('sex')!r}: F, M, X or unknown")
    for n, item in enumerate(doc["values"]):
        if not isinstance(item, dict) or not item.get("marker") or isinstance(item.get("value"), bool) \
                or not isinstance(item.get("value"), (int, float)):
            raise _invalid(f"values[{n}]: each value needs a marker and a number (as printed: {item!r})")
    return doc


def read(file: str) -> dict[str, Any]:
    """`read --file report.json`: {date, birth_year, sex, values: [{marker, value, unit, ref_low, ref_high, printed}]}."""
    doc = _report(load_json(file))
    day, sex = iso_date(doc["date"]), Sex(doc.get("sex") or "unknown")
    known = _coordinates()
    rows, seen = [], set()
    for item in doc["values"]:
        row = _row(item, known, sex)
        if row.get("known") and row["marker"] in seen:
            row["repeat"] = True  # the first value of a marker counts; a repeat is shown, not used
        seen.add(row["marker"])
        rows.append(row)
    age = _age(rows, doc.get("birth_year"), sex, day)
    path = _reports() / f"{day.isoformat()}.json"
    earlier = sorted(p.stem for p in _reports().glob("*.json")) if _reports().is_dir() else []
    atomic_write_json(path, _observations(rows, doc["values"], day))
    atomic_write_json(_reports() / "summaries" / f"{day.isoformat()}.json", {"date": day.isoformat(), "rows": rows, "age": age})
    out = {"date": day.isoformat(), "rows": rows, "age": age, "saved": str(path),
           "unknown": [r["marker"] for r in rows if not r.get("known")]}
    if [d for d in earlier if d != day.isoformat()]:
        out["in_plsi"] = TREND
    return out


def history() -> dict[str, Any]:
    """The reports kept so far, newest first; the trend over time runs in PLSI."""
    folder = _reports() / "summaries"
    rows = []
    for p in sorted(folder.glob("*.json"), reverse=True) if folder.is_dir() else []:
        s = load_json(p)
        rows.append({"date": s["date"], "values": len(s["rows"]), "blood_age": (s.get("age") or {}).get("blood_age")})
    return {"reports": rows, **({"in_plsi": TREND} if len(rows) > 1 else {})}


def card(day: dt.date | None = None) -> dict[str, Any]:
    """`card [--date]`: one self-contained page for a report: the blood-test age and every value."""
    folder = _reports() / "summaries"
    dates = sorted(p.stem for p in folder.glob("*.json")) if folder.is_dir() else []
    if not dates:
        raise errors.NotFound("no report read yet", code="NO_REPORT", hint="read one first: read --file report.json")
    s = load_json(folder / f"{(day.isoformat() if day else dates[-1])}.json")
    e = html.escape
    age = s.get("age") or {}
    head = (f"<div class=age><b>{age['blood_age']}</b><span>blood-test age</span><i>{age['age']} years old · "
            f"{'+' if age['difference'] > 0 else ''}{age['difference']} years</i></div>") if "blood_age" in age else (
            "<p class=muted>Blood-test age needs all nine markers and the birth year: "
            + e(", ".join(age.get("missing", []))) + "</p>")
    rows = "".join(f"<tr><td>{e(str(r.get('label') or r['marker']))}</td><td>{e(str(r['value']))} {e(str(r.get('unit') or ''))}</td>"
                   f"<td>{e(' – '.join('' if v is None else str(v) for v in r['lab_range']) if any(v is not None for v in r['lab_range']) else '')}</td>"
                   f"<td class={e(str(r.get('lab_position') or ''))}>{e(str(r.get('lab_position') or ''))}</td></tr>" for r in s["rows"])
    page = f"""<!doctype html><meta charset=utf-8><title>Lab report {e(s['date'])}</title>
<style>body{{font:15px system-ui;margin:2rem auto;max-width:720px;color:#16201b}}.age{{background:#0f7a4f;color:#fff;border-radius:16px;padding:1.5rem;margin:1rem 0}}
.age b{{font-size:3rem;display:block}}.age i{{display:block;opacity:.85}}table{{width:100%;border-collapse:collapse}}td{{padding:.4rem;border-bottom:1px solid #e3e8e5}}
.above,.below{{color:#b3261e;font-weight:600}}.muted,footer{{color:#5c6b63}}footer{{margin-top:2rem;font-size:13px}}</style>
<h1>Lab report · {e(s['date'])}</h1>{head}<table><tr><th align=left>Marker</th><th align=left>Value</th><th align=left>Lab range</th><th></th></tr>{rows}</table>
<footer>Not medical advice: discuss your results with a doctor. Blood-test age: {e(age.get('source', 'Levine 2018'))}.<br>
Made with the Lab Report plugin · the trend over time runs in <a href="{SITE}">PLSI</a></footer>"""
    path = folder.parent / f"{s['date']}.html"
    atomic_write_text(path, page)
    return {"path": str(path), "date": s["date"]}


COMMANDS: dict[str, Cmd] = {
    "markers": Cmd("labreport.plugin:markers", (), "the markers a report can hold, with units and conversions"),
    "read": Cmd("labreport.plugin:read", (FILE,), "read one blood test: units, ranges, blood-test age; keep it for PLSI",
                ("card",)),
    "card": Cmd("labreport.plugin:card", (A("--date", dest="day", type=iso_date, help="YYYY-MM-DD (default the latest)"),),
                "a page for one report: blood-test age and values"),
    "history": Cmd("labreport.plugin:history", (), "the reports kept so far"),
}
