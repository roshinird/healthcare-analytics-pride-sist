# 05 — SQL Analytics

**Status:** Authoritative. These 9 questions are the complete MUST-HAVE analytics scope. Do not add further questions without developer approval — every addition risks the time budget.

All queries run against `encounters` / `vw_encounter_enriched` as defined in `04-database-schema.md`. All queries are **read-only** and must be executed as **parameterized statements** (never string-concatenated) from `backend/app/services/queries.py`.

**Safe aggregation rule (repeated from schema file):** at most one JOIN (`encounters ⋈ ref_medical_condition`) ever appears in any query below. This structurally guarantees no double-counting.

---

## Q1 — KPI Summary

- **Purpose:** Top-line operational snapshot for the dashboard header.
- **Grain:** Aggregate over all (optionally filtered) encounters.
- **Source:** `encounters`
- **SQL concepts:** Aggregate functions, `CASE`-based conditional aggregation.
- **Filtering:** Supports `start_date`, `end_date`, `condition`, `admission_type`, `insurance_provider`, `gender`.

```sql
SELECT
    COUNT(*)                                                   AS total_encounters,
    ROUND(AVG(length_of_stay_days), 2)                         AS avg_length_of_stay,
    ROUND(AVG(CASE WHEN billing_is_valid = 1 THEN billing_amount END), 2) AS avg_billing_amount,
    MIN(admission_date)                                        AS earliest_admission,
    MAX(admission_date)                                        AS latest_admission
FROM encounters
WHERE 1=1
  -- AND admission_date >= :start_date  (if provided)
  -- AND admission_date <= :end_date    (if provided)
  -- AND condition_id = :condition_id   (if provided)
  -- AND admission_type = :admission_type (if provided)
  -- AND insurance_provider = :insurance_provider (if provided)
  -- AND gender = :gender (if provided);
```
- **Pandas handoff:** rounding/formatting only; no heavy transformation needed.
- **Edge case:** if `avg_billing_amount` is `NULL` (all matching rows have invalid billing), API returns `0` with a `note` field (see `06-api-contract.md`).

---

## Q2 — Monthly Admissions Trend

- **Purpose:** Show admission volume over time and month-over-month change.
- **Grain:** Month.
- **Source:** `encounters`
- **SQL concepts:** CTE, date functions (`strftime`), window function (`LAG`).

```sql
WITH monthly AS (
    SELECT
        strftime('%Y-%m', admission_date) AS month,
        COUNT(*) AS encounter_count
    FROM encounters
    WHERE 1=1 -- same optional filters as Q1
    GROUP BY strftime('%Y-%m', admission_date)
)
SELECT
    month,
    encounter_count,
    LAG(encounter_count) OVER (ORDER BY month) AS prev_month_count,
    ROUND(
        100.0 * (encounter_count - LAG(encounter_count) OVER (ORDER BY month))
        / NULLIF(LAG(encounter_count) OVER (ORDER BY month), 0), 2
    ) AS pct_change
FROM monthly
ORDER BY month;
```
- **Pandas handoff:** compute a 3-month rolling average (`.rolling(3).mean()`) alongside the SQL-computed month-over-month `%` change — this is a deliberate case of SQL and Pandas each computing a *different* derived metric from the same base data (SHOULD HAVE enhancement; MUST HAVE is the raw trend + `pct_change`).
- **Edge case:** first month has `prev_month_count = NULL`, `pct_change = NULL` — frontend renders as "—".

---

## Q3 — Top-10 Facilities by Encounter Volume

- **Purpose:** Which facilities in the dataset show the highest encounter volume.
- **Grain:** Hospital (flat text field — **not** a normalized entity; framed honestly as a long-tail, mostly-unique field).
- **Source:** `encounters`
- **SQL concepts:** Window function (`RANK`), `GROUP BY`, `LIMIT`.

