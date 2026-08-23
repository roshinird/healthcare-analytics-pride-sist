# 00 — Project Overview

**Status:** Authoritative (non-frozen, but must stay consistent with 04, 06, 14)
**Applies to:** any AI-assisted coding agent (Claude Code, Cursor, Windsurf, or any other tool) and both human developers.

---

## 1. Project

**Healthcare Analytics using SQL and Python Libraries** — an Advanced SQL and Python course final project.

## 2. Problem Statement

Hospitals and health systems generate large volumes of admission-level operational data. Turning that raw data into decision-useful insight requires: a well-designed relational schema, non-trivial SQL (joins, aggregation, window functions, CTEs), Python-based transformation (Pandas/NumPy), and a professional presentation layer (API + dashboard). This project builds a small, complete, end-to-end system that demonstrates that full pipeline on a single, realistic, freely available healthcare dataset.

## 3. Educational Objective

Demonstrate — genuinely, not superficially — for an Advanced SQL and Python course:
- Relational database design (appropriately simple, not over-engineered)
- Advanced SQL: JOIN, GROUP BY, HAVING, CASE, CTE, window functions, subqueries, date functions, views, indexes
- Python data handling: Pandas transformation, NumPy statistical calculation
- Backend/API development (FastAPI)
- Professional frontend/dashboard development (React)
- Sound engineering judgment about scope, data-quality handling, and privacy

## 4. Target User

A course evaluator / viva panel, and — in the product fiction — a hospital operations analyst reviewing encounter-level trends. **Not** a clinician, and **not** a real hospital's IT department.

## 5. System Overview

```
SQLite (encounters + ref_medical_condition)
      │  parameterized SQL (JOIN, GROUP BY, CTE, window fns, subqueries, view)
      ▼
FastAPI backend (services/queries.py → services/analytics.py)
      │  Pandas transformation + NumPy statistics
      ▼
JSON API (versionless, read-only, 9 endpoints)
      │  fetch()
      ▼
React + Vite dashboard (KPI cards, filters, Recharts charts)
```

One optional path: FastAPI can also return a **Matplotlib-generated PNG** report (SHOULD HAVE) as a second, distinct visualization channel.

## 6. Dataset Framing

The system analyzes a **single, public, synthetic** Kaggle dataset ("Healthcare Dataset", prasad22, ~55,500 rows). Each row is an **independent synthetic admission/encounter record**. There is **no real patient**, **no real hospital**, and **no real clinician** behind any row. Full detail in `03-dataset.md` — that file is authoritative for all dataset semantics and must be read before touching ingestion code.

## 7. Scope (summary — full detail in `01-requirements.md`)

- **MUST HAVE:** core schema, 9 analytics questions, 8 MUST API endpoints, React dashboard with filters and charts, deployment, security rules.
- **SHOULD HAVE:** IQR billing-outlier analysis, Matplotlib report endpoint, 3-month rolling average.
- **NICE TO HAVE:** CSV export, searchable hospital filter.
- **DO NOT BUILD:** anything involving patient identity, readmission, department analytics, doctor analytics, diagnosis/treatment/prediction, authentication, or any paid/hosted infrastructure.

## 8. Non-Goals

This is **not**:
- A clinical decision-support or diagnostic system
- An EHR or patient portal
- A predictive/ML system
- A multi-tenant or authenticated product
- A system that tracks or infers real patient identity across records

## 9. Success Criteria

The project is successful if, at the end of implementation:
1. All 9 MUST-HAVE analytics questions run correctly against the seeded database and are visible on the dashboard.
2. The dashboard loads, filters, and renders all charts with no console errors, against both mock and live API data.
3. The deployed (or locally run) system can be demoed end-to-end in under 5 minutes.
4. No dropped/prohibited field (patient identity, doctor entity, department, room number, medication) reappears anywhere in the schema, API, or UI.
5. Total combined technical implementation time stays within **8–10 hours**.

## 10. Hard Constraints (repeated here for visibility — authoritative versions live in their own files)

- **Time:** 8–10 combined technical man-hours (see `12-dev-workflow-split.md`).
- **Cost:** ₹0 total — no paid API, dataset, hosting, or database (see `11-deployment.md`).
- **Team:** Two developers, shared GitHub repo. Dev A ≈ 58% technical implementation (lead + integration owner), Dev B ≈ 42% (independent subsystem owner).
- **Development method:** Entirely AI-assisted/vibe-coded. Any AI coding agent may be used — the documentation in this project root is written to be **tool-agnostic** and must not assume any specific product.

## 11. Technology-Independent AI-Assisted Implementation Principle

These 15 files are the **persistent implementation context** for whichever AI coding agent is used. They are intentionally written as deterministic engineering specifications (exact schema, exact API contract, exact file layout) rather than prose suggestions, so that:
- Any competent AI coding agent can implement against them with minimal ambiguity.
- Switching tools mid-project (e.g., starting in one agent, continuing in another) does not lose context — the context lives in these files, not in a chat history.
- `04-database-schema.md`, `06-api-contract.md`, and `14-ai-agent-instructions.md` are **frozen**: no agent may alter the decisions in these files without explicit developer approval. See `14-ai-agent-instructions.md` for the full guardrail list.

## 12. How to Use This Spec Set

1. Read this file first.
2. Read `14-ai-agent-instructions.md` before writing any code.
3. Read `03-dataset.md` and `04-database-schema.md` before touching ingestion/DB code.
4. Read `06-api-contract.md` before touching backend or frontend code.
5. Everything else is scoped to the relevant subsystem (backend files for Dev B, frontend files for Dev A, shared files for both).
