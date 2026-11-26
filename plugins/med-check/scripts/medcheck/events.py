"""The event envelope shared by all layers. The log itself is plsi.life.store.

Each layer registers the payload model of its own event types with `register_payload`, so no layer
imports another to read or write the log.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from medcheck.vocab import EventType


@dataclass(frozen=True)
class NewEvent:
    """An event to append via EventStore.append_many; ids and recorded_at are tool-set."""

    type: EventType
    payload: BaseModel
    dedupe_key: str | None = None
    dedupe: bool = False  # True: if an ACTIVE event has the same dedupe_key, append nothing and return its id


PAYLOAD_TYPES: dict[EventType, type[BaseModel]] = {}


def register_payload(event_type: EventType, model: type[BaseModel]) -> None:
    PAYLOAD_TYPES[event_type] = model
