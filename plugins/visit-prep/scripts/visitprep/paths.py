"""Ids, instance directories and safe path joining (Windows-aware)."""

from __future__ import annotations

import os
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
MAPS_DIR = REPO_ROOT / "maps"  # the shipped State Maps
# repo data the package reads from its folder; a non-editable (wheel) install leaves them behind
REPO_DATA = ("maps", "mothership/consent.md", "mothership/references")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_WINDOWS_RESERVED = {"con", "prn", "aux", "nul"} | {f"{p}{i}" for p in ("com", "lpt") for i in range(1, 10)}
# <PLSI_HOME> folders that are not instances: never an instance name
HOME_DIRS = frozenset({"egress", "extensions", "feedback", "inbox", "journal", "mothership", "research", "targets", "work"})


def is_reserved(name: str) -> bool:
    return name.split(".")[0].lower() in _WINDOWS_RESERVED


def is_valid_id(value: str) -> bool:
    return bool(ID_RE.fullmatch(value)) and not is_reserved(value)


def require_repo_data() -> None:
    return None


def home_dir() -> Path:
    return Path(os.environ.get("VISITPREP_HOME") or Path("~/visit-prep").expanduser())


