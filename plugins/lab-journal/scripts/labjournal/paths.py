"""Ids, instance directories and safe path joining (Windows-aware)."""

from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath, PureWindowsPath

from labjournal.errors import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
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


def validate_id(value: str, what: str = "id") -> str:
    if not isinstance(value, str) or not is_valid_id(value):
        raise ValidationError(f"invalid {what}: {value!r}", hint=f"must match {ID_RE.pattern} and not be a Windows reserved name")
    return value


def require_repo_data() -> None:
    return None


def journal_home() -> Path:
    return Path(os.environ.get("LABJOURNAL_HOME") or "/workspace/lab-journal")


def safe_join(base: Path | str, *parts: str) -> Path:
    """Join relative parts under base; reject absolute, drive-relative, '..', ':' and escapes."""
    base_path = Path(base).resolve()
    for part in parts:
        p = str(part)
        if not p or ":" in p or "\x00" in p or PureWindowsPath(p).anchor or PurePosixPath(p).is_absolute():
            raise ValidationError(f"unsafe path component: {p!r}")
        segs = re.split(r"[\\/]", p)
        if ".." in segs:
            raise ValidationError(f"unsafe path component: {p!r}")
        if any(is_reserved(s) for s in segs if s):
            raise ValidationError(f"reserved name in path: {p!r}")
    joined = base_path.joinpath(*parts).resolve()
    if joined != base_path and base_path not in joined.parents:
        raise ValidationError(f"path escapes base: {'/'.join(parts)!r}")
    return joined
