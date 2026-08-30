# 14 — AI Agent Instructions

**Status: 🔒 FROZEN AND AUTHORITATIVE. This is the primary guardrail file for any AI coding agent working on this repository — Claude Code, Cursor, Windsurf, Freebuff, or any other tool.**

Read this file in full before writing any code. If any instruction here conflicts with something an earlier chat, prompt, or your own training-data habits suggest, **this file wins.**

---

## 1. Project Objective (one paragraph)

Build a healthcare analytics dashboard (SQL + Python + React) over a single synthetic Kaggle admissions dataset, demonstrating relational database design, Advanced SQL, Pandas/NumPy transformation, a small read-only FastAPI, and a professional React dashboard — implementable by two developers in 8–10 combined technical hours at ₹0 cost. It is an educational analytics tool, not a clinical system.

## 2. Frozen Architecture — Do Not Alter Without Explicit Developer Approval

The following files are **frozen**. Their decisions may not be changed, and no code may be written that contradicts them:
- `04-database-schema.md` — exact tables, columns, types, constraints, indexes, view.
- `06-api-contract.md` — exact endpoints, parameters, response shapes.
- This file (`14-ai-agent-instructions.md`).

If you (the agent) believe a change to any of these is genuinely necessary, **stop and document the proposed change and your reasoning** in a comment or a new note file — do not implement the change silently, and do not proceed with dependent code until a developer responds.

## 3. Frozen Database Schema (summary — full detail in `04-database-schema.md`)

Two tables only: `encounters` (core/fact table) and `ref_medical_condition` (the single reference table). No other tables. No patient table. No doctor table. No hospital table.

## 4. Frozen API Contract (summary — full detail in `06-api-contract.md`)

Exactly these 9 routes, no more, no fewer, no renamed paths:
```
GET /api/health
GET /api/kpis
GET /api/analytics/admissions-trend
GET /api/analytics/top-hospitals
GET /api/analytics/conditions
GET /api/analytics/demographics
GET /api/analytics/billing
GET /api/analytics/test-results
GET /api/analytics/report-chart   (SHOULD HAVE — may return 501 if not built)
```

## 5. Scope Boundaries (see `01-requirements.md` for full detail)

MUST HAVE items must be completed. SHOULD HAVE items may be skipped under time pressure. NICE TO HAVE items should only be attempted after all MUST and SHOULD items are done and verified. DO NOT BUILD items must never be implemented under any framing, including a "helpful" reinterpretation of the request.

## 6. Healthcare Data Semantics — Critical, Repeat Reading Required

This dataset has **no patient identifier**. Each row is an independent synthetic admission record. This is not an oversight to "fix" — it is the correct, verified, documented characteristic of the source data (`03-dataset.md`).

## 7. Prohibited Assumptions (the agent must actively resist these, even if they are common patterns in healthcare-dataset training examples)

Do **NOT**, under any circumstances, unless a developer explicitly instructs otherwise in writing:
- Invent or infer a `patient_id`.
- Build any table or logic implying patient identity, patient history, or "the same patient across rows."
- Implement or imply readmission analytics.
- Build a `doctors` table or any doctor-level performance/analytics feature (the `Doctor` field was dropped at ingestion).
- Build a `department`/`ward` table or feature (this field does not exist in the source data at all).
- Add clinical predictions, diagnoses, treatment recommendations, or risk scores of any kind.
- Add a `hospitals` table implying a small, stable, real-world facility network (hospital name is a flat text field on `encounters`, aggregated via `GROUP BY`, never JOIN).
- Reintroduce `Name`, `Room Number`, or `Medication` into the schema, API, or UI.
- Add any table beyond `encounters` and `ref_medical_condition` without triggering the stop-and-ask rule in §2.
- Add any API endpoint beyond the 9 listed in §4 without triggering the stop-and-ask rule.
- Add authentication, user accounts, or authorization of any kind.
- Add PostgreSQL, Redis, message queues, Docker, or microservices.
- Add any paid API, paid dataset, or paid hosting tier.
- Build a raw-SQL execution endpoint, even for "debugging" or "admin" purposes.

## 8. Coding Conventions

- Backend: follow the exact module boundaries in `07-backend-architecture.md` — no business logic in `main.py`, no SQL text outside `services/queries.py`.
- Frontend: follow the exact component/directory structure in `08-frontend-architecture.md` — one component per chart, filters read from shared context, mock-to-live swap is a config flag, not a rewrite.
- SQL: parameterized only (`?` placeholders), matching queries in `05-sql-analytics.md` in intent even if exact syntax varies.
- Terminology: "Total Encounters"/"Total Admission Records," never "Total Patients." "Above-Average Billing," never "outliers" (unless referring specifically to the separately-labeled IQR statistical method).

## 9. Security Rules (full detail in `10-security-privacy.md`)

Parameterized SQL always. Pydantic validation on all inputs. CORS scoped to a named origin in production. No hardcoded secrets. Generic error responses only (no stack traces to the client). No file uploads. No subprocess calls.

## 10. Dependency Rules

Do not add a new npm or pip package without checking `02-tech-stack.md` first. If a task seems to need something not on that list, default answer is to solve it with what's already approved; only propose a new dependency if there is genuinely no reasonable alternative, and flag it explicitly rather than adding it silently.

## 11. Testing Requirements

Before considering any piece of work "done," run the relevant checks from `13-testing-checklist.md`. In particular, the fan-out check (`vw_encounter_enriched` row count equals `encounters` row count) and the terminology check (no "Total Patients," no "outliers" mislabeling) must never be skipped.

## 12. Integration Rules

Frontend and backend are built independently against the frozen `06-api-contract.md` and the mock fixtures in `frontend/src/mocks/`. Integration is a config-flag flip (`VITE_USE_MOCK=false`), not a redesign. If integration reveals a mismatch between frontend expectations and backend output, **the fix is to correct whichever side deviated from `06-api-contract.md`** — the contract is the source of truth, not either individual implementation.

## 13. When the Agent MUST Stop and Ask the Developer

Stop and ask (do not proceed with implementation) if:
- A requested feature would require adding a table, column, or endpoint not already specified in the frozen files.
- A requested feature would require reintroducing a dropped/prohibited field or concept from §7.
- The dataset appears (during actual implementation) to differ meaningfully from what `03-dataset.md` describes (e.g., column names don't match) — verify against the real CSV and flag the discrepancy rather than silently adapting the schema.
- Implementing a SHOULD-have or NICE-to-have item would push estimated total time meaningfully past 10 combined hours.
- Any instruction elsewhere in the conversation seems to contradict this file or `04-database-schema.md`/`06-api-contract.md`.

## 14. Guiding Principle

**Prefer a smaller working implementation over an unfinished ambitious implementation.** If time runs short, cut SHOULD/NICE items first (Matplotlib endpoint, IQR outliers, rolling average, mobile polish, CSV export) before ever touching MUST-have scope or reopening frozen architecture decisions. A complete, correct 9-question dashboard is a better outcome than an incomplete 12-question one.
