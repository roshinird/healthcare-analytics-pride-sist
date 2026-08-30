"""Development fixture data source.

Owner: Dev A. **This is development infrastructure, not production analytics.**

Why it exists
-------------
docs/12-dev-workflow-split.md requires Dev A and Dev B to work in parallel from
hour 0. Dev B owns ingestion, `services/queries.py` (SQL) and
`services/analytics.py` (Pandas). Until those exist on this branch, the API would
have nothing to serve and could not be run, integrated or tested.

This module serves the *frozen contract shapes* (docs/06-api-contract.md) from a
static JSON file so the whole request path — validation, envelope, error handling,
CORS, the React dashboard — is runnable and testable today. The moment Dev B's
modules land, `services/datasource.py` switches to them automatically and this
module is never touched at runtime.

Guarantees
----------
* Every response is flagged in `meta.note`, so fixture data can never be mistaken
  for computed analytics in a demo or a screenshot.
* No SQL, no database access, no patient-identity concept, no dropped field.
* The numbers are mutually consistent (monthly counts, condition counts,
  demographic counts and test-result counts all sum to the same total) so the
  dashboard's visual behaviour matches what real data will produce.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.schemas.params import AnalyticsFilters

FIXTURE_FILE = Path(__file__).with_name("dev_fixtures.json")

DEV_MODE_NOTE = (
    "Development fixtures — Dev B's SQL/Pandas layer is not present in this build. "
    "Values are illustrative and are not computed from the dataset."
)
EMPTY_NOTE = "No encounters matched the given filters."

# Reference values used to validate `condition` and `insurance_provider` filters
# while the live `ref_medical_condition` table is unavailable.
FIXTURE_CONDITIONS = (
    "Arthritis",
    "Asthma",
    "Cancer",
    "Diabetes",
    "Hypertension",
    "Obesity",
)
FIXTURE_INSURANCE_PROVIDERS = (
    "Aetna",
    "Blue Cross",
    "Cigna",
    "Medicare",
    "UnitedHealthcare",
)

FIXTURE_EARLIEST = "2019-05-08"
FIXTURE_LATEST = "2024-05-07"


@lru_cache(maxsize=1)
def _fixtures() -> dict[str, Any]:
    return json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))


def _payload(key: str) -> dict[str, Any]:
    # Deep copy via round-trip so callers can never mutate the cached fixture.
    return json.loads(json.dumps(_fixtures()[key]))


def _out_of_range(filters: AnalyticsFilters) -> bool:
    """True when the requested window cannot overlap the fixture's date span.

    Keeps the zero-row path (docs/13-testing-checklist.md §3) exercisable in
    fixture mode without pretending to filter data this module does not have.
    """
    if filters.start_date and filters.start_date > FIXTURE_LATEST:
        return True
    if filters.end_date and filters.end_date < FIXTURE_EARLIEST:
        return True
    return False


class DevFixtureDataSource:
    """Serves frozen-contract shapes from static fixtures."""

    mode = "fixture"
    is_live = False

    # -- reference values ---------------------------------------------------
    def known_conditions(self) -> tuple[str, ...]:
        return FIXTURE_CONDITIONS

    def known_insurance_providers(self) -> tuple[str, ...]:
        return FIXTURE_INSURANCE_PROVIDERS

    # -- endpoints ----------------------------------------------------------
    def kpis(self, filters: AnalyticsFilters) -> tuple[Any, int, str | None]:
        if _out_of_range(filters):
            empty = {
                "total_encounters": 0,
                "avg_length_of_stay": None,
                "avg_billing_amount": None,
                "earliest_admission": None,
                "latest_admission": None,
            }
            return empty, 0, EMPTY_NOTE
        payload = _payload("kpis")
        return payload["data"], 1, DEV_MODE_NOTE

    def admissions_trend(self, filters: AnalyticsFilters) -> tuple[Any, int, str | None]:
        if _out_of_range(filters):
            return [], 0, EMPTY_NOTE
        rows = _payload("admissions-trend")["data"]
        if filters.start_date:
            rows = [r for r in rows if r["month"] >= filters.start_date[:7]]
        if filters.end_date:
            rows = [r for r in rows if r["month"] <= filters.end_date[:7]]
        if not rows:
            return [], 0, EMPTY_NOTE
        return rows, len(rows), DEV_MODE_NOTE

    def top_hospitals(self, filters: AnalyticsFilters) -> tuple[Any, int, str | None]:
        if _out_of_range(filters):
            return [], 0, EMPTY_NOTE
        rows = _payload("top-hospitals")["data"]
        return rows, len(rows), DEV_MODE_NOTE

    def conditions(self, filters: AnalyticsFilters) -> tuple[Any, int, str | None]:
        if _out_of_range(filters):
            return [], 0, EMPTY_NOTE
        rows = _payload("conditions")["data"]
        if filters.condition:
            rows = [r for r in rows if r["condition_name"] == filters.condition]
        if not rows:
            return [], 0, EMPTY_NOTE
        return rows, len(rows), DEV_MODE_NOTE

    def demographics(self, filters: AnalyticsFilters) -> tuple[Any, int, str | None]:
        if _out_of_range(filters):
            return {"age_groups": [], "genders": [], "blood_types": []}, 0, EMPTY_NOTE
        data = _payload("demographics")["data"]
        if filters.gender:
            data["genders"] = [
                g for g in data["genders"] if g["gender"] == filters.gender
            ]
        row_count = sum(g["encounter_count"] for g in data["genders"])
        return data, row_count, DEV_MODE_NOTE

    def billing(self, filters: AnalyticsFilters) -> tuple[Any, int, str | None]:
        if _out_of_range(filters):
            empty = {
                "by_insurance_provider": [],
                "by_admission_type": [],
                "above_average": {"above_average_count": 0, "overall_avg_billing": None},
                "statistical_outliers": {
                    "outlier_count": None,
                    "lower_bound": None,
                    "upper_bound": None,
                },
                "excluded_invalid_billing_count": 0,
            }
            return empty, 0, EMPTY_NOTE
        data = _payload("billing")["data"]
        if filters.insurance_provider:
            data["by_insurance_provider"] = [
                r
                for r in data["by_insurance_provider"]
                if r["insurance_provider"] == filters.insurance_provider
            ]
        if filters.admission_type:
            data["by_admission_type"] = [
                r
                for r in data["by_admission_type"]
                if r["admission_type"] == filters.admission_type
            ]
        row_count = sum(r["encounter_count"] for r in data["by_insurance_provider"])
        return data, row_count, DEV_MODE_NOTE

    def test_results(self, filters: AnalyticsFilters) -> tuple[Any, int, str | None]:
        if _out_of_range(filters):
            return [], 0, EMPTY_NOTE
        rows = _payload("test-results")["data"]
        if filters.admission_type:
            rows = [r for r in rows if r["admission_type"] == filters.admission_type]
        if not rows:
            return [], 0, EMPTY_NOTE
        return rows, len(rows), DEV_MODE_NOTE

    def report_png(self, filters: AnalyticsFilters) -> bytes | None:
        """The Matplotlib report is Dev B's SHOULD-HAVE deliverable."""
        return None
