"""The page renderer: one package template with one inline script (its CSP hash filled in) and one JSON payload."""

from __future__ import annotations

import base64
import hashlib
import re
from importlib import resources
from typing import Any

from labjournal.files import canonical_json

PAYLOAD_PLACEHOLDER = "__PLSI_PAYLOAD__"
HASH_PLACEHOLDER = "__PLSI_SCRIPT_HASH__"
LOGO_PLACEHOLDER = "__PLSI_LOGO__"
_SCRIPT_RE = re.compile(r"<script>(.*?)</script>", re.S)
_ESCAPES = {"<": "\\u003c", ">": "\\u003e", "&": "\\u0026", "\u2028": "\\u2028", "\u2029": "\\u2029"}


def _script_hash(script: str) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii")


def _embed_json(obj: Any) -> str:
    return re.sub("[<>&\u2028\u2029]", lambda m: _ESCAPES[m.group()], canonical_json(obj))


def _logo() -> str:
    return "data:image/png;base64," + base64.b64encode(resources.files("labjournal").joinpath("logo.png").read_bytes()).decode("ascii")


def render_template(template_name: str, payload: dict[str, Any], parts: dict[str, str] | None = None) -> str:
    template = resources.files("labjournal").joinpath(template_name).read_text(encoding="utf-8")
    for placeholder, text in (parts or {}).items():
        template = template.replace(placeholder, text)
    template = template.replace(LOGO_PLACEHOLDER, _logo())
    script = _SCRIPT_RE.search(template)
    head, sep, tail = template.partition(PAYLOAD_PLACEHOLDER)
    if script is None or not sep or PAYLOAD_PLACEHOLDER in tail or head.count(HASH_PLACEHOLDER) != 1:
        raise RuntimeError(f"{template_name} must hold one inline script, one payload and one hash placeholder")
    head = head.replace(HASH_PLACEHOLDER, _script_hash(script.group(1)))
    return head + _embed_json(payload) + tail
