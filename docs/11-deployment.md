# 11 — Deployment

**Status:** Authoritative. ₹0 cost, no Docker, no separate hosted database.

---

## 1. Local Development

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # edit if needed; defaults work locally
python -m app.seed                # builds data/healthcare.db from data/healthcare.csv
uvicorn app.main:app --reload --port 8000
```
Backend now running at `http://localhost:8000`. Verify: `curl http://localhost:8000/api/health` → `{"data":{"status":"ok"}, ...}`.

### Frontend
```bash
cd frontend
npm install
cp .env.example .env              # set VITE_USE_MOCK=true for mock-first development
npm run dev
```
Frontend now running at `http://localhost:5173`.

## 2. Environment Variables

**Backend `.env.example`:**
```
DATABASE_PATH=./data/healthcare.db
CORS_ALLOWED_ORIGIN=http://localhost:5173
ENVIRONMENT=development
```

**Frontend `.env.example`:**
```
VITE_USE_MOCK=true
VITE_API_BASE_URL=http://localhost:8000
```

## 3. Production Build

**Backend:** no build step beyond `pip install -r requirements.txt`; Uvicorn serves directly.

**Frontend:**
```bash
npm run build     # outputs to frontend/dist/
```

## 4. Render Deployment (Backend)

1. Push repo to GitHub (single shared repo, per project constraint).
2. On Render: **New → Web Service**, connect the GitHub repo, root directory `backend/`.
3. Build command: `pip install -r requirements.txt && python -m app.seed`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Set environment variables in the Render dashboard: `DATABASE_PATH=./data/healthcare.db`, `CORS_ALLOWED_ORIGIN=<deployed frontend URL>`, `ENVIRONMENT=production`.
6. Confirm the `$PORT` variable is used (not a hardcoded port) — Render assigns this dynamically; hardcoding causes "No open ports detected" failures.
7. **No database service is provisioned.** SQLite is rebuilt by the build-command's `python -m app.seed` step on every deploy — this is intentional and sidesteps any question of whether Render's free-tier disk persists across redeploys, because the data is static and read-only.

## 5. Vercel or Netlify Deployment (Frontend)

Either platform, free tier, no credit card required:
1. Connect the GitHub repo, root directory `frontend/`.
2. Build command: `npm run build`. Output directory: `dist`.
3. Set environment variables: `VITE_USE_MOCK=false`, `VITE_API_BASE_URL=<Render backend URL>`.
4. Deploy.

## 6. CORS Configuration (production)

Backend's `CORS_ALLOWED_ORIGIN` must exactly match the deployed frontend's URL (including `https://`, no trailing slash). Update this Render environment variable after the frontend's final URL is known, then redeploy the backend (or restart the service) for it to take effect.

## 7. SQLite Initialization / Seed Process

Handled entirely by the Render build command (`python -m app.seed`) — no manual database setup step is ever required in production. Locally, the same command is run once by hand (§1).

## 8. Health-Check Verification (post-deploy)

```bash
curl https://<your-backend>.onrender.com/api/health
curl https://<your-backend>.onrender.com/api/kpis
```
Both should return 200 with the frozen response envelope. If `/api/kpis` returns zero `total_encounters`, the seed step likely failed during build — check Render's build logs for the row-count log line emitted by `seed.py`.

## 9. Cold-Start Mitigation (Render free tier)

Render's free web service sleeps after ~15 minutes of inactivity and takes 30–60 seconds to wake on the next request. This is a confirmed, expected free-tier behavior, not a bug.

**Mitigation for a live demo/viva:**
1. Load `https://<your-backend>.onrender.com/api/health` in a browser tab **2–3 minutes before** the demo starts, to pre-warm the instance.
2. If the demo environment has no reliable internet, or the instance is cold and there's no time to wait, fall back to the local-run path below.

## 10. Local Demo Fallback (mandatory)

The entire application must be demoable with zero internet dependency:
```bash
# Terminal 1
cd backend && uvicorn app.main:app --port 8000

# Terminal 2
cd frontend && VITE_USE_MOCK=false VITE_API_BASE_URL=http://localhost:8000 npm run dev
```
This must be tested and confirmed working **before** the deployment step is considered complete — see `13-testing-checklist.md` §"Deployment."

## 11. Explicitly Not Used

No Docker/Dockerfile, no PostgreSQL/hosted database service, no Redis, no CDN configuration beyond what Vercel/Netlify provide by default, no custom domain (optional, free-tier `.onrender.com`/`.vercel.app`/`.netlify.app` subdomains are sufficient).