```sql
WITH ranked AS (
    SELECT
        hospital_name,
        COUNT(*) AS encounter_count,
        RANK() OVER (ORDER BY COUNT(*) DESC) AS volume_rank
    FROM encounters
    WHERE 1=1 -- same optional filters as Q1
    GROUP BY hospital_name
)
SELECT hospital_name, encounter_count, volume_rank
FROM ranked
WHERE volume_rank <= 10
ORDER BY volume_rank;
```
- **Pandas handoff:** none required beyond response shaping.
- **Edge case:** with filters applied, fewer than 10 facilities may qualify — return whatever the query yields, do not pad.

---

## Q4 — Medical Condition Distribution

- **Purpose:** Case-mix distribution across the 6 known conditions.
- **Grain:** Condition.
- **Source:** `vw_encounter_enriched`
- **SQL concepts:** `JOIN` (via the view), `GROUP BY`, `HAVING`.

```sql
SELECT
    condition_name,
    condition_category,
    COUNT(*) AS encounter_count
FROM vw_encounter_enriched
WHERE 1=1 -- same optional filters as Q1
GROUP BY condition_name, condition_category
HAVING COUNT(*) > 0
ORDER BY encounter_count DESC;
```
- **Pandas handoff:** compute `percentage_share = encounter_count / total * 100` for the donut/bar chart labels.
- **Note on `HAVING`:** with the full unfiltered dataset all 6 conditions will always have count > 0 — the `HAVING` clause exists to correctly suppress conditions with zero matches once date/type filters are applied (a genuine, not decorative, use).

---

## Q5 — Average Length of Stay by Condition Category

- **Purpose:** Which condition categories drive the most bed-days.
- **Grain:** Condition category (Chronic/Acute) and condition name.
- **Source:** `vw_encounter_enriched`
- **SQL concepts:** `JOIN`, `GROUP BY`, `AVG`.

```sql
SELECT
    condition_name,
    condition_category,
    ROUND(AVG(length_of_stay_days), 2) AS avg_length_of_stay,
    COUNT(*) AS encounter_count
FROM vw_encounter_enriched
WHERE 1=1 -- same optional filters as Q1
GROUP BY condition_name, condition_category
ORDER BY avg_length_of_stay DESC;
```
- **Pandas handoff:** none required beyond response shaping.

---

## Q6 — Demographic Breakdown (Age Group × Gender × Blood Type)

- **Purpose:** Understand the demographic profile of encounters.
- **Grain:** Age group, gender, blood type (three separate breakdowns in one response).
- **Source:** `encounters`
- **SQL concepts:** `CASE` (age bucketing), `GROUP BY`.

```sql
-- Age group breakdown
SELECT
    CASE
        WHEN age < 18 THEN 'Pediatric (0-17)'
        WHEN age BETWEEN 18 AND 64 THEN 'Adult (18-64)'
        ELSE 'Senior (65+)'
    END AS age_group,
    COUNT(*) AS encounter_count
FROM encounters
WHERE 1=1 -- same optional filters as Q1
GROUP BY age_group;

-- Gender breakdown
SELECT gender, COUNT(*) AS encounter_count
FROM encounters
WHERE 1=1
GROUP BY gender;

-- Blood type breakdown
SELECT blood_type, COUNT(*) AS encounter_count
FROM encounters
WHERE 1=1
GROUP BY blood_type
ORDER BY encounter_count DESC;
```
- **Pandas handoff:** merge the three result sets into one response object with three keyed arrays (`age_groups`, `genders`, `blood_types`); compute percentage share for each.

---

## Q7 — Billing by Insurance Provider & Admission Type

- **Purpose:** Payer mix and admission-type cost profile.
- **Grain:** Insurance provider; admission type (two breakdowns in one response).
- **Source:** `encounters` (filtered to `billing_is_valid = 1` for all financial aggregates)
- **SQL concepts:** `GROUP BY`, `AVG`/`SUM`, view usage.

