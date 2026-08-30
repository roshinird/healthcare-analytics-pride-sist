# Healthcare Analytics (SQL + Python + React)

An Advanced SQL and Python course project: an end-to-end healthcare analytics dashboard built over a single **synthetic** hospital admissions dataset. It demonstrates relational database design, Advanced SQL (JOIN, GROUP BY, HAVING, CASE, CTEs, window functions, subqueries, date functions, views, indexes), Python transformation with Pandas and NumPy, a read-only FastAPI backend, and a professional React dashboard.

**This is an educational analytics project, not a clinical system.** The dataset contains no real patients, clinicians, or facilities. The application performs descriptive and operational analytics only — it does not diagnose, predict, or recommend treatment.

---

## What this branch contains

This is the **Dev A** branch. It implements:

- The complete React dashboard — layout, filters, KPI row, all eight charts, loading/empty/error states, responsive behaviour.
- The FastAPI application shell — routers, Pydantic validation, CORS, error handling, configuration, health endpoint.
- Deployment configuration and CI.
- A development data source so the API and dashboard are runnable, testable and demoable **before** Dev B's data layer lands.

Dev B separately owns ingestion, the SQLite seed process, `services/queries.py` (SQL), `services/analytics.py` (Pandas), `services/stats.py` (NumPy) and `services/report.py` (Matplotlib). The two sides meet at the frozen API contract and nowhere else.

---

## Quick start

Two terminals. Nothing to install globally, nothing to pay for.

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/api/health` → `{"data":{"status":"ok"}, ...}`
Interactive API docs: <http://localhost:8000/docs>

Once Dev B's seed script exists, build the database first with `python -m app.seed`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env               # VITE_USE_MOCK=true works with no backend at all
npm run dev
```

Dashboard: <http://localhost:5173>

### Running against the live backend

Set `VITE_USE_MOCK=false` in `frontend/.env` and restart the dev server. That is the entire integration step — no component code changes (docs/08-frontend-architecture.md §4).

---

## Architecture

```
SQLite (encounters + ref_medical_condition)
   |  parameterized SQL - JOIN, GROUP BY, HAVING, CASE, CTE, window fns, subquery, view
   v
services/queries.py  ->  services/analytics.py (Pandas)  ->  services/stats.py (NumPy)
   v
FastAPI - 9 read-only GET routes, Pydantic-validated, frozen response envelope
   v
React + Vite dashboard - shared filter context, Recharts, per-card data states
```

One optional side channel: FastAPI can also render a Matplotlib "Executive Summary" PNG (SHOULD HAVE). The dashboard hides its download action when that endpoint is absent rather than showing a broken control.

### Technology

| Layer | Choice |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, Recharts, lucide-react |
| Backend | Python 3.11+, FastAPI, Pydantic, Uvicorn |
| Data | SQLite, Pandas, NumPy |
| Server-side charts | Matplotlib (SHOULD HAVE) |
| Hosting | Render (backend) + Vercel or Netlify (frontend) |

Rationale for every choice, including what was rejected and why, is in [`docs/02-tech-stack.md`](docs/02-tech-stack.md). Total cost is Rs. 0, and no step requires a credit card.

---

## The dashboard

Eight visualisations, each mapped to exactly one documented analytics question. Every card displays the question number and the SQL techniques behind it — a decorative chart would have nowhere to put that tag, which is the point.

| Card | Question | Techniques |
|---|---|---|
| Operational snapshot (KPI row) | Q1 | aggregates, conditional `CASE` |
| Monthly admissions trend | Q2 | CTE, `LAG`, `strftime`, Pandas rolling mean |
| Highest-volume facilities | Q3 | CTE, `RANK`, `GROUP BY` |
| Case mix by condition | Q4 | `JOIN` via view, `GROUP BY`, `HAVING` |
| Average length of stay by condition | Q5 | `JOIN`, `AVG`, `GROUP BY` |
| Who these encounters represent | Q6 | `CASE` bucketing, `GROUP BY` |
| Billing by payer | Q7 | `GROUP BY`, `SUM`, `AVG` |
| Cost profile by admission urgency | Q7 / Q8 | `GROUP BY`, scalar subquery, NumPy IQR |
| Test results by admission urgency | Q9 | two-dimensional `GROUP BY`, Pandas pivot |

