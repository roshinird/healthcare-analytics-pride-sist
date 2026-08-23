# 13 — Testing Checklist

**Status:** Authoritative implementation-ready QA checklist. Run before considering any subsystem "done."

---

## 1. Database

- [ ] `SELECT COUNT(*) FROM encounters` returns a plausible non-zero value (tens of thousands).
- [ ] `SELECT COUNT(*) FROM ref_medical_condition` returns exactly 6.
- [ ] No `NULL` in any `NOT NULL` column (`SELECT * FROM encounters WHERE age IS NULL OR gender IS NULL OR condition_id IS NULL ...` returns 0 rows).
- [ ] No `encounters.condition_id` orphaned (`SELECT COUNT(*) FROM encounters e LEFT JOIN ref_medical_condition c ON e.condition_id = c.condition_id WHERE c.condition_id IS NULL` returns 0).
- [ ] `SELECT COUNT(*) FROM encounters WHERE length_of_stay_days <= 0` returns 0 (invalid rows excluded at ingestion, not merely flagged).
- [ ] `SELECT COUNT(*) FROM encounters WHERE billing_is_valid = 0` matches the count logged by `seed.py` at ingestion time.
- [ ] Re-running `python -m app.seed` produces an identical `encounters` row count both times (idempotency check).
- [ ] `SELECT COUNT(*) FROM vw_encounter_enriched` equals `SELECT COUNT(*) FROM encounters` exactly (fan-out check — must never differ).
- [ ] Confirm `Name`, `Doctor`, `Room Number`, `Medication` columns do **not** exist anywhere in the schema (`PRAGMA table_info(encounters)` inspected manually).

## 2. SQL / Analytics Correctness

- [ ] Q1 (KPIs): `avg_length_of_stay` and `avg_billing_amount` are sane (positive, within plausible range for the dataset).
- [ ] Q2 (trend): sum of all monthly `encounter_count` values equals `SELECT COUNT(*) FROM encounters` (no rows lost/duplicated by the `strftime` grouping).
- [ ] Q3 (top hospitals): exactly ≤10 rows returned, `volume_rank` strictly increasing with no gaps for tied-free data (verify `RANK()` behavior on a small manual sample).
- [ ] Q4 (conditions): sum of all `encounter_count` across the 6 conditions equals total encounter count (confirms the JOIN introduces no fan-out).
- [ ] Q5 (LOS by condition): spot-check one condition's `avg_length_of_stay` against a manual `AVG()` query with a hardcoded `WHERE condition_name = '...'`.
- [ ] Q6 (demographics): age-group counts sum to total; gender counts sum to total.
- [ ] Q7 (billing): `by_insurance_provider` counts sum to `total_encounters - excluded_invalid_billing_count`.
- [ ] Q8 (above-average): `above_average_count` is less than total valid-billing count (never all or none, sanity range check).
- [ ] Q9 (test results): sum across all `admission_type` × `test_result` cells equals total encounter count.
- [ ] Every query in `services/queries.py` executed once directly (outside FastAPI) to confirm it runs without error against the seeded DB.

## 3. API

- [ ] `GET /api/health` returns 200 with the frozen shape.
- [ ] Each of the 8 MUST endpoints returns 200 with `data` and `meta` present and field names matching `06-api-contract.md` exactly.
- [ ] Each endpoint tested with **no filters** (baseline) and **at least one filter combination** (e.g., `condition=Diabetes&gender=Female`).
- [ ] Invalid parameter (e.g., `start_date=not-a-date`) returns 422 with the frozen error shape.
- [ ] A filter combination guaranteed to match zero rows (e.g., an implausible date range) returns 200 with `meta.row_count = 0` and an appropriate `meta.note` — never a 404 or 500.
- [ ] `/api/analytics/report-chart` (if implemented) returns `Content-Type: image/png`; if not implemented, returns 501 with the documented error shape.
- [ ] No endpoint response contains `name`, `doctor`, `room_number`, or `medication` fields.
- [ ] CORS: a request from the deployed frontend origin succeeds; a request from an arbitrary other origin is blocked (verify in production config, not just local dev where CORS may be permissive).

## 4. Frontend

- [ ] All 7–8 charts render with mock data (`VITE_USE_MOCK=true`) with zero console errors.
- [ ] Every filter (date range, condition, admission type, insurance, gender) updates chart data.
- [ ] Loading skeleton visible momentarily on initial mount (or on slow network, simulate via browser devtools throttling).
- [ ] Error state renders correctly when the API is intentionally stopped/unreachable, with a working "Retry" action.
- [ ] Empty state renders correctly for a filter combination returning zero rows.
- [ ] Responsive: dashboard usable at 375px (mobile), 768px (tablet), and 1440px (desktop) widths.
- [ ] KPI labels read "Total Encounters" (not "Total Patients"); billing table (if built) reads "Above-Average Billing" (not "outliers") unless the IQR-based statistical outlier view is separately and correctly labeled.
- [ ] Footer disclaimer (synthetic data, non-clinical) is visible on every page state.

## 5. Integration

- [ ] `VITE_USE_MOCK=false` + local backend running → every chart renders identically in structure to the mock version (values differ, shapes match).
- [ ] No hardcoded `localhost` URLs remain once pointed at the deployed backend (`VITE_API_BASE_URL` correctly read from env).
- [ ] CORS configured correctly for the production frontend origin — verify with an actual browser request from the deployed frontend, not just `curl`.

## 6. Deployment

- [ ] Backend deploys successfully to Render; build logs show the seed script's row-count log line.
- [ ] `GET https://<backend>.onrender.com/api/health` returns 200.
- [ ] `GET https://<backend>.onrender.com/api/kpis` returns a non-zero `total_encounters`.
- [ ] Frontend deploys successfully to Vercel/Netlify and loads with live data (not mock).
- [ ] Cold-start behavior observed once deliberately (hit the backend after 15+ minutes idle) to confirm the 30–60s wake time is understood and the pre-warm step is documented/rehearsed.
- [ ] **Full local-fallback run performed at least once**: both servers started locally, dashboard fully functional with zero internet dependency.

## 7. Final Viva / Demo Smoke Test (run immediately before presenting)

- [ ] Pre-warm the Render backend 2–3 minutes before the demo.
- [ ] Open the deployed frontend URL fresh (private/incognito window) and confirm it loads with live data within a few seconds.
- [ ] Click through every filter once, confirm charts update.
- [ ] Have the local-fallback terminal commands ready and tested, in case the deployed version fails live.
- [ ] Be ready to answer: "why no patient ID?", "why is Doctor/Hospital not a table?", "how do you prevent double-counting?", "why SQLite not Postgres?" — answers are all documented verbatim in `03-dataset.md`, `04-database-schema.md`, and `02-tech-stack.md`.
