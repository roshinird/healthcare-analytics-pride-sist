"""
Healthcare Analytics — SQL Analytics Query Layer

Dev B responsibility:
- Implement all 9 MUST-HAVE analytical questions.
- Keep analytical logic in SQL rather than the FastAPI/router layer.
- Demonstrate the required SQL concepts:
    SELECT, WHERE, ORDER BY, JOIN, GROUP BY, HAVING,
    aggregate functions, subqueries, CTEs, window functions,
    CASE expressions, date functions, and the frozen database view.
- Support the frozen dashboard filters.

Database model:
    encounters
        -> many-to-one ->
    ref_medical_condition

The vw_encounter_enriched view is used where appropriate to keep
condition-related queries readable while preserving the one-to-many
fan-out safety guarantee.

IMPORTANT:
- All user-controlled filter values are parameterized.
- No patient identity, doctor, room, medication, or longitudinal
  analytics are introduced.
- Invalid billing rows are excluded from monetary analytics using
  billing_is_valid = 1.
- Encounter counts that describe the dataset may explicitly include
  invalid-billing rows where appropriate.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .database import get_connection


# ============================================================================
# Filter helper
# ============================================================================

def _build_filters(
    *,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    condition: str | None = None,
    admission_type: str | None = None,
    insurance_provider: str | None = None,
    gender: str | None = None,
    table_alias: str = "e",
    condition_alias: str = "c",
) -> tuple[str, list[Any]]:
    """
    Build a parameterized WHERE clause for the frozen dashboard filters.

    Returns:
        (sql_fragment, parameters)

    The returned SQL fragment either contains no WHERE clause or starts
    with "WHERE". All values are passed separately as SQLite parameters.

    The table_alias parameter allows the helper to work with either
    encounters/ref_medical_condition joins or the enriched analytical view.
    """

    clauses: list[str] = []
    params: list[Any] = []

    if start_date is not None:
        clauses.append(f"{table_alias}.admission_date >= ?")
        params.append(str(start_date))

    if end_date is not None:
        clauses.append(f"{table_alias}.admission_date <= ?")
        params.append(str(end_date))

    if condition is not None and condition.strip():
        clauses.append(f"{condition_alias}.condition_name = ?")
        params.append(condition.strip())

    if admission_type is not None and admission_type.strip():
        clauses.append(f"{table_alias}.admission_type = ?")
        params.append(admission_type.strip())

    if insurance_provider is not None and insurance_provider.strip():
        clauses.append(f"{table_alias}.insurance_provider = ?")
        params.append(insurance_provider.strip())

    if gender is not None and gender.strip():
        clauses.append(f"{table_alias}.gender = ?")
        params.append(gender.strip())

    if not clauses:
        return "", params

    return "WHERE " + " AND ".join(clauses), params


def _rows_to_dicts(rows: list[Any]) -> list[dict[str, Any]]:
    """Convert sqlite3.Row objects into ordinary dictionaries."""

    return [dict(row) for row in rows]


# ============================================================================
# Q1 — KPI Summary
# ============================================================================

def get_kpis(
    *,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    condition: str | None = None,
    admission_type: str | None = None,
    insurance_provider: str | None = None,
    gender: str | None = None,
) -> dict[str, Any]:
    """
    Q1:
        KPI summary:
        - total encounters
        - average length of stay
        - average billing
        - minimum admission date
        - maximum admission date

    SQL concepts:
        SELECT, WHERE, JOIN, aggregate functions.
    """

    where_sql, params = _build_filters(
        start_date=start_date,
        end_date=end_date,
        condition=condition,
        admission_type=admission_type,
        insurance_provider=insurance_provider,
        gender=gender,
    )

    # _build_filters() normally targets condition_name using the
    # supplied table alias. Q1 joins ref_medical_condition as `c`,
    # so correct the condition predicate for this query.
    if condition is not None and condition.strip():
        where_sql = where_sql.replace(
            "e.condition_name = ?",
            "c.condition_name = ?",
        )

    query = f"""
        SELECT
            COUNT(*) AS total_encounters,
            ROUND(AVG(e.length_of_stay_days), 2) AS avg_los_days,
            ROUND(
                AVG(
                    CASE
                        WHEN e.billing_is_valid = 1
                        THEN e.billing_amount
                    END
                ),
                2
            ) AS avg_billing_amount,
            MIN(e.admission_date) AS min_admission_date,
            MAX(e.admission_date) AS max_admission_date,
            SUM(
                CASE
                    WHEN e.billing_is_valid = 0 THEN 1
                    ELSE 0
                END
            ) AS invalid_billing_count
        FROM encounters AS e
        JOIN ref_medical_condition AS c
            ON e.condition_id = c.condition_id
        {where_sql};
    """

    connection = get_connection()

    try:
        row = connection.execute(query, params).fetchone()
        return dict(row)
    finally:
        connection.close()


# ============================================================================
# Q2 — Monthly Admissions Trend + Month-over-Month Change
# ============================================================================

def get_admissions_trend(
    *,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    condition: str | None = None,
    admission_type: str | None = None,
    insurance_provider: str | None = None,
    gender: str | None = None,
) -> list[dict[str, Any]]:
    """
    Q2:
        Monthly admissions trend and month-over-month percentage change.

    SQL concepts:
        CTE, date functions, GROUP BY, aggregate functions,
        window function (LAG), ORDER BY.
    """

    where_sql, params = _build_filters(
        start_date=start_date,
        end_date=end_date,
        condition=condition,
        admission_type=admission_type,
        insurance_provider=insurance_provider,
        gender=gender,
    )
    if condition is not None and condition.strip():
        where_sql = where_sql.replace(
            "e.condition_name = ?",
            "c.condition_name = ?",
        )
    query = f"""
        WITH monthly_admissions AS (
            SELECT
                strftime('%Y-%m', e.admission_date) AS admission_month,
                COUNT(*) AS encounter_count
            FROM encounters AS e
            JOIN ref_medical_condition AS c
                ON e.condition_id = c.condition_id
            {where_sql}
            GROUP BY strftime('%Y-%m', e.admission_date)
        ),
        monthly_with_previous AS (
            SELECT
                admission_month,
                encounter_count,
                LAG(encounter_count) OVER (
                    ORDER BY admission_month
                ) AS previous_month_count
            FROM monthly_admissions
        )
        SELECT
            admission_month,
            encounter_count,
            previous_month_count,
            CASE
                WHEN previous_month_count IS NULL
                     OR previous_month_count = 0
                THEN NULL
                ELSE ROUND(
                    (
                        CAST(encounter_count AS REAL)
                        - previous_month_count
                    )
                    * 100.0
                    / previous_month_count,
                    2
                )
            END AS mom_change_percent
        FROM monthly_with_previous
        ORDER BY admission_month;
    """

    connection = get_connection()

    try:
        rows = connection.execute(query, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        connection.close()


# ============================================================================
# Q3 — Top 10 Hospitals
# ============================================================================

def get_top_hospitals(
    *,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    condition: str | None = None,
    admission_type: str | None = None,
    insurance_provider: str | None = None,
    gender: str | None = None,
) -> list[dict[str, Any]]:
    """
    Q3:
        Top 10 hospitals by encounter volume.

    SQL concepts:
        GROUP BY, COUNT, window function (RANK), ORDER BY, LIMIT.
    """

    where_sql, params = _build_filters(
        start_date=start_date,
        end_date=end_date,
        condition=condition,
        admission_type=admission_type,
        insurance_provider=insurance_provider,
        gender=gender,
    )
    if condition is not None and condition.strip():
        where_sql = where_sql.replace(
            "e.condition_name = ?",
            "c.condition_name = ?",
        )
    query = f"""
        WITH hospital_counts AS (
            SELECT
                e.hospital_name,
                COUNT(*) AS encounter_count
            FROM encounters AS e
            JOIN ref_medical_condition AS c
                ON e.condition_id = c.condition_id
            {where_sql}
            GROUP BY e.hospital_name
        ),
        ranked_hospitals AS (
            SELECT
                hospital_name,
                encounter_count,
                RANK() OVER (
                    ORDER BY encounter_count DESC
                ) AS hospital_rank
            FROM hospital_counts
        )
        SELECT
            hospital_name,
            encounter_count,
            hospital_rank
        FROM ranked_hospitals
        ORDER BY hospital_rank, hospital_name
        LIMIT 10;
    """

    connection = get_connection()

    try:
        rows = connection.execute(query, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        connection.close()


# ============================================================================
# Q4 — Medical Condition Distribution
# ============================================================================

def get_condition_distribution(
    *,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    condition: str | None = None,
    admission_type: str | None = None,
    insurance_provider: str | None = None,
    gender: str | None = None,
) -> list[dict[str, Any]]:
    """
    Q4:
        Distribution of encounters across medical conditions.

    SQL concepts:
        GROUP BY, HAVING, aggregate functions, ORDER BY.

    Percentage-share calculation is intentionally left to Pandas,
    per the frozen architecture.
    """

    where_sql, params = _build_filters(
        start_date=start_date,
        end_date=end_date,
        condition=condition,
        admission_type=admission_type,
        insurance_provider=insurance_provider,
        gender=gender,
        table_alias="e",
    )

    query = f"""
        SELECT
            e.condition_name,
            e.condition_category,
            COUNT(*) AS encounter_count
        FROM vw_encounter_enriched AS e
        {where_sql}
        GROUP BY
            e.condition_name,
            e.condition_category
        HAVING COUNT(*) > 0
        ORDER BY encounter_count DESC, e.condition_name;
    """

    connection = get_connection()

    try:
        rows = connection.execute(query, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        connection.close()

# ============================================================================
# Q5 — Average LOS by Condition Category and Condition
# ============================================================================

def get_los_by_condition_category(
    *,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    condition: str | None = None,
    admission_type: str | None = None,
    insurance_provider: str | None = None,
    gender: str | None = None,
) -> list[dict[str, Any]]:
    """
    Q5:
        Average length of stay by medical condition and condition category.

    Grain:
        Condition name × condition category.

    Source:
        Frozen vw_encounter_enriched view.

    SQL concepts:
        JOIN, GROUP BY, AVG, ORDER BY.

    The frozen specification requires both condition_name and
    condition_category in the analytical grain.
    """

    # The frozen enriched view exposes condition_name and
    # condition_category directly. The filter helper expects the
    # condition table alias "c", so use the view as alias "e" and
    # build the condition predicate explicitly below.
    clauses: list[str] = []
    params: list[Any] = []

    if start_date is not None:
        clauses.append("e.admission_date >= ?")
        params.append(str(start_date))

    if end_date is not None:
        clauses.append("e.admission_date <= ?")
        params.append(str(end_date))

    if condition is not None and condition.strip():
        clauses.append("e.condition_name = ?")
        params.append(condition.strip())

    if admission_type is not None and admission_type.strip():
        clauses.append("e.admission_type = ?")
        params.append(admission_type.strip())

    if insurance_provider is not None and insurance_provider.strip():
        clauses.append("e.insurance_provider = ?")
        params.append(insurance_provider.strip())

    if gender is not None and gender.strip():
        clauses.append("e.gender = ?")
        params.append(gender.strip())

    where_sql = (
        "WHERE " + " AND ".join(clauses)
        if clauses
        else ""
    )

    query = f"""
        SELECT
            e.condition_name,
            e.condition_category,
            ROUND(AVG(e.length_of_stay_days), 2) AS avg_length_of_stay,
            COUNT(*) AS encounter_count
        FROM vw_encounter_enriched AS e
        {where_sql}
        GROUP BY
            e.condition_name,
            e.condition_category
        ORDER BY avg_length_of_stay DESC, e.condition_name;
    """

    connection = get_connection()

    try:
        rows = connection.execute(query, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        connection.close()


# ============================================================================
# Q6 — Demographic Breakdown
# ============================================================================

def get_demographics(
    *,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    condition: str | None = None,
    admission_type: str | None = None,
    insurance_provider: str | None = None,
    gender: str | None = None,
) -> list[dict[str, Any]]:
    """
    Q6:
        Demographic breakdown:
            age group × gender × blood type.

    SQL concepts:
        CASE, GROUP BY, ORDER BY, aggregate functions.

    Age groups:
        0-17
        18-34
        35-49
        50-64
        65+
    """

    where_sql, params = _build_filters(
        start_date=start_date,
        end_date=end_date,
        condition=condition,
        admission_type=admission_type,
        insurance_provider=insurance_provider,
        gender=gender,
    )

    query = f"""
        SELECT
            CASE
                WHEN e.age BETWEEN 0 AND 17 THEN '0-17'
                WHEN e.age BETWEEN 18 AND 34 THEN '18-34'
                WHEN e.age BETWEEN 35 AND 49 THEN '35-49'
                WHEN e.age BETWEEN 50 AND 64 THEN '50-64'
                ELSE '65+'
            END AS age_group,
            e.gender,
            e.blood_type,
            COUNT(*) AS encounter_count
        FROM encounters AS e
        JOIN ref_medical_condition AS c
            ON e.condition_id = c.condition_id
        {where_sql}
        GROUP BY
            CASE
                WHEN e.age BETWEEN 0 AND 17 THEN '0-17'
                WHEN e.age BETWEEN 18 AND 34 THEN '18-34'
                WHEN e.age BETWEEN 35 AND 49 THEN '35-49'
                WHEN e.age BETWEEN 50 AND 64 THEN '50-64'
                ELSE '65+'
            END,
            e.gender,
            e.blood_type
        ORDER BY
            CASE
                WHEN age_group = '0-17' THEN 1
                WHEN age_group = '18-34' THEN 2
                WHEN age_group = '35-49' THEN 3
                WHEN age_group = '50-64' THEN 4
                WHEN age_group = '65+' THEN 5
                ELSE 6
            END,
            e.gender,
            e.blood_type;
    """

    connection = get_connection()

    try:
        rows = connection.execute(query, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        connection.close()


# ============================================================================
# Q7 — Billing by Insurance Provider and Admission Type
# ============================================================================

def get_billing_analysis(
    *,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    condition: str | None = None,
    admission_type: str | None = None,
    insurance_provider: str | None = None,
    gender: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """
    Q7:
        Billing analysis by:
            - insurance provider
            - admission type

    Q8:
        Above-average billing encounters are also returned here because
        the frozen API contract groups the billing analytics together.

    SQL concepts:
        GROUP BY, aggregate functions, subquery, CASE, ORDER BY.

    Monetary analytics exclude billing_is_valid = 0.

    The query applies all supplied filters consistently to the outer
    queries and their subqueries.
    """

    # ------------------------------------------------------------------
    # Build common filters
    # ------------------------------------------------------------------

    where_sql, params = _build_filters(
        start_date=start_date,
        end_date=end_date,
        condition=condition,
        admission_type=admission_type,
        insurance_provider=insurance_provider,
        gender=gender,
    )

    # _build_filters() uses e.condition_name, while these queries join
    # ref_medical_condition as `c`.
    if condition is not None and condition.strip():
        where_sql = where_sql.replace(
            "e.condition_name = ?",
            "c.condition_name = ?",
        )

    # ------------------------------------------------------------------
    # Q7a — Billing by insurance provider
    # ------------------------------------------------------------------

    insurance_query = f"""
        SELECT
            e.insurance_provider,
            COUNT(*) AS valid_billing_encounters,
            ROUND(SUM(e.billing_amount), 2) AS total_billing_amount,
            ROUND(AVG(e.billing_amount), 2) AS avg_billing_amount
        FROM encounters AS e
        JOIN ref_medical_condition AS c
            ON e.condition_id = c.condition_id
        {where_sql}
        {"AND" if where_sql else "WHERE"} e.billing_is_valid = 1
        GROUP BY e.insurance_provider
        HAVING COUNT(*) > 0
        ORDER BY total_billing_amount DESC;
    """

    # ------------------------------------------------------------------
    # Q7b — Billing by admission type
    # ------------------------------------------------------------------

    admission_type_query = f"""
        SELECT
            e.admission_type,
            COUNT(*) AS valid_billing_encounters,
            ROUND(SUM(e.billing_amount), 2) AS total_billing_amount,
            ROUND(AVG(e.billing_amount), 2) AS avg_billing_amount
        FROM encounters AS e
        JOIN ref_medical_condition AS c
            ON e.condition_id = c.condition_id
        {where_sql}
        {"AND" if where_sql else "WHERE"} e.billing_is_valid = 1
        GROUP BY e.admission_type
        HAVING COUNT(*) > 0
        ORDER BY avg_billing_amount DESC;
    """

    # ------------------------------------------------------------------
    # Q8 — Above-average billing encounters
    #
    # The scalar subquery computes the average for the SAME filtered
    # population as the outer query.
    #
    # LIMIT 100 is intentional because the detailed API result does not
    # expose an unbounded list of above-average encounters.
    # ------------------------------------------------------------------

    above_average_query = f"""
        SELECT
            e.encounter_id,
            e.age,
            e.gender,
            c.condition_name,
            e.hospital_name,
            e.insurance_provider,
            e.admission_date,
            e.admission_type,
            ROUND(e.billing_amount, 2) AS billing_amount
        FROM encounters AS e
        JOIN ref_medical_condition AS c
            ON e.condition_id = c.condition_id
        {where_sql}
        {"AND" if where_sql else "WHERE"} e.billing_is_valid = 1
        AND e.billing_amount > (
            SELECT AVG(e2.billing_amount)
            FROM encounters AS e2
            JOIN ref_medical_condition AS c2
                ON e2.condition_id = c2.condition_id
            {where_sql.replace("e.", "e2.").replace("c.", "c2.")}
            {"AND" if where_sql else "WHERE"} e2.billing_is_valid = 1
        )
        ORDER BY e.billing_amount DESC, e.encounter_id
        LIMIT 100;
    """

    # ------------------------------------------------------------------
    # Q8 summary — actual count above the filtered average
    #
    # This is separate from above_average_query because that query is
    # intentionally limited to 100 detailed rows.
    # ------------------------------------------------------------------

    above_average_summary_query = f"""
        SELECT
            COUNT(*) AS above_average_count
        FROM encounters AS e
        JOIN ref_medical_condition AS c
            ON e.condition_id = c.condition_id
        {where_sql}
        {"AND" if where_sql else "WHERE"} e.billing_is_valid = 1
        AND e.billing_amount > (
            SELECT AVG(e2.billing_amount)
            FROM encounters AS e2
            JOIN ref_medical_condition AS c2
                ON e2.condition_id = c2.condition_id
            {where_sql.replace("e.", "e2.").replace("c.", "c2.")}
            {"AND" if where_sql else "WHERE"} e2.billing_is_valid = 1
        );
    """

    # ------------------------------------------------------------------
    # Q8 summary — filtered overall average
    # ------------------------------------------------------------------

    overall_average_query = f"""
        SELECT
            ROUND(AVG(e.billing_amount), 2) AS overall_avg_billing
        FROM encounters AS e
        JOIN ref_medical_condition AS c
            ON e.condition_id = c.condition_id
        {where_sql}
        {"AND" if where_sql else "WHERE"} e.billing_is_valid = 1;
    """

    connection = get_connection()

    try:
        insurance_rows = connection.execute(
            insurance_query,
            params,
        ).fetchall()

        admission_type_rows = connection.execute(
            admission_type_query,
            params,
        ).fetchall()

        above_average_rows = connection.execute(
            above_average_query,
            params + params,
        ).fetchall()

        above_average_count_row = connection.execute(
            above_average_summary_query,
            params + params,
        ).fetchone()

        overall_average_row = connection.execute(
            overall_average_query,
            params,
        ).fetchone()

        above_average_count = (
            int(above_average_count_row["above_average_count"])
            if above_average_count_row is not None
            and above_average_count_row["above_average_count"] is not None
            else 0
        )

        overall_avg_billing = (
            float(overall_average_row["overall_avg_billing"])
            if overall_average_row is not None
            and overall_average_row["overall_avg_billing"] is not None
            else None
        )

        return {
            "by_insurance_provider": _rows_to_dicts(
                insurance_rows
            ),
            "by_admission_type": _rows_to_dicts(
                admission_type_rows
            ),
            "above_average_billing": _rows_to_dicts(
                above_average_rows
            ),
            "above_average_summary": [
                {
                    "above_average_count": above_average_count,
                    "overall_avg_billing": overall_avg_billing,
                }
            ],
        }

    finally:
        connection.close()


# ============================================================================
# Q9 — Test Result Distribution by Admission Type
# ============================================================================

def get_test_results(
    *,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    condition: str | None = None,
    admission_type: str | None = None,
    insurance_provider: str | None = None,
    gender: str | None = None,
) -> list[dict[str, Any]]:
    """
    Q9:
        Test-result distribution by admission type.

    SQL concepts:
        CASE, GROUP BY, aggregate functions, ORDER BY.

    The CASE expression normalizes the three allowed test-result
    categories explicitly, making the analytical mapping visible.
    """

    where_sql, params = _build_filters(
        start_date=start_date,
        end_date=end_date,
        condition=condition,
        admission_type=admission_type,
        insurance_provider=insurance_provider,
        gender=gender,
    )

    query = f"""
        SELECT
            e.admission_type,
            CASE
                WHEN e.test_result = 'Normal' THEN 'Normal'
                WHEN e.test_result = 'Abnormal' THEN 'Abnormal'
                WHEN e.test_result = 'Inconclusive' THEN 'Inconclusive'
                ELSE 'Other'
            END AS test_result,
            COUNT(*) AS encounter_count
        FROM encounters AS e
        JOIN ref_medical_condition AS c
            ON e.condition_id = c.condition_id
        {where_sql}
        GROUP BY
            e.admission_type,
            CASE
                WHEN e.test_result = 'Normal' THEN 'Normal'
                WHEN e.test_result = 'Abnormal' THEN 'Abnormal'
                WHEN e.test_result = 'Inconclusive' THEN 'Inconclusive'
                ELSE 'Other'
            END
        ORDER BY
            e.admission_type,
            encounter_count DESC,
            test_result;
    """

    connection = get_connection()

    try:
        rows = connection.execute(query, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        connection.close()


# ============================================================================
# Convenience function — execute all MUST-HAVE SQL analytics
# ============================================================================

def get_all_analytics(
    *,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    condition: str | None = None,
    admission_type: str | None = None,
    insurance_provider: str | None = None,
    gender: str | None = None,
) -> dict[str, Any]:
    """
    Execute the complete MUST-HAVE analytics set.

    This is primarily useful for integration tests and local validation.
    FastAPI routes may call individual functions instead of executing
    everything at once.
    """

    common_filters = {
        "start_date": start_date,
        "end_date": end_date,
        "condition": condition,
        "admission_type": admission_type,
        "insurance_provider": insurance_provider,
        "gender": gender,
    }

    return {
        "kpis": get_kpis(**common_filters),
        "admissions_trend": get_admissions_trend(**common_filters),
        "top_hospitals": get_top_hospitals(**common_filters),
        "conditions": get_condition_distribution(**common_filters),
        "los_by_condition_category": get_los_by_condition_category(
            **common_filters
        ),
        "demographics": get_demographics(**common_filters),
        "billing": get_billing_analysis(**common_filters),
        "test_results": get_test_results(**common_filters),
    }