Full SQL for each is in [`docs/05-sql-analytics.md`](docs/05-sql-analytics.md).

---

## Dataset and its constraints

Kaggle "Healthcare Dataset" (prasad22), ~55,500 synthetic admission records.

Three properties of this data shaped every downstream decision:

1. **There is no patient identifier.** Each row is an independent encounter. The system therefore counts *encounters*, never patients, and implements no readmission or longitudinal feature. This is a correctness rule, not a style preference.
2. **`Doctor` and `Hospital` are high-cardinality generated text** with no meaningful repeat structure, so neither is normalised into a table. `hospital_name` stays a flat column and is aggregated with `GROUP BY`.
3. **`Billing Amount` contains negative values.** Those rows are retained in the database but flagged `billing_is_valid = 0` and excluded from every financial aggregate — and the excluded count is displayed on the billing card rather than quietly dropped.

`Name`, `Doctor`, `Room Number` and `Medication` are dropped at ingestion and never persisted, logged, queried or returned. Full semantics: [`docs/03-dataset.md`](docs/03-dataset.md).

---

## Testing

```bash
cd backend  && python -m pytest        # 63 tests
cd frontend && npm run lint            # ESLint
cd frontend && npm run test            # 41 tests
cd frontend && npm run build           # production build
```

CI runs all four on every push and pull request ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

The backend suite asserts the frozen contract directly: the exact envelope, the exact field set per endpoint, that SHOULD-HAVE keys are present-and-null rather than omitted, that the OpenAPI surface is exactly the nine documented routes, that a zero-row filter returns 200 with a note rather than a 404, and that no dropped identity field appears in any response. The frontend suite asserts the mock fixtures match that same contract, so mock-to-live integration cannot drift silently.

Manual checklist: [`docs/13-testing-checklist.md`](docs/13-testing-checklist.md).

---

## Deployment

Backend to Render, frontend to Vercel or Netlify, both free tier.

1. Push to GitHub.
2. Render -> New Web Service, root directory `backend/`, or import [`render.yaml`](render.yaml). Build: `pip install -r requirements.txt && python -m app.seed`. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Use `$PORT` — a hardcoded port fails with "no open ports detected".
3. Vercel or Netlify -> root directory `frontend/`, build `npm run build`, output `dist`. Set `VITE_USE_MOCK=false` and `VITE_API_BASE_URL` to the Render URL.
4. Set `CORS_ALLOWED_ORIGIN` on Render to the exact frontend URL (with `https://`, no trailing slash) and redeploy.

**Cold starts are expected.** Render's free web service sleeps after ~15 minutes idle and takes 30–60 seconds to wake. Load `/api/health` two to three minutes before a demo to pre-warm it.

**Local fallback (mandatory before the demo counts as ready):**

