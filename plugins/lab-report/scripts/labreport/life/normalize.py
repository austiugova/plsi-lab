"""Code and unit normalization (`normalize observations`): LOINC via NLM Clinical Tables, RxNorm via plsi.rxnav,
units via a local UCUM alias table. Unit spelling lives in plsi.life.units, LOINC resolution in plsi.life.loinc; this
module drives `plsi normalize observations` and re-exports both for `from labreport.life.normalize import ...`."""

from __future__ import annotations


from labreport.life.units import UNIT_BASES, UNIT_PREFIXES, normalize_unit

__all__ = ["normalize_unit", "UNIT_BASES", "UNIT_PREFIXES"]

MAX_AMBIGUOUS_CANDIDATES = 5


