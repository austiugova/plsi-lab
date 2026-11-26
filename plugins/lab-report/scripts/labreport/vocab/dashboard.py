"""The dashboard vocabulary: export and report formats, live pages, and the blocks, icons, levels and groups a
dashboard draws with."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["LivePage"]


class LivePage(StrEnum):
    """A page a command rewrites in place after it changes what the page shows (`Cmd.refresh`)."""

    CLINIC = "clinic"  # the physician's clinic dashboard
    JOURNAL = "journal"  # the lab journal


