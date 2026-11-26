"""JSON on disk: canonical hashing, atomic writes, unique file names, the instance lock, jsonl logs, capped input reading."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from medcheck.errors import InstanceLocked, NotFound, ValidationError

MAX_INPUT_BYTES = 50 * 1024 * 1024
LOCK_TIMEOUT_S = 10.0


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_hex(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def hash_json(obj: Any) -> str:
    """'sha256:<hex>' over canonical_json(obj). Used for map_hash, state_hash, action/context/input hashes."""
    return "sha256:" + sha256_hex(canonical_json(obj))


@contextlib.contextmanager
def lock(directory: Path, timeout: float = LOCK_TIMEOUT_S, stale: float | None = None) -> Iterator[None]:
    """Exclusive `<directory>/.lock` via O_EXCL; retries until timeout, then InstanceLocked. A lock older than
    `stale` seconds is taken for one a crashed process left and is broken. NOT re-entrant: never call
    EventStore.append* while holding it for the same instance."""
    path = directory / ".lock"
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if stale is not None and _age(path) > stale:
                path.unlink(missing_ok=True)
                continue
            if time.monotonic() >= deadline:
                raise InstanceLocked(f"{directory.name} is locked by another process", hint=f"remove {path} if no plsi process is running") from None
            time.sleep(0.05)
    try:
        os.write(fd, str(os.getpid()).encode("ascii"))
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def _age(path: Path) -> float:
    """Seconds since `path` was written; 0 when it is already gone."""
    try:
        return time.time() - path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def _reject_constant(name: str) -> Any:
    raise ValueError(f"non-finite number {name} is not allowed")


def loads_json(text: str) -> Any:
    return json.loads(text, parse_constant=_reject_constant)


def read_input_bytes(path: str | Path, max_bytes: int = MAX_INPUT_BYTES) -> bytes:
    """Read a user input file ('-' = stdin), capped at max_bytes."""
    if str(path) == "-":
        data = sys.stdin.buffer.read(max_bytes + 1)
    else:
        p = Path(path)
        if not p.is_file():
            raise NotFound(f"input file not found: {p.name}", code="FILE_NOT_FOUND")
        with open(p, "rb") as fh:
            data = fh.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValidationError(f"input exceeds {max_bytes} bytes", code="INPUT_TOO_LARGE")
    return data.removeprefix(b"\xef\xbb\xbf")


def decode_input(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"input is not UTF-8: {exc.reason}", code="INPUT_NOT_UTF8") from None


def parse_input_json(text: str) -> Any:
    try:
        return loads_json(text)
    except ValueError as exc:
        raise ValidationError(f"invalid JSON: {exc}", code="INVALID_JSON") from None


def read_input_text(path: str | Path, max_bytes: int = MAX_INPUT_BYTES) -> str:
    return decode_input(read_input_bytes(path, max_bytes))


def load_json(path: str | Path) -> Any:
    """Parse a JSON input file ('-' = stdin). Rejects NaN/Infinity; capped at 50 MB."""
    return parse_input_json(read_input_text(path))
