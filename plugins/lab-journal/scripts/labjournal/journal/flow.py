"""Flow cytometry gating runs in PLSI: FCS files and gates are kept as recorded."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from labjournal.journal.inplsi import block
from labjournal.journal.results import Results


def derive(folder: Path, r: Results, strict: bool = False) -> dict[str, Any]:
    return {**block("Flow gating"), "samples": []} if r.fcs else {}
