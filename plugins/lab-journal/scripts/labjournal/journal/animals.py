"""Animal studies run in PLSI: groups, animals and weights are kept as recorded."""

from __future__ import annotations

from typing import Any

from labjournal.journal.inplsi import block
from labjournal.journal.results import Results


def weights(r: Results) -> dict[str, Any]:
    return {}


def roster(r: Results) -> dict[str, Any]:
    return block("Animal studies") if r.animals or r.weights or r.groups else {}
