"""The code formats of the Mothership wire (WIRE §2), the same as the Mother's: each code system's pattern, the
LOINC mod-10 check digit and the SNOMED CT Verhoeff check digit. `free` and `cpg` codes are PLSI's own names: they
leave the computer only when a shipped or installed map declares them (`shareable`)."""

from __future__ import annotations

import re

from trialscout.vocab import CodeSystem

PATTERNS = {
    CodeSystem.LOINC: re.compile(r"[0-9]{1,7}-[0-9]"),
    CodeSystem.RXNORM: re.compile(r"[0-9]{1,10}"),
    CodeSystem.SNOMED: re.compile(r"[0-9]{6,18}"),
    CodeSystem.ICD10CM: re.compile(r"[A-TV-Z][0-9][0-9A-Z](?:\.[0-9A-Z]{1,4})?"),
    CodeSystem.CPG: re.compile(r"[a-z][a-z0-9_.:-]{0,63}"),
    CodeSystem.FREE: re.compile(r"[a-z][a-z0-9_.:-]{0,63}"),
}
LOCAL = frozenset({CodeSystem.FREE, CodeSystem.CPG})  # PLSI's own names: no id-number exemption, map-declared only
# never leave as a code: ethnicity and race (the subject carries the ethnicity group) and occupation. Only these
# concepts match: a SNOMED descendant (e.g. one ethnic group) is not caught here, so the skills never record one.
NEVER_SHARED = frozenset({
    (CodeSystem.LOINC.value, "69490-1"), (CodeSystem.LOINC.value, "32624-9"),  # ethnicity, race
    (CodeSystem.LOINC.value, "11341-5"), (CodeSystem.LOINC.value, "85658-3"),  # occupation
    (CodeSystem.SNOMED.value, "372148003"), (CodeSystem.SNOMED.value, "14679004"),  # ethnic group, occupation
})
_D = ("0123456789", "1234067895", "2340178956", "3401289567", "4012395678",
      "5987604321", "6598710432", "7659821043", "8765932104", "9876543210")
_P = ("0123456789", "1576283094", "5803796142", "8916043527", "9453126870", "4286573901", "2793806415", "7046913285")