```bash
# Terminal 1
cd backend && uvicorn app.main:app --port 8000
# Terminal 2
cd frontend && VITE_USE_MOCK=false VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

Full runbook: [`docs/11-deployment.md`](docs/11-deployment.md).

---

## Security and privacy

Healthcare domain, so the bar is higher than a generic analytics project — but this builds disciplined engineering practice, not compliance infrastructure.

- Parameterized SQL only. No f-string, `.format()` or `%` SQL construction from user input, anywhere.
- No endpoint accepts or executes free-form SQL. Permanent constraint.
- Every query parameter is Pydantic-validated before reaching a service function; invalid input returns 422 with the frozen error shape.
- Unhandled exceptions return a generic message. Tracebacks, exception text and file paths are logged server-side only, and a test asserts they never reach a client.
- CORS is scoped to a single named origin in production. `*` is permitted only in local development.
- No secrets in source. All configuration comes from environment variables; only `.env.example` is committed.
- No authentication, no file upload, no subprocess execution, no row-level encounter data, no patient-identity inference.

Details and the pre-merge review checklist: [`docs/10-security-privacy.md`](docs/10-security-privacy.md).

---

## Development notes

### Where the two developers meet

`backend/app/services/datasource.py` is the only seam. It imports Dev B's `queries`/`analytics` modules when the seeded database is present, and otherwise serves contract-shaped fixtures from `dev_fixtures.py`. The expected builder signatures are documented at the top of that file.

**Fixture responses are always flagged in `meta.note`**, and the dashboard header shows a "Mock data" pill, so a screenshot can never be mistaken for computed analytics. If a single builder is missing during partial integration, that one endpoint falls back with a visible note instead of taking the dashboard down.

### Frozen files

[`docs/04-database-schema.md`](docs/04-database-schema.md), [`docs/06-api-contract.md`](docs/06-api-contract.md) and [`docs/14-ai-agent-instructions.md`](docs/14-ai-agent-instructions.md) are frozen. Their decisions may not be changed — by a human or an AI coding agent — without explicit developer approval. Any AI tool used on this repository must read `14-ai-agent-instructions.md` before writing code.

### Deviations from the specification, and why

| Deviation | Reason |
|---|---|
| `DATABASE_PATH` defaults to `./data/database/healthcare.db` rather than `./data/healthcare.db` | Matches the directory layout and root `.env.example` already present in the repository skeleton. The value is environment-configurable either way. |
| Backend `schemas` is a package rather than a single `schemas.py` | The skeleton ships `backend/app/schemas/` as a directory; request and response models are split across `params.py` and `responses.py`. Module boundaries from `docs/07-backend-architecture.md` are unchanged. |
| `frontend/src/features/` and `frontend/src/charts/` removed | Both duplicate `components/charts/` from `docs/08-frontend-architecture.md`. `src/lib/` and `src/types/` were kept and given real content (formatting, chart theme, contract typedefs). |
| No Framer Motion | `docs/02-tech-stack.md` rejects it outright. Animation is CSS keyframes plus an IntersectionObserver reveal, with `prefers-reduced-motion` honoured throughout. |
| Vitest, Testing Library and ESLint added | Development dependencies only, not shipped or deployed. Justified against the dependency-minimisation rule by the testing requirements in `docs/13-testing-checklist.md`. |

---

## Documentation

All 15 authoritative specification files are in [`docs/`](docs/). Read [`00-project-overview.md`](docs/00-project-overview.md) first, then [`14-ai-agent-instructions.md`](docs/14-ai-agent-instructions.md).

| File | Purpose |
|---|---|
| [00-project-overview.md](docs/00-project-overview.md) | Purpose, scope, non-goals, success criteria |
| [01-requirements.md](docs/01-requirements.md) | Requirements and MUST/SHOULD/NICE/DO-NOT-BUILD scope |
| [02-tech-stack.md](docs/02-tech-stack.md) | Technology choices and rationale |
| [03-dataset.md](docs/03-dataset.md) | Dataset semantics, cleaning rules, retained/dropped columns |
| [04-database-schema.md](docs/04-database-schema.md) | FROZEN schema: DDL, constraints, indexes, view |
| [05-sql-analytics.md](docs/05-sql-analytics.md) | The 9 MUST-HAVE analytics questions, with SQL |
| [06-api-contract.md](docs/06-api-contract.md) | FROZEN endpoints and response shapes |
| [07-backend-architecture.md](docs/07-backend-architecture.md) | Backend module structure and boundaries |
| [08-frontend-architecture.md](docs/08-frontend-architecture.md) | Frontend component structure and boundaries |
| [09-ui-design-system.md](docs/09-ui-design-system.md) | Design tokens, chart styling, layout rules |
| [10-security-privacy.md](docs/10-security-privacy.md) | Security rules, PII handling, forbidden patterns |
| [11-deployment.md](docs/11-deployment.md) | Local dev, Render/Vercel deployment, local fallback |
| [12-dev-workflow-split.md](docs/12-dev-workflow-split.md) | Dev A/B task and hour allocation |
| [13-testing-checklist.md](docs/13-testing-checklist.md) | QA checklist across DB, SQL, API, frontend, deployment |
| [14-ai-agent-instructions.md](docs/14-ai-agent-instructions.md) | FROZEN guardrails for any AI coding agent |

---

## Disclaimer

This dashboard analyzes a synthetic, publicly available dataset of independent hospital admission records for educational purposes. The dataset contains no real patients, clinicians, or facilities. The system performs descriptive/operational analytics only — it does not diagnose, predict, or recommend clinical treatment. It must never be used, extended, or presented as a real clinical, diagnostic, or patient-management system.
