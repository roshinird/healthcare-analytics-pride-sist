"""
Healthcare Analytics — Pandas / NumPy Analytics Layer

Dev B responsibility:
- Transform SQL query results into API/dashboard-friendly structures.
- Perform percentage-share calculations for distribution analytics.
- Provide the demographic 2-dimensional pivot required by the architecture.
- Produce data-quality statistics for invalid billing records.
- Provide NumPy-based IQR billing outlier analysis.
- Provide rolling-average admissions analytics as a SHOULD-HAVE feature.

Integration contract:
- Exposes build_* functions expected by Dev A's LiveDataSource.
- Each build_* function accepts (conn, filters).
- SQL remains in app.queries.
- Pandas performs transformation/shaping.
- NumPy performs statistical calculations.

This module must not:
- create or modify database tables;
- execute arbitrary SQL;
- introduce patient identity;
- introduce additional dimensions;
- replace the frozen SQL analytics layer.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..database import get_connection
from ..queries import (
    get_admissions_trend,
    get_billing_analysis,
    get_condition_distribution,
    get_demographics,
    get_kpis,
    get_los_by_condition_category,
    get_test_results,
    get_top_hospitals,
)


# ============================================================================
# Helpers
# ============================================================================

def _filter_kwargs(filters: Any) -> dict[str, Any]:
    """
    Convert the frozen AnalyticsFilters object into keyword arguments
    understood by app.queries.

    Supports both a Pydantic AnalyticsFilters object and a dictionary,
    which makes the integration layer easier to test independently.
    """

    if isinstance(filters, dict):
        return {
            "start_date": filters.get("start_date"),
            "end_date": filters.get("end_date"),
            "condition": filters.get("condition"),
            "admission_type": filters.get("admission_type"),
            "insurance_provider": filters.get("insurance_provider"),
            "gender": filters.get("gender"),
        }

    return {
        "start_date": getattr(filters, "start_date", None),
        "end_date": getattr(filters, "end_date", None),
        "condition": getattr(filters, "condition", None),
        "admission_type": getattr(filters, "admission_type", None),
        "insurance_provider": getattr(filters, "insurance_provider", None),
        "gender": getattr(filters, "gender", None),
    }


def _dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Create a DataFrame safely from SQL result dictionaries."""

    return pd.DataFrame(records)


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Convert a DataFrame to JSON-compatible records.

    NaN / infinite values are converted to None so FastAPI/Pydantic
    can serialize the result safely.
    """

    if df.empty:
        return []

    cleaned = df.replace([np.inf, -np.inf], np.nan)

    cleaned = cleaned.astype(object).where(
        pd.notna(cleaned),
        None,
    )

    return cleaned.to_dict(orient="records")


def _round_numeric(
    df: pd.DataFrame,
    decimals: int = 2,
) -> pd.DataFrame:
    """Round numeric columns without modifying non-numeric fields."""

    result = df.copy()

    numeric_columns = result.select_dtypes(
        include=["number"]
    ).columns

    if len(numeric_columns) > 0:
        result[numeric_columns] = result[numeric_columns].round(
            decimals
        )

    return result


# ============================================================================
# Q1 — KPI transformation
# ============================================================================

def transform_kpis(
    kpis: dict[str, Any],
) -> dict[str, Any]:
    """Shape KPI SQL output for the API."""

    df = _dataframe([kpis])

    if df.empty:
        return {}

    df = _round_numeric(df, 2)

    return _records(df)[0]


# ============================================================================
# Q2 — Admissions trend transformation
# ============================================================================

def transform_admissions_trend(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Transform monthly admissions results.

    Adds the SHOULD-HAVE rolling 3-month average using Pandas.
    """

    df = _dataframe(records)

    if df.empty:
        return []

    df["admission_month"] = pd.to_datetime(
        df["admission_month"],
        format="%Y-%m",
        errors="coerce",
    )

    df = df.sort_values(
        "admission_month"
    ).reset_index(drop=True)

    df["rolling_3_month_avg"] = (
        df["encounter_count"]
        .rolling(
            window=3,
            min_periods=1,
        )
        .mean()
        .round(2)
    )

    df["admission_month"] = (
        df["admission_month"]
        .dt.strftime("%Y-%m")
    )

    df = _round_numeric(df, 2)

    return _records(df)