```sql
-- By insurance provider
SELECT
    insurance_provider,
    COUNT(*) AS encounter_count,
    ROUND(AVG(billing_amount), 2) AS avg_billing,
    ROUND(SUM(billing_amount), 2) AS total_billing
FROM encounters
WHERE billing_is_valid = 1 -- AND same optional filters as Q1
GROUP BY insurance_provider
ORDER BY total_billing DESC;

-- By admission type
SELECT
    admission_type,
    COUNT(*) AS encounter_count,
    ROUND(AVG(billing_amount), 2) AS avg_billing
FROM encounters
WHERE billing_is_valid = 1
GROUP BY admission_type
ORDER BY avg_billing DESC;
```
- **Pandas handoff:** compute `pct_of_total_billing` per insurance provider.

---

## Q8 — Above-Average Billing Encounters

- **Purpose:** Identify encounters billed above the overall average — a simple, correctly-labeled comparison (**not** a statistical outlier claim).
- **Grain:** Encounter (aggregate count + sample returned).
- **Source:** `encounters` (filtered to `billing_is_valid = 1`)
- **SQL concepts:** Scalar **subquery**.

```sql
SELECT COUNT(*) AS above_average_count,
       ROUND((SELECT AVG(billing_amount) FROM encounters WHERE billing_is_valid = 1), 2) AS overall_avg_billing
FROM encounters
WHERE billing_is_valid = 1
  AND billing_amount > (SELECT AVG(billing_amount) FROM encounters WHERE billing_is_valid = 1);
```
- **Pandas handoff:** none for the MUST-have count. **(SHOULD HAVE extension, not part of this query):** a separate Pandas/NumPy pass computes genuine IQR-based statistical outliers (`Q1 - 1.5*IQR`, `Q3 + 1.5*IQR`) using `np.percentile` — kept explicitly distinct from this subquery and clearly labeled "Statistical Outliers (IQR method)" wherever it appears, so the two concepts are never conflated in the UI.
- **Terminology rule:** UI/API must label this "Above-Average Billing Encounters," never "outliers."

---

## Q9 — Test Result Distribution by Admission Type

- **Purpose:** Outcome-pattern overview across urgency levels.
- **Grain:** Test result × admission type.
- **Source:** `encounters`
- **SQL concepts:** `CASE` (optional normalization of labels), `GROUP BY` (two dimensions).

```sql
SELECT
    admission_type,
    test_result,
    COUNT(*) AS encounter_count
FROM encounters
WHERE 1=1 -- same optional filters as Q1
GROUP BY admission_type, test_result
ORDER BY admission_type, test_result;
```
- **Pandas handoff:** pivot the long-format result into a matrix (`admission_type` rows × `test_result` columns) for the grouped-bar chart.

---

## SHOULD-HAVE Analytics (not part of the 9 MUST-have questions)

### S1 — Statistical Billing Outliers (IQR method)
- Computed entirely in Pandas/NumPy (not SQL): pull `billing_amount` for `billing_is_valid = 1` rows, compute Q1/Q3 via `np.percentile([...], [25, 75])`, flag rows outside `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]`.
- Returned via the same `/api/analytics/billing` endpoint as an additional `statistical_outliers` block, clearly separate from Q8's `above_average` block.

### S2 — 3-Month Rolling Average Admissions
- Computed in Pandas from the Q2 monthly series via `.rolling(window=3).mean()`. Returned as an additional field in the `/api/analytics/admissions-trend` response.

---

## Concept Coverage Verification (all within the 9 MUST-have questions)

| Concept | Demonstrated in |
|---|---|
| JOIN | Q4, Q5 (via `vw_encounter_enriched`) |
| GROUP BY | Q1, Q3, Q4, Q5, Q6, Q7, Q9 |
| HAVING | Q4 |
| CASE | Q6, Q1 (conditional aggregation) |
| CTE | Q2, Q3 |
| Window function | Q2 (`LAG`), Q3 (`RANK`) |
| Subquery | Q8 |
| Date functions | Q2 (`strftime`) |
| View | Q4, Q5 (`vw_encounter_enriched`) |
| Indexes | All queries filtering/grouping on `condition_id`, `admission_date`, `hospital_name`, `insurance_provider`, `admission_type` use the indexes defined in `04-database-schema.md` |
