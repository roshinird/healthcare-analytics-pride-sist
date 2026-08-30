# 10 — Security & Privacy

**Status:** Authoritative for all security decisions. These rules are stronger than a generic analytics project's because the domain is healthcare — but this project builds no compliance infrastructure; it builds sound, disciplined engineering practice appropriate to a synthetic dataset.

---

## 1. Non-Negotiable Backend Rules

1. **Parameterized SQL only.** Every query in `services/queries.py` uses `?` placeholders with a params tuple. No f-string, `.format()`, or `%`-based SQL construction from user input, ever.
2. **No arbitrary SQL execution endpoint.** There is no endpoint, debug route, or admin panel that accepts raw SQL from a request. This is a permanent constraint, not a MUST/SHOULD item — violating it is a blocking defect.
3. **All request inputs validated via Pydantic** before reaching any service function. Query parameters (dates, enums, strings) are typed and constrained (see `06-api-contract.md` §2 for exact validation rules).
4. **CORS restricted to a named origin** in production (`CORS_ALLOWED_ORIGIN` env var — the deployed frontend URL). Wildcard `*` is permitted only in local development.
5. **No hardcoded secrets.** Even though this project requires no paid/secret API key, all configuration (DB path, CORS origin, environment name) is read from environment variables via `config.py`, never inlined in source.
6. **Safe error responses.** Any unhandled exception is caught and converted to the frozen `{ "error": { "code": "INTERNAL_ERROR", "message": "An unexpected error occurred." } }` shape. The raw exception message/stack trace is logged server-side only, never returned to the client.
7. **No debug mode in production.** FastAPI/Uvicorn run without `--reload` and without verbose tracebacks exposed (`ENVIRONMENT=production` gates this in `config.py`).
8. **No file upload endpoints** anywhere in the API.
9. **No subprocess execution** anywhere in the backend.
10. **Dependency minimization** — no library is added without justification (see `02-tech-stack.md` §"Dependency Minimization Rule").

## 2. PII / Healthcare-Data-Specific Rules

1. **`Name` is dropped at ingestion and never persisted, logged, queried, or returned** by any endpoint, script, or log statement. This applies even though the field is synthetic — the discipline is deliberate (see `03-dataset.md` §1, §6).
2. **No patient-identity inference.** No code path may attempt to determine whether two encounter rows represent "the same patient" (by name matching, demographic matching, or any other heuristic). See `03-dataset.md` §4 and §7 for the full prohibition.
3. **No row-level encounter data is exposed with any field or field-combination that could function as a re-identification key.** All API responses are aggregate (grouped/counted) except where a small bounded sample is explicitly part of the contract (e.g., top-10 hospitals) — no endpoint returns the full 55,000-row encounter list.
4. **No readmission, longitudinal, or "patient history" feature of any kind.**
5. **No doctor-level or department-level analytics** (fields dropped/nonexistent per `03-dataset.md`).

## 3. What This Application Must NOT Claim To Do

The system is a **healthcare analytics/education dashboard**. It is explicitly **not**:
- A medical diagnostic system
- A clinical decision-support system
- An EHR (electronic health record) system
- A patient portal
- A treatment or medication recommendation system
- A predictive/ML clinical risk-scoring engine

This must be stated in the frontend footer and README (exact text in `03-dataset.md` §8) and must never be contradicted by UI copy elsewhere (no "risk score," no "recommended treatment," no "flagged patient" language anywhere).

## 4. AI-Generated Code Review Checklist

Before merging any AI-agent-generated code, a human developer must verify:
- [ ] No new SQL string is built via concatenation/f-string with a variable derived from a request parameter.
- [ ] No new table, column, or field reintroduces `Name`, `Doctor`, `Room Number`, `Medication`, or any patient/department entity (cross-check against `04-database-schema.md` §6 and `03-dataset.md` §5).
- [ ] No new endpoint accepts or executes free-form SQL, shell commands, or file paths from the client.
- [ ] No secret, API key, or credential appears in source code or committed `.env` files (only `.env.example` with placeholder values is committed).
- [ ] Error responses returned to the client never include a Python traceback or raw exception text.
- [ ] CORS configuration in the reviewed code does not use `*` in a production code path.

## 5. Forbidden Patterns (explicit, for AI-agent guardrails)

```python
# FORBIDDEN — string-built SQL
query = f"SELECT * FROM encounters WHERE condition_id = {condition_id}"

# FORBIDDEN — arbitrary SQL execution endpoint
@app.post("/api/run-sql")
def run_sql(sql: str): ...

# FORBIDDEN — patient identity inference
def find_same_patient(row1, row2):
    return row1["name"] == row2["name"]  # Name doesn't exist in schema; this pattern is banned regardless

# FORBIDDEN — returning raw exception to client
except Exception as e:
    return {"error": str(e)}   # leaks internals; use the frozen generic error shape instead

# CORRECT pattern
query = "SELECT * FROM encounters WHERE condition_id = ?"
cursor.execute(query, (condition_id,))
```

## 6. Data-Quality Transparency (a security-adjacent trust practice)

The negative-billing exclusion (`billing_is_valid = 0`) is never silently hidden — its count is surfaced via `excluded_invalid_billing_count` in the `/api/analytics/billing` response (`06-api-contract.md`). Transparent handling of messy data is treated as part of the security/integrity posture of the system, not just a UX nicety.
