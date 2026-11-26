"""Keys from the environment or a .env file; values are never printed, and `redact()` masks them."""

from __future__ import annotations

import os
import re
from pathlib import Path

from labreport import files
from labreport.errors import PluginError, ValidationError
from labreport.paths import REPO_ROOT, home_dir

UNLOCKS: dict[str, str] = {
    "LABREPORT_HOME": "where the plugin keeps its files",
    "LABREPORT_DEBUG": "redacted tracebacks on stderr when 1",
    "LABREPORT_ENV_FILE": "a .env file to read keys from",
}

_SECRET_NAME = re.compile(r"KEY|TOKEN|PASSWORD|USERNAME|SECRET|EMAIL")
_CANDIDATE = re.compile(_SECRET_NAME.pattern + r"|CLIENT|BEARER|_URL$")  # names worth showing in scan
_seen: set[str] = set()
_QUERY_SECRET = re.compile(r"(?i)([?&](?:api_key|key|token|password)=)[^&\s#\"']+")
_BEARER = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+")


def env_file() -> Path:
    return Path(os.environ.get("LABREPORT_ENV_FILE") or REPO_ROOT / ".env")


def _remember(name: str, value: str) -> None:
    """Record a value for redaction; only secret-like names, so paths and URLs in messages stay readable."""
    if _SECRET_NAME.search(name):
        hide(value)


def hide(value: str) -> None:
    """Mask a secret that does not come from the environment (e.g. a relay install token) in every redacted message."""
    if len(value) >= 6:
        _seen.add(value)


def load_env_file(path: Path | None = None) -> dict[str, str]:
    """Parse KEY=VALUE lines (optional `export `, quotes, # comments). Missing file -> {}."""
    path = path or env_file()
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.removeprefix("export ").partition("=")
        name, value = name.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        if name:
            values[name] = value
            _remember(name, value)
    return values


def map_file() -> Path:
    return home_dir() / "keys-map.json"


def aliases() -> dict[str, str]:
    """Known variable -> the name of the user's existing secret it is read from (names only); the one reader of
    keys-map.json, which must map names to names."""
    path = map_file()
    try:
        mapped = files.load_json(path) if path.is_file() else {}
    except ValidationError:
        mapped = None
    if not isinstance(mapped, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in mapped.items()):
        raise ValidationError(f"{path.name} must map key variables to secret names", code="KEYS_MAP_INVALID",
                              hint=f"delete {path} and map the keys again (plsi keys scan)")
    return mapped


def _value(name: str, file_values: dict[str, str]) -> str | None:
    """Process env first, then .env; empty strings count as unset."""
    return os.environ.get(name) or file_values.get(name) or None


def redact(text: str) -> str:
    """Mask every recorded secret value, secret query parameters and bearer tokens. Never raises: an unreadable
    .env or keys-map.json leaves the values already recorded."""
    text = str(text)
    for name in UNLOCKS:
        _remember(name, os.environ.get(name, ""))
    try:
        file_values = load_env_file()
        for name, source in aliases().items():
            _remember(name, _value(source, file_values) or "")
    except (OSError, ValueError, PluginError):
        pass
    for value in sorted(_seen, key=len, reverse=True):
        text = text.replace(value, "***")
    return _BEARER.sub(r"\1***", _QUERY_SECRET.sub(r"\1***", text))
