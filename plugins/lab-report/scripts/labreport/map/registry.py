"""Map registry: shipped maps/*.yaml + <instance>/maps/user/*.yaml, validation, snapshots."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from labreport import paths
from labreport.errors import NotFound, ValidationError, violation
from labreport.map import biolearn, derive
from labreport.map.models import Derive, MapContract, MapCoordinate
from labreport.models import SourceRef, parse
from labreport.paths import MAPS_DIR as SHIPPED_DIR
from labreport.vocab import ClaimLevel, CoordinateKind, CorrespondenceType, DeriveEngine, Ethnicity, Sex, SourceKind

LIVE_BATCH = 50
USER_PREFIX = "user_"  # user map ids; shipped map ids never start with it
LOAD_CHECKED = frozenset({DeriveEngine.NATIVE, DeriveEngine.EXTENSION})  # biolearn names: maps validate only (slow import)


def _parse(text: str, origin: str) -> MapContract:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValidationError(f"{origin}: not valid YAML: {exc}", code="MAP_INVALID") from None
    return parse(MapContract, data, origin, code="MAP_INVALID")


def _rule_violations(m: MapContract, user: bool, checked: frozenset[DeriveEngine] = LOAD_CHECKED) -> list[dict[str, str]]:
    """Checks beyond the schema; derive model names are checked for the `checked` engines that can list them."""
    out = []
    if user and not m.id.startswith(USER_PREFIX):
        out.append(violation("id", "map.user_prefix", f"user map ids must start with {USER_PREFIX}", USER_PREFIX + m.id))
    if user and m.claim_level != ClaimLevel.DESIGNED:
        out.append(violation("claim_level", "map.user_claim_level", "user maps must have claim_level designed", "designed"))
    out += [violation(f"coordinates.{i}.local_only", "map.user_local_only",
                      f"{c.id}: a user map may keep a coordinate local, never mark it shareable", "local_only: true")
            for i, c in enumerate(m.coordinates) if user and c.local_only is False]
    used = {c.derive.engine for c in m.coordinates if c.derive} & checked
    known = {e: fn() for e in used if (fn := derive.ENGINES[e].models)}
    for i, c in enumerate(m.coordinates):
        d = c.derive
        if d is None or known.get(d.engine) is None or d.model in known[d.engine]:  # type: ignore[operator]
            continue
        rule, message, hint = derive.ENGINES[d.engine].unknown  # type: ignore[misc]
        out.append(violation(f"coordinates.{i}.derive.model", rule, message.format(d.model), hint))
    for i, c in enumerate(m.coordinates):
        if c.ranges and (tie := next(((sex, e) for sex in (Sex.F, Sex.M, Sex.UNKNOWN) for e in (*Ethnicity, None)
                                      if len(c.best_ranges(sex, e)) > 1), None)):
            out.append(violation(f"coordinates.{i}.ranges", "map.range_tie",
                                 f"two {c.id} ranges fit sex {tie[0]}, ethnicity {tie[1]} equally",
                                 "give one range both sex and ethnicity, or drop one"))
    return out


def _expanded(m: MapContract) -> MapContract:
    """Shipped/user maps with `expand`: add a derived coordinate per biolearn clock not already declared.
    Snapshots are stored expanded and never re-expanded, so a newer biolearn cannot change an old map hash."""
    if m.expand is None or not biolearn.available():
        return m
    have = {c.id for c in m.coordinates}
    extra = [
        MapCoordinate(id=cid, label=f"{c['name']}: {c['output']} ({c['tissue']}, {c['year']})", kind=CoordinateKind.DERIVED,
                      unit=c["unit"], derive=Derive(engine=DeriveEngine.BIOLEARN, model=c["name"], inputs=[m.expand.input]),
                      correspondence_type=CorrespondenceType.STATISTICAL,
                      sources=[SourceRef(kind=SourceKind.MODEL, id="biolearn", title=c["name"], url=c["source"])])
        for c in biolearn.clocks() if (cid := re.sub(r"[^a-z0-9_]+", "_", c["name"].lower()).strip("_")) not in have
    ]
    doc = m.dump()
    return MapContract.model_validate({**doc, "coordinates": [*doc["coordinates"], *(x.dump() for x in extra)]})


@lru_cache(maxsize=32)
def _shipped(path: Path, mtime_ns: int) -> MapContract:
    """A parsed shipped map, re-read only when its file changes."""
    return _parse(path.read_text(encoding="utf-8"), path.name)


def _user_dir(instance: str) -> Path:
    return paths.instance_dir(instance) / "maps" / "user"


def load_all(instance: str | None = None) -> dict[str, MapContract]:
    """All maps by id: shipped maps plus, when instance is given, its maps/user/*.yaml.
    Raises errors.ValidationError (with violations) on an invalid file or a duplicate id."""
    files = [(p, False) for p in sorted(SHIPPED_DIR.glob("*.yaml"))]
    if instance is not None:
        files += [(p, True) for p in sorted(_user_dir(instance).glob("*.yaml"))]
    out: dict[str, MapContract] = {}
    for path, user in files:
        raw = _parse(path.read_text(encoding="utf-8"), path.name) if user else _shipped(path, path.stat().st_mtime_ns)
        m = _expanded(raw)
        if bad := _rule_violations(m, user):
            raise ValidationError(f"{path.name}: {bad[0]['message']}", code="MAP_INVALID", violations=bad)
        if m.id in out:
            raise ValidationError(f"duplicate map id {m.id!r} ({path.name})", code="MAP_DUPLICATE")
        out[m.id] = m
    return out


def get(map_id: str, instance: str | None = None) -> MapContract:
    """One map by id (shipped or the instance's user maps). Raises errors.NotFound (code MAP_NOT_FOUND)."""
    maps = load_all(instance)
    if map_id not in maps:
        raise NotFound(f"unknown map {map_id!r}", code="MAP_NOT_FOUND", hint="plsi maps list")
    return maps[map_id]


def coordinate(m: MapContract, coordinate_id: str) -> MapCoordinate:
    """One coordinate of `m`. Raises errors.NotFound (code COORDINATE_NOT_FOUND)."""
    if (c := m.coordinate(coordinate_id)) is None:
        raise NotFound(f"map {m.id} has no coordinate {coordinate_id!r}", code="COORDINATE_NOT_FOUND", hint=f"plsi maps show {m.id}")
    return c


