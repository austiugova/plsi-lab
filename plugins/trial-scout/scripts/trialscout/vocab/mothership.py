"""The Mothership vocabulary: reference kinds, what an enrolled user contributes, enrollment and receipt states,
the messages and project actions sent to the relay, publication status, professional scopes and analyses."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["ReferenceKind"]


class ReferenceKind(StrEnum):
    CODE_SYSTEM = "code_system"
    TERMINOLOGY_API = "terminology_api"
    EVIDENCE_SOURCE = "evidence_source"
    LABEL_SOURCE = "label_source"
    CLOCK_LIBRARY = "clock_library"
    MODEL = "model"
    ORACLE = "oracle"
    PAPER = "paper"
    DATASET = "dataset"
    JOURNAL = "journal"
    DIGEST = "digest"  # curated paper digests, event calendars, industry reports
    BASE_RATE = "base_rate"  # population mortality, incidence and prevalence tables: absolute risks for predictions
    EDUCATION = "education"
    DEVICE_DATA = "device_data"  # wearable and device data platforms (wearables/import)
    CONTACT = "contact"  # where PLSI may send data (the Longevity Mothership relay)
    DIRECTORY = "directory"  # public practitioner directories and licence registers (navigator/physicians)


