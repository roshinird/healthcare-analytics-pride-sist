"""Data-source resolution — the integration seam between Dev A and Dev B.

Owner: Dev A.
Spec: docs/07-backend-architecture.md §3, docs/12-dev-workflow-split.md §6.

The routers never care where a payload came from. They ask this module for a data
source and get one of two implementations:

* ``LiveDataSource``  — Dev B's `services/queries.py` (SQL) + `services/analytics.py`
  (Pandas) reading the seeded SQLite file. Used whenever the database is present
  **and** the builder functions are importable.
* ``DevFixtureDataSource`` — contract-shaped static fixtures. Used until then.

Integration contract for Dev B
------------------------------
`app/services/analytics.py` should expose one builder per endpoint, each taking a
`sqlite3.Connection` and an `AnalyticsFilters` instance and returning the `data`
block exactly as specified in docs/06-api-contract.md::

    build_kpis(conn, filters)             -> dict
    build_admissions_trend(conn, filters) -> list[dict]
    build_top_hospitals(conn, filters)    -> list[dict]
    build_conditions(conn, filters)       -> list[dict]
    build_demographics(conn, filters)     -> dict
    build_billing(conn, filters)          -> dict
    build_test_results(conn, filters)     -> list[dict]

Common alternative names (``get_kpis``, ``kpis``, …) are also accepted so a naming
difference cannot block integration. If a builder is missing while the database is
present, that single endpoint falls back to fixtures with a visible `meta.note`
instead of failing the whole dashboard.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Callable, Optional

from app.database import connection_scope, database_is_ready
from app.schemas.params import AnalyticsFilters
from app.services.dev_fixtures import DevFixtureDataSource

logger = logging.getLogger("healthcare_analytics")

_ANALYTICS_MODULE = "app.services.analytics"
_QUERIES_MODULE = "app.services.queries"

PARTIAL_NOTE = (
    "This endpoint is still served from development fixtures — the corresponding "
    "analytics builder is not available yet."
)


def _load_module(name: str):
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


def _resolve(module, endpoint: str) -> Optional[Callable[..., Any]]:
    """Find Dev B's builder for `endpoint`, tolerating a few naming conventions."""
    if module is None:
        return None
    for candidate in (f"build_{endpoint}", f"get_{endpoint}", endpoint):
        fn = getattr(module, candidate, None)
        if callable(fn):
            return fn
    return None


def _row_count(data: Any) -> int:
    """Return a meaningful row/encounter count for an endpoint payload."""

    if isinstance(data, list):
        return len(data)

    if isinstance(data, dict):
        # KPI-style payloads expose their encounter count directly.
        total_encounters = data.get("total_encounters")
        if isinstance(total_encounters, int):
            return total_encounters

        # Billing is a structured dictionary. Its insurance-provider rows
        # represent grouped billing data, so use the sum of their valid
        # encounter counts rather than returning the generic fallback of 1.
        insurance_rows = data.get("by_insurance_provider")
        if isinstance(insurance_rows, list):
            total = 0
            found_count = False

            for row in insurance_rows:
                if not isinstance(row, dict):
                    continue

                count = row.get("encounter_count")
                if isinstance(count, int):
                    total += count
                    found_count = True

            if found_count:
                return total

        row_count = data.get("row_count")
        if isinstance(row_count, int):
            return row_count

        return 1 if data else 0

    return 0


class LiveDataSource:
    """Delegates to Dev B's SQL + Pandas layer against the seeded SQLite file."""

    mode = "live"
    is_live = True

    def __init__(self, analytics_module, queries_module) -> None:
        self._analytics = analytics_module
        self._queries = queries_module
        self._fallback = DevFixtureDataSource()

    # -- reference values ---------------------------------------------------
    def _distinct(self, column: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
        # `column` is chosen from a fixed internal whitelist, never from a request
        # (docs/10-security-privacy.md §1.1).
        allowed = {
            "condition_name": "SELECT condition_name FROM ref_medical_condition ORDER BY 1",
            "insurance_provider": (
                "SELECT DISTINCT insurance_provider FROM encounters ORDER BY 1"
            ),
        }
        sql = allowed.get(column)
        if sql is None:
            return fallback
        try:
            with connection_scope() as conn:
                return tuple(row[0] for row in conn.execute(sql).fetchall())
        except Exception:  # noqa: BLE001 - reference lookup must never 500 a request
            logger.warning("Reference lookup failed for %s; using fixture values", column)
            return fallback

    def known_conditions(self) -> tuple[str, ...]:
        return self._distinct("condition_name", self._fallback.known_conditions())

    def known_insurance_providers(self) -> tuple[str, ...]:
        return self._distinct(
            "insurance_provider", self._fallback.known_insurance_providers()
        )

    # -- endpoints ----------------------------------------------------------
    def _call(
        self, endpoint: str, filters: AnalyticsFilters
    ) -> tuple[Any, int, Optional[str]]:
        builder = _resolve(self._analytics, endpoint) or _resolve(self._queries, endpoint)
        if builder is None:
            logger.warning("No analytics builder found for '%s'; serving fixtures", endpoint)
            data, count, _ = getattr(self._fallback, endpoint)(filters)
            return data, count, PARTIAL_NOTE

        with connection_scope() as conn:
            data = builder(conn, filters)

        count = _row_count(data)
        note = "No encounters matched the given filters." if count == 0 else None
        return data, count, note

    def kpis(self, filters):  # noqa: D102
        return self._call("kpis", filters)

    def admissions_trend(self, filters):  # noqa: D102
        return self._call("admissions_trend", filters)

    def top_hospitals(self, filters):  # noqa: D102
        return self._call("top_hospitals", filters)

    def conditions(self, filters):  # noqa: D102
        return self._call("conditions", filters)

    def demographics(self, filters):  # noqa: D102
        return self._call("demographics", filters)

    def billing(self, filters):  # noqa: D102
        return self._call("billing", filters)

    def test_results(self, filters):  # noqa: D102
        return self._call("test_results", filters)

    def report_png(self, filters: AnalyticsFilters) -> Optional[bytes]:
        """SHOULD HAVE — Dev B's `services/report.py`. Absent means HTTP 501."""
        report_module = _load_module("app.services.report")
        generator = _resolve(report_module, "summary_png") or getattr(
            report_module, "generate_summary_png", None
        )
        if not callable(generator):
            return None
        with connection_scope() as conn:
            return generator(conn, filters)


def get_datasource():
    """Return the best available data source for this deployment.

    Recomputed per request (cheap: two cached module lookups plus one `stat`) so a
    freshly seeded database is picked up without restarting the server.
    """
    if database_is_ready():
        analytics_module = _load_module(_ANALYTICS_MODULE)
        queries_module = _load_module(_QUERIES_MODULE)
        if analytics_module or queries_module:
            return LiveDataSource(analytics_module, queries_module)
        logger.warning(
            "Database is present but no analytics/queries module was importable; "
            "serving development fixtures."
        )
    return DevFixtureDataSource()
