# 01 — Requirements

**Status:** Authoritative. Scope classifications here override any conflicting suggestion elsewhere.

---

## 1. Functional Requirements

### 1.1 Data layer
- FR-1 (MUST): System ingests the source CSV into a SQLite database matching `04-database-schema.md` exactly.
- FR-2 (MUST): Ingestion drops `Name`, `Doctor`, `Room Number`, `Medication` per the audited column-retention rule.
- FR-3 (MUST): Ingestion derives `length_of_stay_days` and flags `billing_is_valid = false` for negative billing amounts.
- FR-4 (MUST): Ingestion is idempotent — re-running the seed script produces the same row count and does not duplicate rows.

### 1.2 Analytics / SQL
- FR-5 (MUST): All 9 MUST-HAVE analytics questions in `05-sql-analytics.md` are implemented as parameterized SQL queries.
- FR-6 (SHOULD): IQR-based billing outlier query implemented.
- FR-7 (MUST): No query may double-count encounters (see fan-out rule, `04-database-schema.md` §5).

### 1.3 Backend / API
- FR-8 (MUST): All 8 MUST endpoints in `06-api-contract.md` are implemented and return the frozen response shape.
- FR-9 (SHOULD): `/api/analytics/report-chart` (Matplotlib PNG) implemented.
- FR-10 (MUST): All query parameters are validated via Pydantic; invalid input returns HTTP 422 with the frozen error shape.

### 1.4 Frontend
- FR-11 (MUST): Dashboard renders KPI row, filter bar, and all 7–8 charts corresponding to the 9 MUST-have questions.
- FR-12 (MUST): Filters (date range, condition, admission type, insurance provider, gender) update chart data via API query parameters.
- FR-13 (MUST): Each chart independently handles loading, empty, and error states.
- FR-14 (SHOULD): Dashboard is responsive down to mobile width (single-column collapse).

## 2. Non-Functional Requirements

- NFR-1 (MUST): ₹0 total cost — no paid API keys, no paid hosting tier, no credit card requirement anywhere.
- NFR-2 (MUST): Combined implementation time ≤ 10 hours (target 8–10h; see `12-dev-workflow-split.md`).
- NFR-3 (MUST): No PII beyond what is explicitly retained per `03-dataset.md`; `Name` never stored or returned.
- NFR-4 (MUST): API responses for any single endpoint return in under ~1.5s against the seeded dataset on Render's free tier (post-cold-start).
- NFR-5 (SHOULD): Frontend initial load renders KPI skeleton within 500ms of mount (before API resolves).

## 3. Analytics Requirements

- AR-1 (MUST): The 9 MUST-HAVE questions collectively demonstrate JOIN, GROUP BY, HAVING, CASE, CTE, window function, subquery, date functions, view, and index usage (mapping in `05-sql-analytics.md`).
- AR-2 (MUST): No analytics question implies patient-level identity, readmission, department performance, or doctor performance.
- AR-3 (SHOULD): IQR-based outlier detection implemented in Pandas/NumPy, not SQL.

## 4. Visualization Requirements

- VR-1 (MUST): Recharts used for all interactive dashboard charts.
- VR-2 (SHOULD): One Matplotlib-generated static PNG ("Executive Summary") available via a dedicated endpoint and a "Download Report" UI action.
- VR-3 (MUST): Every chart on the dashboard maps to exactly one analytics question in `05-sql-analytics.md` — no decorative/unexplained charts.

## 5. Privacy Requirements

- PR-1 (MUST): `Name` column dropped at ingestion; never persisted, queried, logged, or returned by any endpoint.
- PR-2 (MUST): No endpoint returns row-level encounter data with any field that could function as an identity key.
- PR-3 (MUST): The application UI and API documentation explicitly state the dataset is synthetic and the system performs no clinical decision-making.
- PR-4 (MUST): No feature infers or displays "same patient across encounters."

## 6. Performance Requirements

- PF-1 (MUST): Indexes exist on all columns used in WHERE/JOIN/GROUP BY clauses per `04-database-schema.md`.
- PF-2 (SHOULD): Heavy aggregate queries (trend, top-hospitals) complete in under 200ms against the local SQLite file.
- PF-3 (MUST): No client-side computation duplicates SQL aggregation that the API already performs (avoid redundant heavy work in the browser).

## 7. Deployment Requirements

- DR-1 (MUST): Backend deployable to Render free tier with zero paid add-ons.
- DR-2 (MUST): Frontend deployable to Vercel or Netlify free tier.
- DR-3 (MUST): A fully offline/local run path exists and is documented (`11-deployment.md`) as a demo fallback.
- DR-4 (MUST): No separate hosted database service — SQLite ships with/rebuilds alongside the backend.

## 8. Scope Classification (authoritative)

### MUST HAVE
- Schema: `encounters` + `ref_medical_condition` exactly as specified
- 9 MUST-HAVE analytics questions (05-sql-analytics.md)
- 8 MUST API endpoints (06-api-contract.md)
- React dashboard: KPI row, filter bar, 7–8 charts, loading/empty/error states
- Data-quality handling (negative billing exclusion, disclosed)
- Deployment (Render + Vercel/Netlify) + local fallback
- Security rules per `10-security-privacy.md`

### SHOULD HAVE
- IQR statistical billing-outlier analysis (NumPy)
- Matplotlib "Executive Summary" report PNG endpoint
- 3-month rolling average admissions (Pandas)
- Mobile-responsive polish

### NICE TO HAVE
- CSV export of dashboard data
- Searchable/typeahead hospital filter

### DO NOT BUILD
- Patient identity, patient dimension, or any patient-level tracking
- Readmission analytics of any kind
- Doctor-level analytics or a doctor entity/table
- Department/ward analytics (no such field exists in source data)
- Room-number analytics (field dropped)
- Medication analytics (field dropped)
- Authentication, accounts, or authorization of any kind
- Diagnosis, treatment recommendation, or predictive/ML modeling
- PostgreSQL, Redis, message queues, or microservices
- Any paid API, dataset, or hosting tier
- File upload functionality
- Any endpoint that executes arbitrary or dynamically constructed SQL
