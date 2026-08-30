# 06 — API Contract

**Status: 🔒 FROZEN AND AUTHORITATIVE.**
No AI coding agent may add, remove, rename, or restructure endpoints, parameters, or response fields without explicit developer approval. Frontend and backend must both conform exactly to this file — it is the single source of truth that lets Dev A and Dev B work in parallel.

---

## 1. Common Response Envelope (frozen)

**Success:**
```json
{
  "data": { },
  "meta": {
    "row_count": 0,
    "generated_at": "2026-08-23T10:00:00Z",
    "note": null
  }
}
```
- `data` shape varies per endpoint (documented below).
- `meta.note` is used for non-error advisories (e.g., "no encounters matched the given filters", or "3 rows excluded due to invalid billing").

**Error:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "start_date must be in YYYY-MM-DD format"
  }
}
```

## 2. Common Query Parameters (accepted by all `/api/analytics/*` endpoints unless noted otherwise)

| Param | Type | Required | Validation |
|---|---|---|---|
| `start_date` | string (`YYYY-MM-DD`) | No | Must parse as a valid date |
| `end_date` | string (`YYYY-MM-DD`) | No | Must parse as a valid date; must be ≥ `start_date` if both given |
| `condition` | string | No | Must match a `condition_name` in `ref_medical_condition`, else 422 |
| `admission_type` | string | No | Must be one of `Emergency`, `Urgent`, `Elective`, else 422 |
| `insurance_provider` | string | No | Must match a known provider value present in the data, else 422 |
| `gender` | string | No | Must be `Male` or `Female`, else 422 |

Any unrecognized query parameter is ignored (not an error), to keep the contract forward-tolerant.

## 3. HTTP Status Codes

| Code | Meaning |
|---|---|
| 200 | Success (including zero-row results — see §4 empty-response rule) |
| 422 | Validation error (bad parameter value) |
| 500 | Unhandled server error (generic message only — see `10-security-privacy.md`) |

---

## 4. Endpoints

### `GET /api/health` (MUST)
- **Purpose:** Liveness check; also used to pre-warm Render's free-tier instance before a demo.
- **Params:** none.
- **Response:**
```json
{ "data": { "status": "ok" }, "meta": { "generated_at": "2026-08-23T10:00:00Z" } }
```

---

### `GET /api/kpis` (MUST)
- **Purpose:** KPI row — total encounters, avg LOS, avg billing, date range covered.
- **Params:** common filters (§2).
- **Response (example):**
```json
{
  "data": {
    "total_encounters": 55021,
    "avg_length_of_stay": 15.42,
    "avg_billing_amount": 25517.33,
    "earliest_admission": "2019-05-08",
    "latest_admission": "2024-05-07"
  },
  "meta": { "row_count": 1, "generated_at": "2026-08-23T10:00:00Z", "note": null }
}
```
- **Empty result (no rows match filters):** `data` fields all `null`/`0`, `meta.note = "No encounters matched the given filters."`

---

### `GET /api/analytics/admissions-trend` (MUST)
- **Purpose:** Q2 — monthly admissions trend, % change, rolling average.
- **Params:** common filters (§2).
- **Response (example):**
```json
{
  "data": [
    { "month": "2024-01", "encounter_count": 512, "prev_month_count": null, "pct_change": null, "rolling_avg_3mo": null },
    { "month": "2024-02", "encounter_count": 498, "prev_month_count": 512, "pct_change": -2.73, "rolling_avg_3mo": null },
    { "month": "2024-03", "encounter_count": 530, "prev_month_count": 498, "pct_change": 6.43, "rolling_avg_3mo": 513.33 }
  ],
  "meta": { "row_count": 3, "generated_at": "2026-08-23T10:00:00Z", "note": null }
}
```
- `rolling_avg_3mo` is SHOULD HAVE — if not implemented, field is present and always `null`, never omitted (keeps the frontend contract stable regardless of build order).

---

### `GET /api/analytics/top-hospitals` (MUST)
- **Purpose:** Q3 — top-10 facilities by encounter volume.
- **Params:** common filters (§2).
- **Response (example):**
```json
{
  "data": [
    { "hospital_name": "Smith and Sons", "encounter_count": 41, "volume_rank": 1 },
    { "hospital_name": "Kim Inc", "encounter_count": 39, "volume_rank": 2 }
  ],
  "meta": { "row_count": 2, "generated_at": "2026-08-23T10:00:00Z", "note": null }
}
```

---

### `GET /api/analytics/conditions` (MUST)
- **Purpose:** Q4 (distribution) and Q5 (avg LOS by condition) combined.
- **Params:** common filters (§2).
- **Response (example):**
```json
{
  "data": [
    { "condition_name": "Diabetes", "condition_category": "Chronic", "encounter_count": 9231, "percentage_share": 16.78, "avg_length_of_stay": 15.51 },
    { "condition_name": "Cancer", "condition_category": "Acute", "encounter_count": 9187, "percentage_share": 16.69, "avg_length_of_stay": 15.33 }
  ],
  "meta": { "row_count": 6, "generated_at": "2026-08-23T10:00:00Z", "note": null }
}
```

---

### `GET /api/analytics/demographics` (MUST)
- **Purpose:** Q6 — age group, gender, blood type breakdowns.
- **Params:** common filters (§2).
- **Response (example):**
```json
{
  "data": {
    "age_groups": [
      { "age_group": "Pediatric (0-17)", "encounter_count": 0, "percentage_share": 0.0 },
      { "age_group": "Adult (18-64)", "encounter_count": 33012, "percentage_share": 60.0 },
      { "age_group": "Senior (65+)", "encounter_count": 22009, "percentage_share": 40.0 }
    ],
    "genders": [
      { "gender": "Male", "encounter_count": 27500, "percentage_share": 50.0 },
      { "gender": "Female", "encounter_count": 27521, "percentage_share": 50.0 }
    ],
    "blood_types": [
      { "blood_type": "O+", "encounter_count": 7100, "percentage_share": 12.9 }
    ]
  },
  "meta": { "row_count": 55021, "generated_at": "2026-08-23T10:00:00Z", "note": null }
}
```

---

### `GET /api/analytics/billing` (MUST, with SHOULD-have extension)
- **Purpose:** Q7 (by insurance/admission type), Q8 (above-average), S1 (IQR outliers — SHOULD).
- **Params:** common filters (§2).
- **Response (example):**
```json
{
  "data": {
    "by_insurance_provider": [
      { "insurance_provider": "Medicare", "encounter_count": 11020, "avg_billing": 25601.12, "total_billing": 282122432.4, "pct_of_total_billing": 20.15 }
    ],
    "by_admission_type": [
      { "admission_type": "Emergency", "encounter_count": 18500, "avg_billing": 25890.44 }
    ],
    "above_average": {
      "above_average_count": 27210,
      "overall_avg_billing": 25517.33
    },
    "statistical_outliers": {
      "outlier_count": 812,
      "lower_bound": 1200.5,
      "upper_bound": 48200.75
    },
    "excluded_invalid_billing_count": 143
  },
  "meta": { "row_count": 55021, "generated_at": "2026-08-23T10:00:00Z", "note": null }
}
```
- `statistical_outliers` is SHOULD HAVE — if not implemented, the key is present with `null` values (never omitted).
- `excluded_invalid_billing_count` is always populated — this is the data-quality transparency field (MUST HAVE).

---

### `GET /api/analytics/test-results` (MUST)
- **Purpose:** Q9 — test result distribution by admission type.
- **Params:** common filters (§2).
- **Response (example):**
```json
{
  "data": [
    { "admission_type": "Emergency", "test_result": "Normal", "encounter_count": 6100 },
    { "admission_type": "Emergency", "test_result": "Abnormal", "encounter_count": 6300 },
    { "admission_type": "Emergency", "test_result": "Inconclusive", "encounter_count": 6100 }
  ],
  "meta": { "row_count": 9, "generated_at": "2026-08-23T10:00:00Z", "note": null }
}
```

---

### `GET /api/analytics/report-chart` (SHOULD HAVE)
- **Purpose:** Server-generated Matplotlib "Executive Summary" PNG (admissions trend, LOS histogram, condition distribution, billing distribution).
- **Params:** common filters (§2), applied identically to the underlying data before rendering.
- **Response:** `Content-Type: image/png`, raw PNG bytes (not the JSON envelope — this is the one endpoint that deviates from §1 by necessity, documented here explicitly as the sole exception).
- **If not implemented:** endpoint returns HTTP 501 with `{ "error": { "code": "NOT_IMPLEMENTED", "message": "Report chart generation is not available in this build." } }` — frontend must handle this gracefully (hide the "Download Report" button rather than erroring).

---

## 5. Frontend Mock JSON (for parallel development before backend is ready)

Dev A builds the frontend against static fixture files placed at `frontend/src/mocks/*.json`, one file per endpoint, containing exactly the example response shapes above. The API client module (`frontend/src/api/client.js`, see `08-frontend-architecture.md`) reads from a `USE_MOCK` flag; switching it to `false` and pointing `BASE_URL` at the live backend is the entire integration step.

## 6. Validation Error Example

Request: `GET /api/kpis?start_date=not-a-date`
```json
{ "error": { "code": "VALIDATION_ERROR", "message": "start_date must be in YYYY-MM-DD format" } }
```
HTTP 422.

## 7. What Is Frozen vs. Flexible

- **Frozen:** endpoint paths, HTTP methods, top-level response envelope, all field names shown above.
- **Flexible (implementation detail, no approval needed):** internal query/service function names, exact SQL query text (as long as it matches `05-sql-analytics.md` semantics), order of fields within a JSON object (not order-sensitive by contract).
