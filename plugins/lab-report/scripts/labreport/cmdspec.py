"""The shape of a command table entry (`Cmd`), the argparse shorthands the tables are written in, and `merge`,
which joins the package tables into one. plsi.cli parses and dispatches the result."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from labreport.vocab import LivePage


def iso_date(value: str) -> date:
    return date.fromisoformat(value)


def A(*flags: str, **kw: Any) -> tuple[tuple[str, ...], dict[str, Any]]:
    return flags, kw


@dataclass(frozen=True)
class Exclusive:
    """A mutually exclusive group of `A(...)` arguments; plsi.cli adds it with add_mutually_exclusive_group."""

    args: tuple[tuple[tuple[str, ...], dict[str, Any]], ...]
    required: bool = True


INSTANCE = A("--instance", required=True, help="instance name")
FILE = A("--file", required=True, help="input path ('-' = stdin)")
PLAN = A("--plan", dest="plan_id", required=True, help="plan id")
MAP = A("--map", dest="map_id", required=True)
MAP_OPT = A("--instance", help="include this instance's user maps")
SENDER = A("--instance", help="the contributor's instance (install token); omit for professional files")
HASH = A("--hash", dest="expected", required=True, help="package_hash of the checked file the user approved")


@dataclass(frozen=True)
class Cmd:
    """`target` "module:function" is called with the parsed arguments; `next` are suggested follow-up commands;
    `refresh`: the page the command changes, rebuilt after it when it exists (plsi.cli, LIVE_PAGES)."""

    target: str
    args: tuple = ()
    help: str = ""
    next: tuple[str, ...] = ()
    refresh: LivePage | None = None


