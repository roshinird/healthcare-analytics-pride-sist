"""Configuration, CORS, error-safety and integration-seam tests.

Owner: Dev A.
Covers docs/10-security-privacy.md §1 and docs/12-dev-workflow-split.md §6.
"""

from __future__ import annotations

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.dependencies import analytics_filters, datasource
from app.main import create_app
from app.schemas.params import AnalyticsFilters
from app.services.dev_fixtures import DevFixtureDataSource


# ------------------------------------------------------------------ config --
def test_production_cors_is_a_single_named_origin() -> None:
    settings = Settings(
        database_path=get_settings().database_path,
        cors_allowed_origin="https://healthcare-analytics.vercel.app/",
        environment="production",
    )
    assert settings.cors_origins == ["https://healthcare-analytics.vercel.app"]
    assert "*" not in settings.cors_origins


def test_development_cors_allows_the_vite_dev_server() -> None:
    settings = Settings(
        database_path=get_settings().database_path,
        cors_allowed_origin="http://localhost:5173",
        environment="development",
    )
    assert "http://localhost:5173" in settings.cors_origins
    assert "*" not in settings.cors_origins


def test_database_path_is_absolute_and_cwd_independent() -> None:
    assert get_settings().database_path.is_absolute()


def test_cors_headers_present_for_allowed_origin() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/api/health", headers={"Origin": "http://localhost:5173"}
        )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


# ------------------------------------------------------------ error safety --
def test_unhandled_exception_never_leaks_internals() -> None:
    app = create_app()
    boom = APIRouter()

    @boom.get("/api/_boom")
    def _boom():  # pragma: no cover - the raise is the point
        raise RuntimeError("secret: /var/data/healthcare.db password=hunter2")

    app.include_router(boom)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/_boom")

    assert response.status_code == 500
    body = response.json()
    assert body == {
        "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}
    }
    assert "hunter2" not in response.text
    assert "Traceback" not in response.text


# ------------------------------------------------------------- filter model --
def test_filters_report_only_supplied_values() -> None:
    filters = AnalyticsFilters(start_date="2024-01-01", gender="Male")
    assert filters.active() == {"start_date": "2024-01-01", "gender": "Male"}
    assert not filters.is_empty
    assert AnalyticsFilters().is_empty


def test_blank_strings_are_treated_as_absent() -> None:
    filters = AnalyticsFilters(condition="", gender="", start_date="")
    assert filters.is_empty


@pytest.mark.parametrize("bad", ["2024-13-01", "2024/01/01", "01-01-2024", "yesterday"])
def test_rejected_date_formats(bad: str) -> None:
    with pytest.raises(Exception):
        AnalyticsFilters(start_date=bad)


# -------------------------------------------------------- integration seam --
def test_filters_reach_the_datasource_unchanged() -> None:
    """Guards the Dev A -> Dev B boundary: what the client sent is what the
    data layer receives."""
    seen: list[AnalyticsFilters] = []

    class RecordingSource(DevFixtureDataSource):
        def conditions(self, filters):
            seen.append(filters)
            return super().conditions(filters)

    app = create_app()
    app.dependency_overrides[datasource] = RecordingSource

    with TestClient(app) as client:
        response = client.get(
            "/api/analytics/conditions",
            params={
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "condition": "Diabetes",
                "admission_type": "Urgent",
                "insurance_provider": "Medicare",
                "gender": "Female",
            },
        )

    assert response.status_code == 200
    assert len(seen) == 1
    assert seen[0].active() == {
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "condition": "Diabetes",
        "admission_type": "Urgent",
        "insurance_provider": "Medicare",
        "gender": "Female",
    }
    app.dependency_overrides.clear()


def test_fixture_source_is_flagged_in_meta_note() -> None:
    """Fixture data can never masquerade as computed analytics."""
    app = create_app()
    app.dependency_overrides[datasource] = DevFixtureDataSource
    with TestClient(app) as client:
        note = client.get("/api/kpis").json()["meta"]["note"]
    app.dependency_overrides.clear()
    assert note and "fixture" in note.lower()


def test_dev_fixtures_are_internally_consistent() -> None:
    """Monthly, condition, demographic and test-result totals must agree."""
    source = DevFixtureDataSource()
    empty = AnalyticsFilters()

    total = source.kpis(empty)[0]["total_encounters"]
    trend, _, _ = source.admissions_trend(empty)
    conditions, _, _ = source.conditions(empty)
    demographics, _, _ = source.demographics(empty)
    test_results, _, _ = source.test_results(empty)
    billing, _, _ = source.billing(empty)

    assert sum(row["encounter_count"] for row in trend) == total
    assert sum(row["encounter_count"] for row in conditions) == total
    assert sum(row["encounter_count"] for row in demographics["age_groups"]) == total
    assert sum(row["encounter_count"] for row in demographics["genders"]) == total
    assert sum(row["encounter_count"] for row in test_results) == total

    valid = total - billing["excluded_invalid_billing_count"]
    assert sum(r["encounter_count"] for r in billing["by_insurance_provider"]) == valid
    assert sum(r["encounter_count"] for r in billing["by_admission_type"]) == valid


def test_analytics_filters_dependency_is_wired_to_every_analytics_route() -> None:
    app = create_app()
    routed = [
        route
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/")
        and getattr(route, "path", "") != "/api/health"
    ]
    assert routed
    for route in routed:
        names = [d.call for d in route.dependant.dependencies]
        assert analytics_filters in names, route.path
