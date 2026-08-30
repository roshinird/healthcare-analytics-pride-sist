# Healthcare Analytics (SQL + Python)

An Advanced SQL and Python course project: a small, end-to-end healthcare analytics dashboard built over a single synthetic hospital admissions dataset. The system demonstrates relational database design, Advanced SQL (JOINs, CTEs, window functions, subqueries, views, indexes), Python data transformation (Pandas/NumPy), a read-only FastAPI backend, and a professional React dashboard frontend.

**This is an educational analytics project, not a clinical system.** The dataset is fully synthetic — it contains no real patients, clinicians, or facilities — and the application performs descriptive/operational analytics only. It does not diagnose, predict, or recommend treatment.

## Technology Summary

- **Backend:** Python, FastAPI, Pydantic, SQLite, Pandas, NumPy
- **Frontend:** React, Vite, Tailwind CSS, Recharts, Lucide
- **Visualization:** Recharts (interactive, MUST HAVE) + Matplotlib (server-generated summary report, SHOULD HAVE)
- **Deployment:** Render (backend) + Vercel or Netlify (frontend) — ₹0 cost, no credit card required

Full rationale for every technology choice is in [`docs/02-tech-stack.md`](docs/02-tech-stack.md).

## Dataset Summary

Kaggle "Healthcare Dataset" (prasad22), ~55,500 synthetic hospital admission/encounter records. Each row is an independent encounter — the dataset has **no patient identifier**, so the system does not track patients, readmissions, or longitudinal history. Full dataset semantics, retained/dropped columns, and cleaning rules are documented in [`docs/03-dataset.md`](docs/03-dataset.md).

## Developer Roles

- **Dev A** — Lead developer, integration owner, final QA, deployment. Primarily works in `backend/app/` (FastAPI routes, schemas, CORS, error handling) and all of `frontend/`.
- **Dev B** — Developer, independent subsystem owner. Primarily works in `backend/data/`, `backend/scripts/`, `backend/app/services/`, and `backend/app/schemas/` (ingestion, SQL query layer, Pandas/NumPy transformation).

Target technical workload split: **Dev A ≈ 58%, Dev B ≈ 42%**, combined implementation time **8–10 hours**. Full task/hour breakdown, parallelization strategy, and integration sequence: [`docs/12-dev-workflow-split.md`](docs/12-dev-workflow-split.md).

## Architecture Status

**The architecture is FROZEN.** In particular, [`docs/04-database-schema.md`](docs/04-database-schema.md), [`docs/06-api-contract.md`](docs/06-api-contract.md), and [`docs/14-ai-agent-instructions.md`](docs/14-ai-agent-instructions.md) are authoritative and must not be altered without explicit developer approval — this applies to human contributors and any AI coding agent working in this repository.

## Documentation

All 15 authoritative specification files live in [`docs/`](docs/):

| File | Purpose |
|---|---|
| [00-project-overview.md](docs/00-project-overview.md) | Purpose, scope, non-goals, success criteria |
| [01-requirements.md](docs/01-requirements.md) | Functional/non-functional requirements, MUST/SHOULD/NICE/DO-NOT-BUILD |
| [02-tech-stack.md](docs/02-tech-stack.md) | Frozen technology choices and rationale |
| [03-dataset.md](docs/03-dataset.md) | Dataset identity, semantics, cleaning rules, retained/dropped columns |
| [04-database-schema.md](docs/04-database-schema.md) | 🔒 Frozen exact schema (DDL, constraints, indexes, view) |
| [05-sql-analytics.md](docs/05-sql-analytics.md) | 9 MUST-HAVE analytics questions with SQL |
| [06-api-contract.md](docs/06-api-contract.md) | 🔒 Frozen exact API endpoints and response shapes |
| [07-backend-architecture.md](docs/07-backend-architecture.md) | Backend module structure and boundaries |
| [08-frontend-architecture.md](docs/08-frontend-architecture.md) | Frontend component structure and boundaries |
| [09-ui-design-system.md](docs/09-ui-design-system.md) | Design tokens, chart styling, layout rules |
| [10-security-privacy.md](docs/10-security-privacy.md) | Security rules, PII handling, forbidden patterns |
| [11-deployment.md](docs/11-deployment.md) | Local dev, Render/Vercel deployment, local fallback |
| [12-dev-workflow-split.md](docs/12-dev-workflow-split.md) | Dev A/B task and hour allocation |
| [13-testing-checklist.md](docs/13-testing-checklist.md) | QA checklist across DB, SQL, API, frontend, deployment |
| [14-ai-agent-instructions.md](docs/14-ai-agent-instructions.md) | 🔒 Frozen guardrails for any AI coding agent |

**Start with `00-project-overview.md`, then `14-ai-agent-instructions.md`, before writing any code.**

## Local Development

*To be completed during implementation.* Exact setup commands for the backend and frontend are specified in [`docs/11-deployment.md`](docs/11-deployment.md) and will be finalized once the corresponding implementation files (`requirements.txt`, `package.json`, seed script, etc.) exist.

## Repository Structure

```
healthcare-analytics/
├── docs/           # 15 authoritative specification files
├── backend/        # FastAPI + SQLite + Pandas/NumPy (Dev B: data/, scripts/, app/services/, app/schemas/ — Dev A: app/ integration)
├── frontend/        # React + Vite + Tailwind + Recharts (Dev A)
└── .github/          # CI/CD workflows (not yet configured)
```

## Disclaimer

This is an educational project built on a public, synthetic dataset. It contains no real patient, clinician, or facility data, and it must never be used, extended, or presented as a real clinical, diagnostic, or patient-management system.
