"""Analytics routes.

Owner: Dev A.
Spec: docs/06-api-contract.md §4 (FROZEN), docs/07-backend-architecture.md §2.

This module contains no SQL and no Pandas. It validates input, calls the resolved
data source, and wraps the result in the frozen envelope.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, Response

from app.dependencies import analytics_filters, datasource, utc_now_iso
from app.errors import NOT_IMPLEMENTED, error_payload
from app.schemas.params import AnalyticsFilters
from app.schemas.responses import (
    BillingResponse,
    ConditionsResponse,
    DemographicsResponse,
    KpiResponse,
    TestResultsResponse,
    TopHospitalsResponse,
    TrendResponse,
)

router = APIRouter(tags=["analytics"])

VALIDATION_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: {"description": "Validation error (frozen error envelope)"},
    500: {"description": "Unhandled server error (generic message only)"},
}


def _envelope(
    fetch: Callable[[AnalyticsFilters], tuple[Any, int, Optional[str]]],
    filters: AnalyticsFilters,
) -> dict:
    data, row_count, note = fetch(filters)
    return {
        "data": data,
        "meta": {
            "row_count": row_count,
            "generated_at": utc_now_iso(),
            "note": note,
        },
    }


@router.get(
    "/api/kpis",
    response_model=KpiResponse,
    responses=VALIDATION_RESPONSES,
    summary="Q1 — KPI summary",
)
def kpis(filters: AnalyticsFilters = Depends(analytics_filters), source=Depends(datasource)):
    return _envelope(source.kpis, filters)


@router.get(
    "/api/analytics/admissions-trend",
    response_model=TrendResponse,
    responses=VALIDATION_RESPONSES,
    summary="Q2 — Monthly admissions trend (CTE + LAG window function)",
)
def admissions_trend(
    filters: AnalyticsFilters = Depends(analytics_filters), source=Depends(datasource)
):
    return _envelope(source.admissions_trend, filters)


@router.get(
    "/api/analytics/top-hospitals",
    response_model=TopHospitalsResponse,
    responses=VALIDATION_RESPONSES,
    summary="Q3 — Top-10 facilities by encounter volume (RANK window function)",
)
def top_hospitals(
    filters: AnalyticsFilters = Depends(analytics_filters), source=Depends(datasource)
):
    return _envelope(source.top_hospitals, filters)


@router.get(
    "/api/analytics/conditions",
    response_model=ConditionsResponse,
    responses=VALIDATION_RESPONSES,
    summary="Q4 + Q5 — Condition distribution and average length of stay",
)
def conditions(
    filters: AnalyticsFilters = Depends(analytics_filters), source=Depends(datasource)
):
    return _envelope(source.conditions, filters)


@router.get(
    "/api/analytics/demographics",
    response_model=DemographicsResponse,
    responses=VALIDATION_RESPONSES,
    summary="Q6 — Age group, gender and blood type breakdowns",
)
def demographics(
    filters: AnalyticsFilters = Depends(analytics_filters), source=Depends(datasource)
):
    return _envelope(source.demographics, filters)


@router.get(
    "/api/analytics/billing",
    response_model=BillingResponse,
    responses=VALIDATION_RESPONSES,
    summary="Q7 + Q8 — Billing by payer and admission type, above-average encounters",
)
def billing(
    filters: AnalyticsFilters = Depends(analytics_filters), source=Depends(datasource)
):
    return _envelope(source.billing, filters)


@router.get(
    "/api/analytics/test-results",
    response_model=TestResultsResponse,
    responses=VALIDATION_RESPONSES,
    summary="Q9 — Test result distribution by admission type",
)
def test_results(
    filters: AnalyticsFilters = Depends(analytics_filters), source=Depends(datasource)
):
    return _envelope(source.test_results, filters)


@router.get(
    "/api/analytics/report-chart",
    responses={
        200: {"content": {"image/png": {}}, "description": "Executive summary PNG"},
        501: {"description": "Report generation not available in this build"},
        **VALIDATION_RESPONSES,
    },
    summary="SHOULD HAVE — Matplotlib executive summary (PNG)",
)
def report_chart(
    filters: AnalyticsFilters = Depends(analytics_filters), source=Depends(datasource)
):
    """The one documented exception to the JSON envelope (docs/06-api-contract.md §4).

    Returns 501 with the frozen error shape when Dev B's `services/report.py` is
    not present, so the dashboard can hide its download action instead of erroring.
    """
    png = source.report_png(filters)
    if not png:
        return _not_implemented()
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


def _not_implemented() -> Response:
    payload = error_payload(
        NOT_IMPLEMENTED, "Report chart generation is not available in this build."
    )
    return Response(
        content=json.dumps(payload),
        status_code=501,
        media_type="application/json",
    )
