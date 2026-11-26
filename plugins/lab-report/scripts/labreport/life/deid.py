"""Deidentification profile `plsi-limited-v1`.

Event dates are kept, so this is NOT HIPAA Safe Harbor. The profile:
- subject.json keeps only birth year, sex, country and relation (age >= 90 -> birth_year null, age_group "90+";
  see deid_subject_fields, applied by plsi.life.store, which owns subject.json);
- Origin keeps file_sha256 and page, never a path or filename;
- FHIR allowlist: code.coding, value[x], effective[x] (Period -> effective_at + effective_end), clinicalStatus,
  component[] (one observation each), medication dose text and doseQuantity. Everything else is dropped (identifier,
  subject, performer, note, text, contained, extension, attachments);
- Patient name parts, identifier values, telecom and address are held in memory only; any observation from
  that bundle whose text contains one of them is rejected with IDENTIFIER_IN_TEXT.
"""

from __future__ import annotations

from typing import Any

from labreport.clock import now
from labreport.vocab import Sex

PROFILE = "plsi-limited-v1"
AGE_GROUP_90 = "90+"
MIN_LEN = 3  # shorter strings would produce false hits
SHORT_LEN = 6  # identifiers shorter than this must match a whole token

_GENDER = {"male": Sex.M, "female": Sex.F, "other": Sex.X, "unknown": Sex.UNKNOWN}


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def deid_subject_fields(birth_year: int | None, sex: Sex | str | None) -> dict[str, Any]:
    """Keep birth_year and sex only; age >= 90 -> birth_year null, age_group "90+"."""
    over_90 = birth_year is not None and now().year - birth_year >= 90
    return {
        "birth_year": None if over_90 else birth_year,
        "age_group": AGE_GROUP_90 if over_90 else None,
        "sex": Sex(sex) if sex is not None else Sex.UNKNOWN,
    }
