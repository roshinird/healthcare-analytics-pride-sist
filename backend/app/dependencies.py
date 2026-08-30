"""Shared FastAPI dependencies.

Owner: Dev A.
Spec: docs/06-api-contract.md §2 (FROZEN), docs/10-security-privacy.md §1.3.

Nothing reaches a service function until it has passed through `analytics_filters`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Query
from pydantic import ValidationError

from app.errors import VALIDATION_ERROR, ApiError
from app.schemas.params import AnalyticsFilters
from app.services.datasource import get_datasource


def utc_now_iso() -> str:
    """Timestamp for `meta.generated_at`, in the contract's Zulu format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def datasource():
    return get_datasource()


def _first_pydantic_message(exc: ValidationError) -> str:
    for err in exc.errors():
        message = str(err.get("msg", "")).removeprefix("Value error, ").strip()
        if message:
            return message
    return "One or more query parameters are invalid."


def analytics_filters(
    start_date: Optional[str] = Query(
        None, description="Inclusive lower bound on admission_date (YYYY-MM-DD)."
    ),
    end_date: Optional[str] = Query(
        None, description="Inclusive upper bound on admission_date (YYYY-MM-DD)."
    ),
    condition: Optional[str] = Query(
        None, description="A condition_name present in ref_medical_condition."
    ),
    admission_type: Optional[str] = Query(
        None, description="Emergency, Urgent or Elective."
    ),
    insurance_provider: Optional[str] = Query(
        None, description="An insurance provider present in the dataset."
    ),
    gender: Optional[str] = Query(None, description="Male or Female."),
    source=Depends(datasource),
) -> AnalyticsFilters:
    """Validate the six common filters. Any failure returns the frozen 422 shape."""
    try:
        filters = AnalyticsFilters(
            start_date=start_date,
            end_date=end_date,
            condition=condition,
            admission_type=admission_type,
            insurance_provider=insurance_provider,
            gender=gender,
        )
    except ValidationError as exc:
        raise ApiError(VALIDATION_ERROR, _first_pydantic_message(exc), 422) from exc

    # Reference-value membership needs the data layer, so it is checked here
    # rather than inside the Pydantic model.
    if filters.condition is not None:
        known = source.known_conditions()
        if filters.condition not in known:
            raise ApiError(
                VALIDATION_ERROR,
                "condition must be one of " + ", ".join(known),
                422,
            )

    if filters.insurance_provider is not None:
        known = source.known_insurance_providers()
        if filters.insurance_provider not in known:
            raise ApiError(
                VALIDATION_ERROR,
                "insurance_provider must be one of " + ", ".join(known),
                422,
            )

    return filters
