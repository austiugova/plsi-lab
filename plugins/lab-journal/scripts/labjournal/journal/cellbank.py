"""Plates, flasks and vials of cells: an entry's vessels, and the cell bank - every vial at its latest record, by
freezer box and position, with stock per cell line and passage."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from labjournal.journal.results import Results
from labjournal.vocab.journal import VesselStatus


def _in_box(status: VesselStatus | None) -> bool:
    return status in (None, VesselStatus.FROZEN)


def vessels(r: Results) -> dict[str, Any]:
    if not r.vessels:
        return {}
    checks = []
    ids = defaultdict(int)
    slots: dict[tuple[str, str], list[str]] = defaultdict(list)
    for v in r.vessels:
        ids[v.id] += 1
        if v.box and v.position and _in_box(v.status):
            slots[(v.box, v.position)].append(v.id)
    checks += [f"vessel id {k} used {n} times" for k, n in ids.items() if n > 1]
    checks += [f"{', '.join(vs)} share box {b} position {p}" for (b, p), vs in slots.items() if len(vs) > 1]
    return {"rows": [v.dump() for v in r.vessels], "checks": checks}
