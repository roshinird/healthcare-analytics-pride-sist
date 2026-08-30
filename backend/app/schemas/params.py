"""Request parameter models.

Owner: Dev A.
Spec: docs/06-api-contract.md §2 (FROZEN), docs/10-security-privacy.md §1.3.

Every inbound query parameter is validated here before any service function is
reached. Unrecognised query parameters are ignored rather than rejected, per the
frozen contract's forward-tolerance rule.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

DATE_FORMAT = "%Y-%m-%d"

ADMISSION_TYPES: tuple[str, ...] = ("Emergency", "Urgent", "Elective")
GENDERS: tuple[str, ...] = ("Male", "Female")


def _parse_iso_date(value: str, field_name: str) -> date:
    try:
        return datetime.strptime(value.strip(), DATE_FORMAT).date()
    except (ValueError, AttributeError) as exc:  # pragma: no cover - message asserted in tests
        raise ValueError(f"{field_name} must be in YYYY-MM-DD format") from exc


class AnalyticsFilters(BaseModel):
    """The six common filters accepted by every `/api/analytics/*` route and `/api/kpis`."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    start_date: Optional[str] = None
    end_date: Optional[str] = None
    condition: Optional[str] = None
    admission_type: Optional[str] = None
    insurance_provider: Optional[str] = None
    gender: Optional[str] = None

    @field_validator("start_date", "end_date")
    @classmethod
    def _validate_dates(cls, value: Optional[str], info) -> Optional[str]:
        if value in (None, ""):
            return None
        _parse_iso_date(value, info.field_name)
        return value.strip()

    @field_validator("admission_type")
    @classmethod
    def _validate_admission_type(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        if value not in ADMISSION_TYPES:
            raise ValueError(
                "admission_type must be one of " + ", ".join(ADMISSION_TYPES)
            )
        return value

    @field_validator("gender")
    @classmethod
    def _validate_gender(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        if value not in GENDERS:
            raise ValueError("gender must be one of " + ", ".join(GENDERS))
        return value

    @field_validator("condition", "insurance_provider")
    @classmethod
    def _normalise_optional_text(cls, value: Optional[str]) -> Optional[str]:
        # Reference-value membership is checked in app/dependencies.py, where the
        # data layer is reachable. Here we only normalise emptiness and length.
        if value in (None, ""):
            return None
        if len(value) > 120:
            raise ValueError("filter value is too long")
        return value

    @model_validator(mode="after")
    def _validate_range(self) -> "AnalyticsFilters":
        if self.start_date and self.end_date:
            start = _parse_iso_date(self.start_date, "start_date")
            end = _parse_iso_date(self.end_date, "end_date")
            if end < start:
                raise ValueError("end_date must be greater than or equal to start_date")
        return self

    def active(self) -> dict[str, str]:
        """Only the filters the caller actually supplied."""
        return {k: v for k, v in self.model_dump().items() if v is not None}

    @property
    def is_empty(self) -> bool:
        return not self.active()