# ============================================================================
# Q3 — Top hospitals transformation
# ============================================================================

def transform_top_hospitals(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Shape top-hospital results."""

    df = _dataframe(records)

    if df.empty:
        return []

    df = _round_numeric(df)

    return _records(df)


# ============================================================================
# Q4 — Condition distribution
# ============================================================================

def transform_condition_distribution(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Calculate percentage share of encounters for each condition.

    Percentage-share calculation is intentionally performed in Pandas.
    """

    df = _dataframe(records)

    if df.empty:
        return []

    total = df["encounter_count"].sum()

    if total == 0:
        df["percentage_share"] = 0.0
    else:
        df["percentage_share"] = (
            df["encounter_count"]
            / total
            * 100
        ).round(2)

    df = _round_numeric(df)

    return _records(df)


# ============================================================================
# Q5 — LOS by condition category
# ============================================================================

def transform_los_by_condition_category(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Shape average LOS by medical-condition category."""

    df = _dataframe(records)

    if df.empty:
        return []

    df = _round_numeric(df, 2)

    return _records(df)


# ============================================================================
# Q6 — Demographic transformation + Pandas pivot
# ============================================================================

def transform_demographics(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Transform demographic breakdown.

    Returns:
        rows  -> flat age-group × gender × blood-type data
        pivot -> age-group × gender Pandas pivot
    """

    df = _dataframe(records)

    if df.empty:
        return {
            "rows": [],
            "pivot": [],
        }

    df = _round_numeric(df)

    pivot = pd.pivot_table(
        df,
        index="age_group",
        columns="gender",
        values="encounter_count",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    pivot.columns.name = None
    pivot = pivot.rename_axis(
        None,
        axis=1,
    )

    preferred_columns = [
        "age_group",
        "Female",
        "Male",
    ]

    existing_columns = [
        column
        for column in preferred_columns
        if column in pivot.columns
    ]

    remaining_columns = [
        column
        for column in pivot.columns
        if column not in existing_columns
    ]

    pivot = pivot[
        existing_columns + remaining_columns
    ]

    pivot = _round_numeric(
        pivot,
        2,
    )

    return {
        "rows": _records(df),
        "pivot": _records(pivot),
    }


# ============================================================================
# Q7 / Q8 — Billing transformation
# ============================================================================

def transform_billing(
    billing: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """
    Transform billing analytics.

    Includes:
    - billing by insurance provider;
    - billing by admission type;
    - above-average billing encounters.
    """

    result: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Insurance provider
    # ------------------------------------------------------------------

    insurance_df = _dataframe(
        billing.get(
            "by_insurance_provider",
            [],
        )
    )

    if not insurance_df.empty:
        total_valid = insurance_df[
            "valid_billing_encounters"
        ].sum()

        if total_valid == 0:
            insurance_df[
                "percentage_share"
            ] = 0.0
        else:
            insurance_df[
                "percentage_share"
            ] = (
                insurance_df[
                    "valid_billing_encounters"
                ]
                / total_valid
                * 100
            ).round(2)

        insurance_df = _round_numeric(
            insurance_df,
            2,
        )

    result[
        "by_insurance_provider"
    ] = _records(insurance_df)

    # ------------------------------------------------------------------
    # Admission type
    # ------------------------------------------------------------------

    admission_df = _dataframe(
        billing.get(
            "by_admission_type",
            [],
        )
    )

    if not admission_df.empty:
        total_valid = admission_df[
            "valid_billing_encounters"
        ].sum()

        if total_valid == 0:
            admission_df[
                "percentage_share"
            ] = 0.0
        else:
            admission_df[
                "percentage_share"
            ] = (
                admission_df[
                    "valid_billing_encounters"
                ]
                / total_valid
                * 100
            ).round(2)

        admission_df = _round_numeric(
            admission_df,
            2,
        )

    result[
        "by_admission_type"
    ] = _records(admission_df)

    # ------------------------------------------------------------------
    # Above-average billing
    # ------------------------------------------------------------------

    above_average_df = _dataframe(
        billing.get(
            "above_average_billing",
            [],
        )
    )

    if not above_average_df.empty:
        above_average_df = _round_numeric(
            above_average_df,
            2,
        )

    result[
        "above_average_billing"
    ] = _records(
        above_average_df
    )

    return result


# ============================================================================
# Q9 — Test-result distribution
# ============================================================================

def transform_test_results(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Calculate test-result percentage shares within each admission type.
    """

    df = _dataframe(records)

    if df.empty:
        return []

    totals = (
        df.groupby(
            "admission_type"
        )["encounter_count"]
        .transform("sum")
    )

    df["percentage_share"] = np.where(
        totals > 0,
        (
            df["encounter_count"]
            / totals
            * 100
        ),
        0.0,
    )

    df["percentage_share"] = (
        df["percentage_share"]
        .round(2)
    )

    df = _round_numeric(
        df,
        2,
    )

    return _records(df)


# ============================================================================
# Data-quality summary
# ============================================================================

def get_data_quality_summary() -> dict[str, Any]:
    """
    Produce the required data-quality summary.

    Metrics:
    - total source/encounter rows;
    - valid billing rows;
    - invalid billing rows;
    - invalid billing percentage.
    """

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total_encounters,

                SUM(
                    CASE
                        WHEN billing_is_valid = 1
                        THEN 1
                        ELSE 0
                    END
                ) AS valid_billing_rows,

                SUM(
                    CASE
                        WHEN billing_is_valid = 0
                        THEN 1
                        ELSE 0
                    END
                ) AS invalid_billing_rows

            FROM encounters;
            """
        ).fetchone()

    finally:
        connection.close()

    total = int(
        row["total_encounters"] or 0
    )

    valid = int(
        row["valid_billing_rows"] or 0
    )

    invalid = int(
        row["invalid_billing_rows"] or 0
    )

    invalid_percentage = (
        invalid / total * 100
        if total > 0
        else 0.0
    )

    return {
        "total_encounters": total,
        "valid_billing_rows": valid,
        "invalid_billing_rows": invalid,
        "invalid_billing_percentage": round(
            invalid_percentage,
            2,
        ),
    }


# ============================================================================
# NumPy — IQR billing outlier analysis
# ============================================================================

def get_billing_iqr_outliers() -> dict[str, Any]:
    """
    Perform IQR-based billing outlier detection.

    Only valid billing records are analyzed.
    """

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                e.encounter_id,
                e.age,
                e.gender,
                c.condition_name,
                e.hospital_name,
                e.insurance_provider,
                e.admission_date,
                e.admission_type,
                e.billing_amount

            FROM encounters AS e

            JOIN ref_medical_condition AS c
                ON e.condition_id = c.condition_id

            WHERE e.billing_is_valid = 1

            ORDER BY e.billing_amount DESC;
            """
        ).fetchall()

    finally:
        connection.close()

    df = _dataframe(
        [dict(row) for row in rows]
    )

    if df.empty:
        return {
            "q1": None,
            "q3": None,
            "iqr": None,
            "lower_bound": None,
            "upper_bound": None,
            "valid_billing_count": 0,
            "outlier_count": 0,
            "outlier_percentage": 0.0,
            "outlier_rows": [],
        }

    values = (
        df["billing_amount"]
        .astype(float)
        .to_numpy()
    )

    q1 = float(
        np.percentile(
            values,
            25,
        )
    )

    q3 = float(
        np.percentile(
            values,
            75,
        )
    )

    iqr = q3 - q1

    lower_bound = (
        q1 - 1.5 * iqr
    )

    upper_bound = (
        q3 + 1.5 * iqr
    )

    outliers = df[
        (
            df["billing_amount"]
            < lower_bound
        )
        |
        (
            df["billing_amount"]
            > upper_bound
        )
    ].copy()

    valid_count = len(df)
    outlier_count = len(outliers)

    outlier_percentage = (
        outlier_count
        / valid_count
        * 100
        if valid_count > 0
        else 0.0
    )

    outliers = outliers.sort_values(
        "billing_amount",
        ascending=False,
    )

    outliers = _round_numeric(
        outliers,
        2,
    )

    return {
        "q1": round(q1, 2),
        "q3": round(q3, 2),
        "iqr": round(iqr, 2),
        "lower_bound": round(
            lower_bound,
            2,
        ),
        "upper_bound": round(
            upper_bound,
            2,
        ),
        "valid_billing_count": valid_count,
        "outlier_count": outlier_count,
        "outlier_percentage": round(
            outlier_percentage,
            2,
        ),
        "outlier_rows": _records(
            outliers
        ),
    }


# ============================================================================
# Dev A integration builders
# ============================================================================

def build_kpis(
    conn: Any,
    filters: Any,
) -> dict[str, Any]:
    """Dev A integration builder for /api/kpis."""

    del conn

    data = get_kpis(
        **_filter_kwargs(filters)
    )

    return transform_kpis(data)


def build_admissions_trend(
    conn: Any,
    filters: Any,
) -> list[dict[str, Any]]:
    """Dev A integration builder for admissions trend."""

    del conn

    data = get_admissions_trend(
        **_filter_kwargs(filters)
    )

    return transform_admissions_trend(
        data
    )


def build_top_hospitals(
    conn: Any,
    filters: Any,
) -> list[dict[str, Any]]:
    """Dev A integration builder for top hospitals."""

    del conn

    data = get_top_hospitals(
        **_filter_kwargs(filters)
    )

    return transform_top_hospitals(
        data
    )


def build_conditions(
    conn: Any,
    filters: Any,
) -> list[dict[str, Any]]:
    """Dev A integration builder for condition distribution."""

    del conn

    data = get_condition_distribution(
        **_filter_kwargs(filters)
    )

    return transform_condition_distribution(
        data
    )


def build_demographics(
    conn: Any,
    filters: Any,
) -> dict[str, Any]:
    """Dev A integration builder for demographics."""

    del conn

    data = get_demographics(
        **_filter_kwargs(filters)
    )

    return transform_demographics(
        data
    )


def build_billing(
    conn: Any,
    filters: Any,
) -> dict[str, Any]:
    """Dev A integration builder for billing analytics."""

    del conn

    data = get_billing_analysis(
        **_filter_kwargs(filters)
    )

    return transform_billing(
        data
    )


def build_test_results(
    conn: Any,
    filters: Any,
) -> list[dict[str, Any]]:
    """Dev A integration builder for test-result analytics."""

    del conn

    data = get_test_results(
        **_filter_kwargs(filters)
    )

    return transform_test_results(
        data
    )


# ============================================================================
# Complete transformation pipeline
# ============================================================================

def get_transformed_analytics(
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    condition: str | None = None,
    admission_type: str | None = None,
    insurance_provider: str | None = None,
    gender: str | None = None,
) -> dict[str, Any]:
    """
    Execute the SQL analytics layer and apply the complete
    Pandas/NumPy transformation layer.

    Primarily used for integration tests and local validation.
    """

    filters = {
        "start_date": start_date,
        "end_date": end_date,
        "condition": condition,
        "admission_type": admission_type,
        "insurance_provider": insurance_provider,
        "gender": gender,
    }

    kpis = get_kpis(
        **filters
    )

    admissions_trend = get_admissions_trend(
        **filters
    )

    top_hospitals = get_top_hospitals(
        **filters
    )

    conditions = get_condition_distribution(
        **filters
    )

    los_by_condition_category = (
        get_los_by_condition_category(
            **filters
        )
    )

    demographics = get_demographics(
        **filters
    )

    billing = get_billing_analysis(
        **filters
    )

    test_results = get_test_results(
        **filters
    )

    return {
        "kpis": transform_kpis(
            kpis
        ),

        "admissions_trend":
            transform_admissions_trend(
                admissions_trend
            ),

        "top_hospitals":
            transform_top_hospitals(
                top_hospitals
            ),

        "conditions":
            transform_condition_distribution(
                conditions
            ),

        "los_by_condition_category":
            transform_los_by_condition_category(
                los_by_condition_category
            ),

        "demographics":
            transform_demographics(
                demographics
            ),

        "billing":
            transform_billing(
                billing
            ),

        "test_results":
            transform_test_results(
                test_results
            ),

        "data_quality":
            get_data_quality_summary(),

        "billing_iqr_outliers":
            get_billing_iqr_outliers(),
    }