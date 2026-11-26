#!/usr/bin/env python3
"""Cursor hook: a plugin's code and records change only through its own commands (folders from MANIFEST.json)."""
import json
import os
import re
import sys
from pathlib import Path

DESTRUCTIVE = re.compile(r"(^|[\s;&|(])(rm|mv|truncate|shred|unlink|chmod|chown)\s|sed\s+(-\w*\s+)*-i|perl\s+-\w*i|"
                         r"(^|[^>])>{1,2}\s*\S|\btee\b|\bcp\b|\brsync\b|python3?\s+-c")
OK = {"permission": "allow"}
MANIFEST: dict = {}
GUARD: dict = {}


def home():
    return Path(os.environ.get(MANIFEST["home_env"]) or MANIFEST["home_default"]).expanduser()


def guarded(path: Path, h: Path):
    """'code', 'records' or None for a path."""
    try:
        rel = path.resolve().relative_to(h)
    except ValueError:
        return None
    top = rel.parts[0] if rel.parts else ""
    return "code" if top in ("app", MANIFEST["command"]) else "records" if top in GUARD["records"] else None


def strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


def tool(event, h):
    cwd = Path(event.get("cwd") or os.getcwd())
    for s in strings(event.get("tool_input") or {}):
        if "\n" in s or len(s) > 1024 or ("/" not in s and "\\" not in s):
            continue
        kind = guarded(cwd / Path(s).expanduser(), h)
        if kind == "code":
            return {"permission": "deny", "user_message": f"{GUARD['title']}: its installed code is never edited.",
                    "agent_message": f"{s} is the {GUARD['title']}'s checked code: never edit it. A missing feature is "
                                     "'not in this plugin yet'; an update is a reinstall from the plugin (install.py install)."}
        if kind == "records":
            return {"permission": "deny", "user_message": f"{GUARD['title']}: records change only through its commands.",
                    "agent_message": f"{s} is a {GUARD['title']} record. " + GUARD["how"].replace("<home>", str(h))}
    return OK


def shell(event, h):
    cmd = event.get("command") or ""
    names = {str(h), str(h.resolve())}
    for base in {str(Path.home()), str(Path.home().resolve())}:
        names |= {n.replace(base, "~", 1) for n in list(names) if n.startswith(base)}
        names |= {n.replace(base, "$HOME", 1) for n in list(names) if n.startswith(base)}
    tops = ("app", *GUARD["records"])
    touches = any(f"{n}/{t}" in cmd for n in names for t in tops)
    if touches and DESTRUCTIVE.search(cmd) and not cmd.lstrip().startswith(tuple(f"{n}/{MANIFEST['command']} " for n in names)):
        return {"permission": "ask", "user_message": f"This command could change or delete {GUARD['title']} records. Allow it?",
                "agent_message": f"{GUARD['title']} records change only through its commands; a backup is a `tar czf` copy."}
    return OK


def main():
    try:
        MANIFEST.update(json.loads((Path(__file__).resolve().parent / "MANIFEST.json").read_text(encoding="utf-8")))
        GUARD.update(MANIFEST["guard"])
        event = json.load(sys.stdin)
        h = home().resolve() if "tool_input" in event else home()
        result = shell(event, h) if "command" in event and "tool_input" not in event else tool(event, h)
    except Exception:  # noqa: BLE001 - never block other work
        result = OK
    print(json.dumps(result))


if __name__ == "__main__":
    main()
