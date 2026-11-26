#!/usr/bin/env python3
"""Cursor hook: the journal and its code change only through `lj`."""
import json
import os
import re
import sys
from pathlib import Path

DESTRUCTIVE = re.compile(r"(^|[\s;&|(])(rm|mv|truncate|shred|unlink|chmod|chown)\s|sed\s+(-\w*\s+)*-i|perl\s+-\w*i|"
                         r"(^|[^>])>{1,2}\s*\S|\btee\b|\bcp\b|\brsync\b|python3?\s+-c")
OK = {"permission": "allow"}


def home():
    return Path(os.environ.get("LABJOURNAL_HOME") or "~/lab-journal").expanduser()


def guarded(path: Path, h: Path):
    try:
        rel = path.resolve().relative_to(h)
    except ValueError:
        return None
    top = rel.parts[0] if rel.parts else ""
    return {"app": "code", "journal": "entry", "lj": "code"}.get(top)


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
        kind = guarded((cwd / Path(s).expanduser()), h)
        if kind == "code":
            return {"permission": "deny", "user_message": "Lab Journal: its installed code is never edited.",
                    "agent_message": f"{s} is the Lab Journal's checked code: never edit it. A missing calculation is "
                                     "'not in this journal yet'; an update is a reinstall from the plugin (install.py install)."}
        if kind == "entry":
            return {"permission": "deny", "user_message": "Lab Journal: entries change only through the journal.",
                    "agent_message": f"{s} is inside the journal. Write the entry JSON under {h}/drafts/ and save it with "
                                     f"`{h}/lj save --file <draft>`; files go in with `lj attach`. A signed entry never "
                                     "changes: write a new entry with \"amends\"."}
    return OK


def shell(event, h):
    cmd = event.get("command") or ""
    names = {str(h), str(h.resolve())}
    for base in {str(Path.home()), str(Path.home().resolve())}:
        names |= {n.replace(base, "~", 1) for n in list(names) if n.startswith(base)}
        names |= {n.replace(base, "$HOME", 1) for n in list(names) if n.startswith(base)}
    touches = any(f"{n}/journal" in cmd or f"{n}/app" in cmd for n in names)
    if touches and DESTRUCTIVE.search(cmd) and not cmd.lstrip().startswith(tuple(f"{n}/lj " for n in names)):
        return {"permission": "ask", "user_message": "This command could change or delete Lab Journal records. Allow it?",
                "agent_message": "Journal records change only through `lj` commands; a backup is `tar czf` of the journal."}
    return OK


def main():
    try:
        event = json.load(sys.stdin)
        h = home().resolve() if "tool_input" in event else home()
        result = shell(event, h) if "command" in event and "tool_input" not in event else tool(event, h)
    except Exception:  # noqa: BLE001 - never block other work
        result = OK
    print(json.dumps(result))


if __name__ == "__main__":
    main()
