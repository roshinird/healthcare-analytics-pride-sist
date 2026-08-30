"""API contract tests.

Owner: Dev A.
Covers docs/13-testing-checklist.md §3 (API) for everything Dev A owns.

These assert the *frozen* shapes in docs/06-api-contract.md. If one of these
fails after a change, the change is a contract violation, not a broken test.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

MUST_ENDPOINTS = [
    "/api/kpis",
    "/api/analytics/admissions-trend",
    "/api/analytics/top-hospitals",
    "/api/analytics/conditions",
    "/api/analytics/demographics",
    "/api/analytics/billing",
    "/api/analytics/test-results",
]

FORBIDDEN_FIELDS = ("name", "doctor", "room_number", "medication", "patient_id")


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


# ---------------------------------------------------------------- health ---
def test_health_returns_frozen_shape(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == {"status": "ok"}
    assert set(body["meta"]) == {"generated_at"}
    assert body["meta"]["generated_at"].endswith("Z")


# -------------------------------------------------------------- envelope ---
@pytest.mark.parametrize("path", MUST_ENDPOINTS)
def test_must_endpoints_return_envelope(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"data", "meta"}
    assert set(body["meta"]) == {"row_count", "generated_at", "note"}
    assert isinstance(body["meta"]["row_count"], int)


@pytest.mark.parametrize("path", MUST_ENDPOINTS)
def test_endpoints_accept_a_filter_combination(client: TestClient, path: str) -> None:
    response = client.get(path, params={"condition": "Diabetes", "gender": "Female"})
    assert response.status_code == 200, response.text
    assert "data" in response.json()


@pytest.mark.parametrize("path", MUST_ENDPOINTS)
def test_unknown_query_parameters_are_ignored(client: TestClient, path: str) -> None:
    """Forward-tolerance rule, docs/06-api-contract.md §2."""
    response = client.get(path, params={"totally_unknown": "value"})
    assert response.status_code == 200


@pytest.mark.parametrize("path", MUST_ENDPOINTS + ["/api/health"])
def test_no_forbidden_identity_fields_anywhere(client: TestClient, path: str) -> None:
    """docs/10-security-privacy.md §2 — dropped fields must never resurface."""
    payload = client.get(path).text.lower()
    for field in FORBIDDEN_FIELDS:
        assert f'"{field}"' not in payload


# ------------------------------------------------------- endpoint shapes ---
def test_kpis_fields(client: TestClient) -> None:
    data = client.get("/api/kpis").json()["data"]
    assert set(data) == {
        "total_encounters",
        "avg_length_of_stay",
        "avg_billing_amount",
        "earliest_admission",
        "latest_admission",
    }


def test_admissions_trend_always_exposes_rolling_average_key(client: TestClient) -> None:
    """SHOULD-HAVE field is present-and-null, never omitted."""
    rows = client.get("/api/analytics/admissions-trend").json()["data"]
    assert rows
    for row in rows:
        assert set(row) == {
            "month",
            "encounter_count",
            "prev_month_count",
            "pct_change",
            "rolling_avg_3mo",
        }
    assert rows[0]["prev_month_count"] is None
    assert rows[0]["pct_change"] is None


def test_top_hospitals_returns_at_most_ten_ranked_rows(client: TestClient) -> None:
    rows = client.get("/api/analytics/top-hospitals").json()["data"]
    assert 0 < len(rows) <= 10
    ranks = [row["volume_rank"] for row in rows]
    assert ranks == sorted(ranks)
    counts = [row["encounter_count"] for row in rows]
    assert counts == sorted(counts, reverse=True)


def test_conditions_rows_carry_category_and_share(client: TestClient) -> None:
    rows = client.get("/api/analytics/conditions").json()["data"]
    assert rows
    for row in rows:
        assert set(row) == {
            "condition_name",
            "condition_category",
            "encounter_count",
            "percentage_share",
            "avg_length_of_stay",
        }
        assert row["condition_category"] in {"Chronic", "Acute"}


def test_demographics_has_three_breakdowns(client: TestClient) -> None:
    data = client.get("/api/analytics/demographics").json()["data"]
    assert set(data) == {"age_groups", "genders", "blood_types"}
    assert all(data[key] for key in data)


def test_billing_blocks_are_always_present(client: TestClient) -> None:
    data = client.get("/api/analytics/billing").json()["data"]
    assert set(data) == {
        "by_insurance_provider",
        "by_admission_type",
        "above_average",
        "statistical_outliers",
        "excluded_invalid_billing_count",
    }
    assert set(data["statistical_outliers"]) == {
        "outlier_count",
        "lower_bound",
        "upper_bound",
    }
    assert isinstance(data["excluded_invalid_billing_count"], int)


def test_test_results_rows(client: TestClient) -> None:
    rows = client.get("/api/analytics/test-results").json()["data"]
    assert rows
    for row in rows:
        assert set(row) == {"admission_type", "test_result", "encounter_count"}
        assert row["admission_type"] in {"Emergency", "Urgent", "Elective"}
        assert row["test_result"] in {"Normal", "Abnormal", "Inconclusive"}


# ------------------------------------------------------------- validation --
@pytest.mark.parametrize(
    "params,fragment",
    [
        ({"start_date": "not-a-date"}, "start_date"),
        ({"end_date": "07-05-2024"}, "end_date"),
        ({"start_date": "2024-05-01", "end_date": "2024-04-01"}, "end_date"),
        ({"admission_type": "Walk-in"}, "admission_type"),
        ({"gender": "Other"}, "gender"),
        ({"condition": "Dragonpox"}, "condition"),
        ({"insurance_provider": "Definitely Not A Payer"}, "insurance_provider"),
    ],
)
def test_invalid_parameters_return_frozen_422(client, params, fragment) -> None:
    response = client.get("/api/kpis", params=params)
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert fragment in body["error"]["message"]


def test_zero_row_filter_returns_200_with_note(client: TestClient) -> None:
    """Never a 404 or a 500 (docs/13-testing-checklist.md §3)."""
    response = client.get(
        "/api/kpis", params={"start_date": "2099-01-01", "end_date": "2099-12-31"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["row_count"] == 0
    assert body["meta"]["note"]
    assert body["data"]["total_encounters"] == 0


def test_unknown_route_returns_frozen_error_shape(client: TestClient) -> None:
    response = client.get("/api/analytics/does-not-exist")
    assert response.status_code == 404
    assert set(response.json()) == {"error"}


# -------------------------------------------------------------- optional ---
def test_report_chart_returns_501_when_not_built(client: TestClient) -> None:
    response = client.get("/api/analytics/report-chart")
    assert response.status_code in (200, 501)
    if response.status_code == 501:
        body = response.json()
        assert body["error"]["code"] == "NOT_IMPLEMENTED"
    else:
        assert response.headers["content-type"] == "image/png"


def test_openapi_exposes_exactly_the_nine_frozen_routes(client: TestClient) -> None:
    """docs/14-ai-agent-instructions.md §4 — no route proliferation."""
    paths = set(client.get("/openapi.json").json()["paths"])
    assert paths == {
        "/api/health",
        "/api/kpis",
        "/api/analytics/admissions-trend",
        "/api/analytics/top-hospitals",
        "/api/analytics/conditions",
        "/api/analytics/demographics",
        "/api/analytics/billing",
        "/api/analytics/test-results",
        "/api/analytics/report-chart",
    }
