"""Shared model base and value types used by every layer: ids, times, Code, SourceRef, ExternalText.

`*Input` models are what the bot writes (with `local_id`s); `extra="forbid"` makes them reject any bookkeeping
field. Stored models extend them with tool-assigned ids and fields.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Any, TypeVar

import pydantic
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, WithJsonSchema, model_validator

from visitprep.clock import parse_time
from visitprep.codes import PATTERNS
from visitprep.errors import ValidationError, violation
from visitprep.paths import ID_RE, is_valid_id
from visitprep.vocab import CodeSystem

CAP_ABSTRACT = 4_000
CAP_LABEL = 8_000
CAP_REPLY = 20_000
CAP_FIELD = 400  # one relayed field (`external_str`)
TRUNCATED = " […]"


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    def dump(self) -> dict[str, Any]:
        """The JSON form every tool writes and returns (None fields omitted)."""
        return self.model_dump(mode="json", exclude_none=True)


def _check_id(value: str) -> str:
    if not is_valid_id(value):
        raise ValueError("Windows reserved names are not allowed")
    return value


SHA256_RE = re.compile(r"[0-9a-f]{64}")
Id = Annotated[str, Field(pattern=ID_RE.pattern), AfterValidator(_check_id)]
LocalId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")]
EventId = Annotated[str, Field(pattern=r"^evt_[0-9a-f]{8,32}$")]
RealId = Annotated[str, Field(pattern=r"^[a-z]+_[0-9a-f]{8,32}$")]
Sha256Hex = Annotated[str, Field(pattern=f"^{SHA256_RE.pattern}$")]
PrefixedHash = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
# Aware UTC datetime; input may be an ISO date (-> T12:00:00Z) or datetime (naive = UTC).
UtcTime = Annotated[
    datetime,
    BeforeValidator(parse_time),
    WithJsonSchema({"anyOf": [{"type": "string", "format": "date-time"}, {"type": "string", "format": "date"}]}),
]


class Code(Model):
    system: CodeSystem
    code: str = Field(min_length=1, max_length=128)
    display: str | None = None

    @model_validator(mode="after")
    def _loinc_format(self) -> Code:
        if self.system == CodeSystem.LOINC and not PATTERNS[CodeSystem.LOINC].fullmatch(self.code):
            raise ValueError(f"LOINC code must match {PATTERNS[CodeSystem.LOINC].pattern}")
        return self


_STRIP = {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x200E, 0x200F, 0x061C} | set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A))


M = TypeVar("M", bound=BaseModel)


def violations_from(exc: pydantic.ValidationError, prefix: str = "") -> list[dict[str, str]]:
    """pydantic errors -> [{path, rule, message, hint}] (path like `claims.0.sources`)."""
    out = []
    for err in exc.errors(include_url=False):
        path = ".".join(str(p) for p in (prefix, *err["loc"]) if p != "")
        out.append(violation(path or "$", f"schema.{err['type']}", err["msg"].removeprefix("Value error, ")))
    return out


def validation_error(exc: pydantic.ValidationError, what: str, code: str | None = None) -> ValidationError:
    """`invalid <what>: <first path>: <first message>`, carrying ALL violations."""
    violations = violations_from(exc)
    return ValidationError(f"invalid {what}: {violations[0]['path']}: {violations[0]['message']}", code=code, violations=violations)


