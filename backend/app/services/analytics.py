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
    """Shape KPI SQL output to the frozen KpiData API contract."""

    if not kpis:
        return {
            "total_encounters": 0,
            "avg_length_of_stay": None,
            "avg_billing_amount": None,
            "earliest_admission": None,
            "latest_admission": None,
        }

    return {
        "total_encounters": int(kpis.get("total_encounters") or 0),
        "avg_length_of_stay": (
            round(float(kpis["avg_los_days"]), 2)
            if kpis.get("avg_los_days") is not None
            else None
        ),
        "avg_billing_amount": (
            round(float(kpis["avg_billing_amount"]), 2)
            if kpis.get("avg_billing_amount") is not None
            else None
        ),
        "earliest_admission": kpis.get("min_admission_date"),
        "latest_admission": kpis.get("max_admission_date"),
    }


# ============================================================================
# Q2 — Admissions trend transformation
# ============================================================================

def transform_admissions_trend(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Transform monthly admissions results.

    Adds the SHOULD-HAVE rolling 3-month average using Pandas and
    maps the SQL/query-layer names to the frozen API contract.
    """

    df = _dataframe(records)

    if df.empty:
        return []

    df["admission_month"] = pd.to_datetime(
        df["admission_month"],
        format="%Y-%m",
        errors="coerce",
    )

    df = df.dropna(
        subset=["admission_month"]
    )

    df = df.sort_values(
        "admission_month"
    ).reset_index(drop=True)

    df["rolling_avg_3mo"] = (
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

    # Map SQL/query-layer names to the frozen API contract.
    result = pd.DataFrame({
        "month": df["admission_month"],
        "encounter_count": df["encounter_count"],
        "prev_month_count": df.get(
            "previous_month_count",
            pd.Series([None] * len(df)),
        ),
        "pct_change": df.get(
            "mom_change_percent",
            pd.Series([None] * len(df)),
        ),
        "rolling_avg_3mo": df["rolling_avg_3mo"],
    })

    result = _round_numeric(
        result,
        2,
    )

    return _records(result)

# ============================================================================
# Q3 — Top hospitals transformation
# ============================================================================

def transform_top_hospitals(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Shape top-hospital results for the API.

    The SQL layer already provides hospital_rank. It is retained as the
    API's required volume rank, while the SQL-only hospital_rank field
    is normalized into volume_rank.
    """

    df = _dataframe(records)

    if df.empty:
        return []

    # The frozen SQL query provides hospital_rank.
    # The API schema expects volume_rank.
    if "hospital_rank" in df.columns:
        df["volume_rank"] = df["hospital_rank"]
        df = df.drop(columns=["hospital_rank"])

    df = _round_numeric(df)

    return _records(df)

# ============================================================================
# Q4 — Condition distribution
# ============================================================================

def transform_condition_distribution(
    records: list[dict[str, Any]],
    los_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Combine Q4 condition-distribution results with Q5 average-LOS results.

    Q4 provides:
        - condition_name
        - condition_category
        - encounter_count

    Q5 provides:
        - condition_name
        - condition_category
        - avg_length_of_stay
        - encounter_count

    Pandas computes percentage_share from the Q4 encounter counts and
    merges the Q5 average LOS into the final frozen API contract.
    """

    df = _dataframe(records)

    if df.empty:
        return []

    if "encounter_count" not in df.columns:
        df["encounter_count"] = 0

    total = df["encounter_count"].sum()

    if total == 0:
        df["percentage_share"] = 0.0
    else:
        df["percentage_share"] = (
            df["encounter_count"]
            / total
            * 100
        )

    # Merge Q5 average LOS into the Q4 distribution results.
    if los_records:
        los_df = _dataframe(los_records)

        if not los_df.empty:
            los_columns = [
                "condition_name",
                "condition_category",
                "avg_length_of_stay",
            ]

            # Keep only columns that are actually available.
            los_columns = [
                column
                for column in los_columns
                if column in los_df.columns
            ]

            if (
                "condition_name" in los_columns
                and "condition_category" in los_columns
                and "avg_length_of_stay" in los_columns
            ):
                los_df = los_df[los_columns]

                df = df.merge(
                    los_df,
                    on=[
                        "condition_name",
                        "condition_category",
                    ],
                    how="left",
                )

    required_columns = [
        "condition_name",
        "condition_category",
        "encounter_count",
        "percentage_share",
        "avg_length_of_stay",
    ]

    if "avg_length_of_stay" not in df.columns:
        df["avg_length_of_stay"] = None

    for column in required_columns:
        if column not in df.columns:
            df[column] = None

    df = df[required_columns]

    df = _round_numeric(df, 2)

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
    Transform demographic breakdown into the frozen API contract.

    The SQL layer supplies the demographic rows. Pandas reshapes those
    rows into independent age-group, gender and blood-type distributions.
    """

    df = _dataframe(records)

    if df.empty:
        return {
            "age_groups": [],
            "genders": [],
            "blood_types": [],
        }

    # ---------------------------------------------------------------
    # Age groups
    # ---------------------------------------------------------------

    age_df = (
        df.groupby("age_group", as_index=False)["encounter_count"]
        .sum()
    )

    age_total = age_df["encounter_count"].sum()

    if age_total:
        age_df["percentage_share"] = (
            age_df["encounter_count"]
            / age_total
            * 100
        ).round(2)
    else:
        age_df["percentage_share"] = 0.0

    age_df = age_df[
        [
            "age_group",
            "encounter_count",
            "percentage_share",
        ]
    ]

    # ---------------------------------------------------------------
    # Gender
    # ---------------------------------------------------------------

    gender_df = (
        df.groupby("gender", as_index=False)["encounter_count"]
        .sum()
    )

    gender_total = gender_df["encounter_count"].sum()

    if gender_total:
        gender_df["percentage_share"] = (
            gender_df["encounter_count"]
            / gender_total
            * 100
        ).round(2)
    else:
        gender_df["percentage_share"] = 0.0

    gender_df = gender_df[
        [
            "gender",
            "encounter_count",
            "percentage_share",
        ]
    ]

    # ---------------------------------------------------------------
    # Blood type
    # ---------------------------------------------------------------

    blood_df = (
        df.groupby("blood_type", as_index=False)["encounter_count"]
        .sum()
    )

    blood_total = blood_df["encounter_count"].sum()

    if blood_total:
        blood_df["percentage_share"] = (
            blood_df["encounter_count"]
            / blood_total
            * 100
        ).round(2)
    else:
        blood_df["percentage_share"] = 0.0

    blood_df = blood_df[
        [
            "blood_type",
            "encounter_count",
            "percentage_share",
        ]
    ]

    return {
        "age_groups": _records(
            _round_numeric(age_df, 2)
        ),
        "genders": _records(
            _round_numeric(gender_df, 2)
        ),
        "blood_types": _records(
            _round_numeric(blood_df, 2)
        ),
    }


# ============================================================================
# Q7 / Q8 — Billing transformation
# ============================================================================

def transform_billing(
    billing: dict[str, Any],
) -> dict[str, Any]:
    """
    Transform billing analytics into the frozen BillingData API shape.

    The SQL query layer is responsible for applying filters and calculating
    billing aggregates. This layer converts those results into the frozen
    API response shape.

    The SQL layer returns:
        - by_insurance_provider
        - by_admission_type
        - above_average_billing
        - above_average_summary

    The detailed above-average result is intentionally limited to 100 rows,
    so the summary is used for the actual above-average count and filtered
    overall average.
    """

    insurance_rows = billing.get(
        "by_insurance_provider",
        [],
    )

    admission_rows = billing.get(
        "by_admission_type",
        [],
    )

    # ------------------------------------------------------------------
    # Billing by insurance provider
    # ------------------------------------------------------------------

    insurance_df = _dataframe(
        insurance_rows
    )

    if not insurance_df.empty:
        insurance_df = insurance_df.rename(
            columns={
                "valid_billing_encounters": "encounter_count",
                "avg_billing_amount": "avg_billing",
                "total_billing_amount": "total_billing",
            }
        )

        total_billing = insurance_df["total_billing"].sum()

        if total_billing > 0:
            insurance_df["pct_of_total_billing"] = (
                insurance_df["total_billing"]
                / total_billing
                * 100
            )
        else:
            insurance_df["pct_of_total_billing"] = 0.0

        insurance_df = _round_numeric(
            insurance_df,
            2,
        )

    # ------------------------------------------------------------------
    # Billing by admission type
    # ------------------------------------------------------------------

    admission_df = _dataframe(
        admission_rows
    )

    if not admission_df.empty:
        admission_df = admission_df.rename(
            columns={
                "valid_billing_encounters": "encounter_count",
                "avg_billing_amount": "avg_billing",
                "total_billing_amount": "total_billing",
            }
        )

        # total_billing is not part of the frozen admission-type
        # response, but it may be present in the SQL result.
        if "total_billing" in admission_df.columns:
            admission_df = admission_df.drop(
                columns=["total_billing"]
            )

        admission_df = _round_numeric(
            admission_df,
            2,
        )

    # ------------------------------------------------------------------
    # Above-average billing
    # ------------------------------------------------------------------
    #
    # The SQL layer returns:
    #
    #   above_average_billing -> detailed rows, limited to 100
    #   above_average_summary -> actual count + filtered average
    #
    # Therefore DO NOT use len(above_average_billing) as the count.
    # ------------------------------------------------------------------

    above_average_summary = billing.get(
        "above_average_summary",
        [],
    )

    if above_average_summary:
        summary = above_average_summary[0]

        above_average_count = summary.get(
            "above_average_count"
        )

        overall_avg_billing = summary.get(
            "overall_avg_billing"
        )

        if above_average_count is not None:
            above_average_count = int(
                above_average_count
            )

        if overall_avg_billing is not None:
            overall_avg_billing = round(
                float(overall_avg_billing),
                2,
            )
    else:
        above_average_count = 0
        overall_avg_billing = None

    above_average = {
        "above_average_count": above_average_count,
        "overall_avg_billing": overall_avg_billing,
    }

    # ------------------------------------------------------------------
    # Statistical outliers
    # ------------------------------------------------------------------

    billing_outliers = get_billing_iqr_outliers()

    # ------------------------------------------------------------------
    # Data quality
    # ------------------------------------------------------------------

    invalid_billing_count = int(
        get_data_quality_summary()["invalid_billing_rows"]
    )

    # ------------------------------------------------------------------
    # Final frozen API shape
    # ------------------------------------------------------------------

    return {
        "by_insurance_provider": (
            _records(insurance_df)
            if not insurance_df.empty
            else []
        ),
        "by_admission_type": (
            _records(admission_df)
            if not admission_df.empty
            else []
        ),
        "above_average": above_average,
        "statistical_outliers": {
            "outlier_count": billing_outliers["outlier_count"],
            "lower_bound": billing_outliers["lower_bound"],
            "upper_bound": billing_outliers["upper_bound"],
        },
        "excluded_invalid_billing_count": invalid_billing_count,
    }
def transform_test_results(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Shape test-result distribution by admission type."""

    result: list[dict[str, Any]] = []

    for row in records:
        result.append({
            "admission_type": row.get("admission_type"),
            "test_result": row.get("test_result"),
            "encounter_count": int(
                row.get("encounter_count") or 0
            ),
        })

    return result


# ============================================================================
# Data-quality summary
# ============================================================================

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
    """Dev A integration builder for condition distribution and LOS."""

    del conn

    filter_kwargs = _filter_kwargs(filters)

    # Q4: condition distribution
    condition_data = get_condition_distribution(
        **filter_kwargs
    )

    # Q5: average length of stay by condition
    los_data = get_los_by_condition_category(
        **filter_kwargs
    )

    # Combine Q4 percentage-share data with Q5 average-LOS data.
    return transform_condition_distribution(
        condition_data,
        los_data,
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
        data,
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