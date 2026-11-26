"""Code extensions: new operations Grok (or a developer) adds without touching the core.

An extension is a small Python package with a manifest `plsi_extension.yaml` (ExtensionManifest below; an installed
version is immutable). Entry-point signatures by kind:
- importer (Life):          run(data: bytes) -> list[dict]  ObservationInput dicts; origin is filled in by ingest
- deriver (Map):            run(inputs: dict[str, float], *, age: float | None, sex: str) -> float
- evidence_source (Policy): run(query: str, limit: int) -> list[dict]  {title, url?, kind?, id?}; kind/id as SourceRef

Rules: extensions ADD operations and never replace core ones. An extension is full-trust code that runs with the
user's permissions: it is installed only with the user's explicit approval naming its source. The static checks are
guard rails, not a sandbox: `install` refuses a package that imports a layer its kind may not use, assigns attributes
of plsi modules, or whose own tests (tests/test_*.py, run with a minimal environment and no keys) fail. Installs live in
<PLSI_HOME>/extensions/<id>/<version>/ and every derived value records extension@version in its provenance.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import Field

from labreport.errors import NotFound, ValidationError
from labreport.files import load_json
from labreport.models import Id, Model, parse
from labreport.paths import home_dir, safe_join
from labreport.vocab import ClaimLevel, ExtensionKind

MANIFEST = "plsi_extension.yaml"
TEST_TIMEOUT_S = 300
# what an extension's tests see of the environment: enough to start Python, never a key
TEST_ENV = ("PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE", "APPDATA",
            "LOCALAPPDATA", "LANG", "LC_ALL", "PYTHONIOENCODING")
FORBIDDEN_IMPORTS: dict[ExtensionKind, tuple[str, ...]] = {
    ExtensionKind.IMPORTER: ("labreport.map", "labreport.policy", "labreport.life.store", "labreport.cli"),
    ExtensionKind.DERIVER: ("labreport.policy", "labreport.life.store", "labreport.cli"),
    ExtensionKind.EVIDENCE_SOURCE: ("labreport.life", "labreport.cli"),
}


class ExtensionManifest(Model):
    id: Id
    version: Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+$")]
    kind: ExtensionKind
    entrypoint: Annotated[str, Field(pattern=r"^[A-Za-z_]\w*:[A-Za-z_]\w*$")]  # <module file without .py>:<function>
    summary: str = Field(min_length=1, max_length=300)
    claim_level: ClaimLevel = ClaimLevel.DESIGNED  # informational
    monotone: bool = False  # derivers only: true lets censored inputs be bounded through it


def _root() -> Path:
    return home_dir() / "extensions"


def _index_path() -> Path:
    return _root() / "index.json"


def _index() -> dict[str, Any]:
    path = _index_path()
    return load_json(path) if path.is_file() else {}


def _read_manifest(directory: Path) -> ExtensionManifest:
    path = directory / MANIFEST
    if not path.is_file():
        raise NotFound(f"{MANIFEST} not found in {directory}", code="EXTENSION_INVALID")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        raise ValidationError(f"{MANIFEST} is not readable YAML: {exc}", code="EXTENSION_INVALID") from None
    return parse(ExtensionManifest, raw, MANIFEST)


def _run_tests(directory: Path) -> str:
    tests = sorted((directory / "tests").glob("test_*.py"))
    if not tests:
        raise ValidationError("an extension needs tests: tests/test_*.py", code="EXTENSION_INVALID")
    with tempfile.TemporaryDirectory() as home:  # tests never touch real instances
        kept = {k: v for k in TEST_ENV if (v := os.environ.get(k)) is not None}  # no keys or tokens reach the tests
        env = kept | {"PYTHONPATH": str(directory), "PLSI_HOME": home, "PLSI_ENV_FILE": str(Path(home) / "none")}
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *map(str, tests)],
                              cwd=directory, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=TEST_TIMEOUT_S)
    last = (proc.stdout.strip().splitlines() or ["no output"])[-1]
    if proc.returncode != 0:
        raise ValidationError(f"extension tests failed: {last}", code="EXTENSION_TESTS_FAILED", hint=proc.stdout[-1500:])
    return last


def test(ext_id: str) -> dict[str, Any]:
    return {"id": ext_id, "tests": _run_tests(_active_dir(ext_id))}


def installed(kind: ExtensionKind) -> dict[str, str]:
    return {k: v["active"] for k, v in _index().items() if v["kind"] == kind and v.get("active")}


def _active_dir(ext_id: str) -> Path:
    entry = _index().get(ext_id)
    if not entry or not entry.get("active"):
        raise NotFound(f"no active extension {ext_id!r}", code="EXTENSION_NOT_FOUND", hint="plsi ext list")
    return safe_join(_root(), ext_id, entry["active"])


def manifest(ext_id: str) -> ExtensionManifest:
    return _read_manifest(_active_dir(ext_id))


def rule_id(ext_id: str) -> str:
    """Provenance rule of an extension value, e.g. 'extension:my_ext@0.1.0'."""
    return f"extension:{ext_id}@{manifest(ext_id).version}"


@lru_cache(maxsize=64)
def _load(ext_id: str, version: str) -> Callable[..., Any]:
    directory = safe_join(_root(), ext_id, version)
    module, func = _read_manifest(directory).entrypoint.split(":")
    spec = importlib.util.spec_from_file_location(f"plsi_ext_{ext_id}_{version.replace('.', '_')}", directory / f"{module}.py")
    if spec is None or spec.loader is None:
        raise ValidationError(f"{module}.py of {ext_id} {version} cannot be loaded", code="EXTENSION_INVALID")
    loaded = importlib.util.module_from_spec(spec)
    before = set(sys.modules)
    sys.path.insert(0, str(directory))  # the extension may import its own helper modules
    try:
        spec.loader.exec_module(loaded)
    finally:
        sys.path.remove(str(directory))
        for name in set(sys.modules) - before:  # its helpers stay its own: another extension's same name loads afresh
            file = getattr(sys.modules[name], "__file__", None)
            if file and Path(file).resolve().is_relative_to(directory):
                del sys.modules[name]
    return getattr(loaded, func)


def _function(ext_id: str, kind: ExtensionKind) -> Callable[..., Any]:
    m = manifest(ext_id)
    if m.kind != kind:
        raise ValidationError(f"{ext_id} is a {m.kind.value}, not a {kind.value}", code="EXTENSION_KIND")
    return _load(ext_id, m.version)


def deriver(ext_id: str) -> Callable[..., float]:
    return _function(ext_id, ExtensionKind.DERIVER)


