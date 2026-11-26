#!/usr/bin/env python3
"""Install, verify and self-test a PLSI plugin's code (names, home and dependencies from MANIFEST.json)."""
import base64
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "MANIFEST.json").read_text(encoding="utf-8"))
PKG, CMD = MANIFEST["package"], MANIFEST["command"]


def out(obj, code=0):
    print(json.dumps(obj, indent=1))
    sys.exit(code)


def home_dir(args):
    if "--home" in args:
        if args.index("--home") + 1 >= len(args):
            out({"ok": False, "error": "--home needs a folder"}, 2)
        return Path(args[args.index("--home") + 1]).expanduser().resolve()
    return Path(os.environ.get(MANIFEST["home_env"]) or MANIFEST["home_default"]).expanduser().resolve()


def usable(python):
    try:
        return subprocess.run([python, "-c", MANIFEST["check"]], capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def find_python(home, with_deps):
    venv = home / "app" / ".venv" / "bin" / "python"
    for p in (str(venv), sys.executable, shutil.which("python3") or ""):
        if p and usable(p):
            return p, None
    if not with_deps:
        return None, f"needs Python 3.11+ with {', '.join(MANIFEST['deps'])}; run install again with --with-deps (uses uv)"
    uv = shutil.which("uv")
    if not uv:
        return None, "uv is not installed: install uv (https://docs.astral.sh/uv/) or the packages yourself"
    for cmd in ([uv, "venv", "--quiet", "--python", ">=3.11", str(venv.parent.parent)],
                [uv, "pip", "install", "--quiet", "--python", str(venv), *MANIFEST["deps"]]):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            return None, (r.stderr or r.stdout)[-400:]
    return (str(venv), None) if usable(str(venv)) else (None, "the new environment does not import the packages")


def verify(home):
    pkg = home / "app" / PKG
    bad = [rel for rel, h in MANIFEST["files"].items()
           if not (pkg / rel).is_file() or hashlib.sha256((pkg / rel).read_bytes()).hexdigest() != h]
    extra = [str(p.relative_to(pkg)) for p in pkg.rglob("*") if p.is_file() and "__pycache__" not in p.parts
             and str(p.relative_to(pkg)) not in MANIFEST["files"]] if pkg.is_dir() else []
    return {"ok": not bad and not extra and pkg.is_dir(), "version": MANIFEST["version"], "files": len(MANIFEST["files"]),
            "mismatched": bad, "unexpected": extra, "code": str(pkg)}


def dig(obj, path):
    for k in path.split("."):
        obj = obj[int(k)] if isinstance(obj, list) else obj[k]
    return obj


def same(have, want):
    if isinstance(want, float) and isinstance(have, (int, float)):
        return abs(have - want) <= 1e-9 * max(1.0, abs(want))
    return have == want


def selftest(home):
    cases = json.loads((HERE / "selftest.json").read_text(encoding="utf-8"))
    scratch, work = tempfile.mkdtemp(prefix=f"{PKG}-selftest-"), tempfile.mkdtemp(prefix=f"{PKG}-inputs-")
    for name, blob in cases["files"].items():
        Path(work, name).write_bytes(base64.b64decode(blob))
    env = {**os.environ, MANIFEST["home_env"]: scratch}
    fails, checks = [], 0
    for argv, expect in cases["cases"]:
        argv = [a.replace("{w}", work) for a in argv]
        r = subprocess.run([str(home / CMD), *argv], env=env, capture_output=True, text=True)
        try:
            got = json.loads(r.stdout)
        except ValueError:
            fails.append({"argv": argv[:2], "error": (r.stdout + r.stderr)[-300:]})
            continue
        for path, want in expect.items():
            checks += 1
            try:
                have = dig(got, path)
            except (KeyError, IndexError, TypeError):
                have = "<missing>"
            if not same(have, want):
                fails.append({"argv": argv[:2], "path": path, "want": want, "got": have})
    shutil.rmtree(scratch, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    return {"ok": not fails, "checks": checks, "failed": fails}


def install(home, with_deps):
    python, why = find_python(home, with_deps)
    if not python:
        out({"ok": False, "error": why}, 3)
    app = home / "app"
    pkg = app / PKG
    if pkg.exists():
        shutil.rmtree(pkg)  # code only, never the data
    shutil.copytree(HERE / PKG, pkg, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(HERE / "MANIFEST.json", app / "MANIFEST.json")
    launcher = home / CMD
    env = MANIFEST["home_env"]
    launcher.write_text(f'#!/bin/sh\nif [ -z "${{{env}:-}}" ]; then {env}={shlex.quote(str(home))}; fi\nexport {env}\n'
                        f'PYTHONPATH={shlex.quote(str(app))}${{PYTHONPATH:+:$PYTHONPATH}} exec {shlex.quote(python)} -m {PKG} "$@"\n')
    launcher.chmod(0o755)
    res = verify(home)
    if not res["ok"]:
        out(res, 1)
    st = selftest(home)
    out({"ok": st["ok"], "version": MANIFEST["version"], "home": str(home), "run": str(launcher), "python": python,
         "files_verified": res["files"], "selftest": st}, 0 if st["ok"] else 1)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] not in ("install", "verify", "selftest"):
        out({"ok": False, "usage": "install.py install|verify|selftest [--home DIR] [--with-deps]"}, 2)
    home = home_dir(args)
    if args[0] == "install":
        install(home, "--with-deps" in args)
    if args[0] == "verify":
        res = verify(home)
        out(res, 0 if res["ok"] else 1)
    res = selftest(home)
    out(res, 0 if res["ok"] else 1)
