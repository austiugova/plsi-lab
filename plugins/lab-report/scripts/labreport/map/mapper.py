"""Mapper: project the event log into a StateDocument, and Policy's one view of the world (states, care context,
subject, scoring values). Never invents values: units convert only through plsi.map.units."""

from __future__ import annotations


from labreport import files, paths
from labreport.life.models import Subject
from labreport.map.models import StateDocument
from labreport.models import parse
from labreport.life.store import EventStore
from labreport.vocab import ObservationKind

FREE_TEXT_KINDS = {ObservationKind.GOAL, ObservationKind.PREFERENCE, ObservationKind.LIFESTYLE}  # set items with no code system
LOCAL_MAPS = frozenset({"personal_context"})  # goals and preferences: free text about the user's life, never sent


def latest_state(instance: str, map_id: str) -> StateDocument | None:
    """Parse states/<map_id>/latest.json, or None if absent. Does NOT verify the hash (callers use verify_hash())."""
    path = paths.safe_join(paths.instance_dir(instance), "states", map_id, "latest.json")
    return parse(StateDocument, files.load_json(path), "latest.json") if path.is_file() else None


def subject(instance: str) -> Subject:
    return EventStore(instance).subject


