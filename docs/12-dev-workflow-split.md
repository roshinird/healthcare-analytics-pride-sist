# 12 — Developer Workflow Split

**Status:** Authoritative. Target: Dev A ≈ 58%, Dev B ≈ 42% of actual technical implementation. Documentation/markdown/GitHub-setup time is not counted toward these percentages.

---

## 1. Frozen Interfaces (must exist before parallel work begins)

- `04-database-schema.md` — exact table/column definitions
- `06-api-contract.md` — exact endpoints, params, response shapes, mock JSON
- `frontend/src/mocks/*.json` — fixture files matching the frozen response shapes exactly

Once these three are in place (they already are, as of this spec set), **Dev A and Dev B can start simultaneously with zero blocking dependency.**

## 2. Task / Hour Table

| Task | Owner | Hours | Depends on |
|---|---|---|---|
| Ingestion script (drop Name/Doctor/Room/Medication, LOS calc, billing validation flag) + seed script + table/view creation | Dev B | 0.75h | `03-dataset.md`, `04-database-schema.md` |
| SQL query layer — all 9 MUST questions (`services/queries.py`) | Dev B | 1.5h | `05-sql-analytics.md` |
| Pandas transformation layer (`services/analytics.py`) — shares, pivots, data-quality summary | Dev B | 1.0h | SQL layer above |
| FastAPI routes, Pydantic schemas, CORS, error handling (`routers/`, `schemas.py`, `main.py`) | Dev A | 1.25h | `06-api-contract.md` |
| React scaffold: Vite/Tailwind setup, layout, KPI row, filter bar | Dev A | 1.0h | `08-frontend-architecture.md`, `09-ui-design-system.md` |
| Chart components (Recharts), all 7–8 charts wired to **mock JSON** | Dev A | 1.25h | mock fixtures |
| SHOULD-have: IQR outlier stats (`services/stats.py`) + Matplotlib report endpoint (`services/report.py`) | Dev B | 0.75h | SQL/Pandas layer |
| Integration: flip `VITE_USE_MOCK=false`, point at live backend, verify every chart against real data | Dev A | 0.75h | Both subsystems complete |
| Testing/debugging (row-count checks, contract checks, chart sanity) | Dev A + Dev B | 0.5h + 0.5h | Integration complete |
| Deployment (Render backend, Vercel/Netlify frontend) + local fallback verification | Dev A | 0.5h | Integration complete |

**Core MUST-have total: 9.0h combined.**
**Dev A: 5.25h (58.3%) | Dev B: 3.75h (41.7%)** — matches target.

**Optional SHOULD-have stretch** (IQR stats + Matplotlib, included above at 0.75h to Dev B) keeps the total at 9.0h; if additional SHOULD-have polish (mobile responsiveness pass, rolling average) is added, expect up to 9.75–10h total, still within budget.

## 3. What Each Developer Starts With

- **Dev A starts with:** the frontend — scaffold, layout, KPI row, filter bar, all charts built and fully demoable against `frontend/src/mocks/*.json`. Dev A does not wait on Dev B at any point during this phase.
- **Dev B starts with:** the database — ingestion, schema, SQL query layer, Pandas transformation layer, all independently testable via plain Python function calls (no FastAPI server needed to verify `services/queries.py` output against `05-sql-analytics.md`).

## 4. Parallelization Strategy

Both developers work off the same frozen `04-database-schema.md` and `06-api-contract.md` from hour 0. Neither needs to wait for the other to produce a single line of code before starting their own subsystem. The only synchronization point is the **integration task**, scheduled after both subsystems are individually complete and self-tested.

## 5. Branch Strategy

- `main` — protected, only merged via reviewed PR.
- `dev-a/frontend` — Dev A's working branch.
- `dev-b/backend` — Dev B's working branch.
- Both branches merge into `main` independently once each subsystem passes its own self-test (frontend renders correctly against mocks; backend returns contract-correct JSON via `curl`/manual testing).
- Integration happens **on `main`** after both merges, as a short final branch (`integration`) that flips the mock flag and fixes any last-mile mismatches, then merges back.

## 6. Integration Sequence

1. Confirm Dev B's backend runs locally and every endpoint returns a response matching `06-api-contract.md` exactly (spot-check with `curl` against 2–3 endpoints minimum, all 8 if time allows).
2. Confirm Dev A's frontend renders correctly against `mocks/*.json` with no console errors.
3. Set `VITE_USE_MOCK=false`, `VITE_API_BASE_URL=http://localhost:8000` in the frontend `.env`.
4. Run both servers locally; click through every filter combination once; confirm every chart updates correctly.
5. Fix any field-name or shape mismatches — these should be rare/zero if both sides followed `06-api-contract.md` exactly; if found, the fix is almost always a one-line rename, not a redesign.
6. Proceed to deployment (`11-deployment.md`).

**Target integration time: 30–45 minutes**, consistent with "integration should take minutes, not hours."

## 7. Handoff Requirements

- Dev B's PR must include: seed script run instructions, confirmation of the 6 validation checks in `04-database-schema.md` §9, and a short note of any deviation from the mapped SQL in `05-sql-analytics.md` (there should be none, but document if unavoidable).
- Dev A's PR must include: confirmation that all 8 MUST-endpoints' mock fixtures render correctly, and a screenshot or short recording of the dashboard for the other developer to sanity-check before integration.

## 8. What Dev A Must Verify Before Final Integration (Dev A is the integration owner)

- [ ] All 9 analytics questions are visually represented and match `05-sql-analytics.md` semantics (correct labels — "Total Encounters" not "Total Patients", "Above-Average Billing" not "outliers").
- [ ] No dropped/prohibited field appears anywhere in the UI (no doctor name, no room number, no medication, no patient ID).
- [ ] Filters work correctly across all charts simultaneously.
- [ ] The synthetic-data / non-clinical disclaimer is visible in the footer.
- [ ] The app is deployable and the local fallback path has been tested end-to-end at least once.
