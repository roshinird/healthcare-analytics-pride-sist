# 02 — Technology Stack

**Status:** Authoritative. This is the final, frozen technology selection — do not substitute alternatives without developer approval.

---

## Frontend

| Tech | Purpose | Why chosen | Why alternatives rejected |
|---|---|---|---|
| **React 18** | UI library | Team familiarity, huge AI-coding-agent training coverage (lowest implementation risk), component model fits a filter+chart dashboard well | Vue/Svelte: less AI-agent tooling reliability for this use case |
| **Vite** | Build tool/dev server | Fastest dev loop for AI-assisted iterative coding; zero-config TS/JSX support | Next.js: SSR/routing/deployment complexity has no payoff for a single-page dashboard |
| **Tailwind CSS** | Styling | Fast, consistent utility styling; avoids "generic Bootstrap" default look when paired with the custom tokens in `09-ui-design-system.md` | Plain CSS: slower to iterate; component libraries (MUI): heavier, harder to make look non-generic |
| **Recharts** | Charting (MUST) | React-native composable API, clean defaults, small bundle, sufficient for all 9 chart types needed | Plotly: heavier bundle, more config for no visual gain here; Chart.js: less idiomatic in React |
| **Lucide-react** | Icons | Small, consistent, free, professional (no clip-art medical imagery) | Font Awesome: heavier, less consistent visual weight |

**Rejected entirely:** Framer Motion (adds bundle/complexity for marginal visual gain — at most a single optional fade-in if time allows, never required), any state-management library (Redux/Zustand) — local component state + one shared filter context is sufficient at this scale.

## Backend

| Tech | Purpose | Why chosen | Why alternatives rejected |
|---|---|---|---|
| **Python 3.11+** | Language | Required by course, best Pandas/NumPy ecosystem | — |
| **FastAPI** | Web framework | Pydantic validation built in (directly satisfies security requirements), auto-generated OpenAPI docs (free viva artifact), clean typed route definitions | Flask: no built-in validation, more boilerplate for the same safety guarantees; Django: far too heavy for a read-only 8-endpoint API |
| **Pydantic** | Request/response validation | Ships with FastAPI, enforces the frozen API contract at the type level | Manual validation: error-prone, slower to write, harder for an AI agent to get right consistently |
| **Uvicorn** | ASGI server | Standard FastAPI production server, works directly on Render | — |

## Data Layer

| Tech | Purpose | Why chosen | Why alternatives rejected |
|---|---|---|---|
| **SQLite** | Database | Zero setup, file-based, ships inside the repo/container, fully supports every required SQL feature (CTEs, window functions since 3.25+, views, indexes) | PostgreSQL: adds a separate hosted service, connection-string management, and a cold-start/connection-limit risk for zero academic benefit at ~55K rows |
| **Pandas** | Transformation layer | Required by course; genuinely used for percentage shares, pivoting, rolling averages, and data-quality summaries (see `07-backend-architecture.md`) | — |
| **NumPy** | Statistical calculation | Used narrowly and specifically for `np.percentile` (IQR outlier detection) and LOS distribution stats — not imported as a checkbox | — |

## Visualization (Server-Side)

| Tech | Status | Purpose |
|---|---|---|
| **Matplotlib** | SHOULD HAVE | Generates one server-side "Executive Summary" PNG (multi-panel figure) via a dedicated endpoint — demonstrates portable, non-interactive Python visualization distinct from the client-side Recharts story. |

## Deployment

| Tech | Purpose | Why chosen | Why alternatives rejected |
|---|---|---|---|
| **Render (Free Web Service)** | Backend hosting | Free, no credit card, deploys directly from GitHub, runs a persistent Python process (unlike serverless-only platforms) | Vercel serverless functions: timeout model unsuitable for a persistent FastAPI+SQLite process; Railway/Fly.io: free tiers less reliable/require card in some configurations |
| **Vercel or Netlify (Free)** | Frontend hosting | Free static hosting, git-connected, ample bandwidth/build minutes for this project's scale | — (either is acceptable; pick one per team preference, document the choice in `11-deployment.md` at implementation time) |

**Known constraint to design around:** Render's free web service sleeps after ~15 minutes idle and cold-starts in 30–60s. This does not change the architecture — it changes the deployment runbook (pre-warm before a demo) and mandates the local-fallback path in `11-deployment.md`.

## Explicitly Rejected / Not Used

- PostgreSQL, MySQL, or any hosted database service
- Redis or any caching infrastructure
- Docker (not required at this scale; adds setup friction without payoff)
- Any authentication library or service
- Any ML/prediction library (scikit-learn, etc.)
- Any paid API (maps, geocoding, LLM, etc.)
- Any file-upload handling library

## Dependency Minimization Rule

Every dependency added beyond this list must be justified in writing (a one-line comment in the relevant spec file or PR description) against the "earns its place" rule used for database columns in `03-dataset.md`. Default answer to "should we add library X" is **no**.
