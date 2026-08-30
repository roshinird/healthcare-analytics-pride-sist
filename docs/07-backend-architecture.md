# 07 — Backend Architecture

**Status:** Authoritative. This structure is final — do not collapse everything into `main.py`.

---

## 1. Directory Structure

```
backend/
  app/
    main.py                  # FastAPI app instance, CORS, router mounting, startup event
    config.py                # environment variable loading (BASE settings)
    database.py               # SQLite connection helper (PRAGMA foreign_keys=ON, row_factory)
    seed.py                    # one-time/idempotent CSV -> cleaned -> SQLite loader (Dev B owns)
    schemas.py                  # Pydantic request/response models (mirrors 06-api-contract.md exactly)
    routers/
      health.py                 # GET /api/health
      analytics.py                # all GET /api/analytics/* and /api/kpis routes
    services/
      queries.py                  # raw parameterized SQL strings/functions, one function per Q1-Q9 (05-sql-analytics.md)
      analytics.py                  # Pandas transformation layer: shapes SQL results into API response shapes
      stats.py                       # NumPy statistical helpers (IQR outlier detection, percentiles) — SHOULD HAVE
      report.py                       # Matplotlib PNG generation — SHOULD HAVE
  data/
    healthcare.csv               # raw source dataset (not committed if large; documented in README how to obtain)
    healthcare.db                 # built by seed.py, gitignored or committed pre-built — team's choice, document in 11-deployment.md
  requirements.txt
  .env.example
```

## 2. Module Responsibilities (strict boundaries)

| Module | Responsibility | Must NOT contain |
|---|---|---|
| `main.py` | App instantiation, CORS middleware, router includes, startup event (verify DB exists / trigger seed if missing) | Business logic, SQL, Pandas code |
| `database.py` | Single `get_connection()` function returning a SQLite connection with `PRAGMA foreign_keys = ON` and `row_factory = sqlite3.Row` | Query text |
| `seed.py` | Ingestion, cleaning, table creation, data load — run via `python -m app.seed` | FastAPI imports (must run standalone) |
| `schemas.py` | Pydantic models only — one request-params model and one response model per endpoint group, matching `06-api-contract.md` field-for-field | Query logic |
| `routers/*.py` | Route decorators, dependency injection of validated params, calling into `services/`, returning schema-validated responses | Raw SQL, Pandas transformation |
| `services/queries.py` | One function per analytics question (`get_kpis(conn, filters) -> list[sqlite3.Row]`, etc.), always parameterized (`?` placeholders) | Response formatting, percentage math |
| `services/analytics.py` | Takes raw query rows, returns Pandas-shaped, API-ready dict/list structures (percentages, pivots, rolling averages) | SQL text |
| `services/stats.py` | `compute_iqr_outliers(billing_series) -> dict` using NumPy | SQL, FastAPI imports |
| `services/report.py` | `generate_summary_png(data) -> bytes` using Matplotlib (non-interactive `Agg` backend) | SQL, route decorators |

## 3. Dependency Flow

```
routers/analytics.py
  → services/queries.py     (SQL, parameterized, returns raw rows)
  → services/analytics.py   (Pandas: shape rows into response dict)
  → services/stats.py       (NumPy: outlier stats, only for /billing)
  → schemas.py               (Pydantic validates the outbound shape)
  → JSON response
```
No router calls `database.py` directly except via `services/queries.py`. No service module imports FastAPI.

## 4. Error Handling

- All routes wrapped so that unhandled exceptions return the frozen error envelope with `code: "INTERNAL_ERROR"` and a generic message — **never** the raw exception string or stack trace (see `10-security-privacy.md`).
- Pydantic validation failures are caught by FastAPI automatically and reshaped (via a custom exception handler in `main.py`) into the frozen `{ "error": { "code": "VALIDATION_ERROR", "message": ... } }` shape instead of FastAPI's default error format.

## 5. Configuration

`config.py` reads from environment variables (via `.env` locally, Render dashboard env vars in production):
```
DATABASE_PATH=./data/healthcare.db
CORS_ALLOWED_ORIGIN=http://localhost:5173
ENVIRONMENT=development   # or "production"
```
No secrets are required for this project (no external paid API), but the pattern is still followed for good practice and to avoid hardcoded values.

## 6. CORS

Configured in `main.py` using `CORS_ALLOWED_ORIGIN` from config — a single origin in production (the deployed frontend URL), permissive (`*` or `http://localhost:5173`) only in local development. Never `*` in a production deployment.

## 7. SQL Parameterization Rule (non-negotiable)

Every query in `services/queries.py` uses `?` placeholders with a params tuple passed to `cursor.execute(sql, params)`. **No f-strings, `.format()`, or `%`-formatting are ever used to build SQL text containing user input.** Static, non-user-controlled SQL fragments (e.g., `ORDER BY` direction chosen from a fixed whitelist) may be conditionally selected in Python but never built from raw user input.

## 8. Database Initialization / Startup Behavior

On `main.py` startup event:
1. Check whether `data/healthcare.db` exists and contains the expected tables.
2. If missing, log a warning and run the seed process automatically (calls into `seed.py`'s main function) — this makes the backend self-healing on a fresh Render deploy where the disk may not have persisted the file.
3. Log final row counts for `encounters` and `ref_medical_condition` at startup for quick sanity verification in Render's log viewer.

## 9. Report Generation (`services/report.py`, SHOULD HAVE)

- Uses `matplotlib.use('Agg')` (non-interactive backend, required for a server process with no display).
- Builds a single `2x2` subplot figure (admissions trend line, LOS histogram, condition distribution bar, billing distribution histogram) from a Pandas DataFrame assembled from the same `services/queries.py` functions used by the JSON endpoints — **no duplicate SQL**.
- Returns raw PNG bytes; the router sets `Content-Type: image/png` explicitly, bypassing the standard JSON response model (documented exception in `06-api-contract.md` §4).

## 10. Testing Hooks

Each `services/queries.py` function must be independently callable and testable without FastAPI running (plain Python function taking a connection object) — this is what enables the row-count and correctness checks in `13-testing-checklist.md`.
