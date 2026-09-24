# Lead Gen

Lead Gen is a free-first, BYOK lead discovery and outreach web app.

It combines automated web search, AI cleanup, website research, lead enrichment,
Excel/CSV import/export, email campaigns, follow-ups, reply tracking, Hostinger
mail delivery, admin controls and production deployment in one focused interface.

## Product flow

```text
Find Leads -> Enrich -> Review -> Export / Outreach -> Follow-ups -> Replies
```

## Stack

- React + Vite + TypeScript + Tailwind CSS
- FastAPI + Python
- Firebase Authentication
- Turso database
- Serper / Brave search adapters
- Gemini / OpenAI BYOK
- Prospeo / Apollo BYOK
- Hostinger Agentic Mail + optional Gmail
- Render static site + API deployment

## Branding

The application name is **Lead Gen**. The supplied Lead Gen artwork is included in
`frontend/public/` and is used for the sidebar, authentication experience, browser
favicon, Apple touch icon and web-app manifest.

## Local development

### Backend

```powershell
cd backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.db.migrate
pytest -q
uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm install --include=optional
npm run check
npm run test
npm run build
npm run dev
```

### Outreach worker while developing locally

Keep a third terminal open:

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m app.outreach.worker
```

With local `BACKGROUND_JOBS_MODE=inline`, lead discovery/enrichment continues to run
through FastAPI background tasks, so a separate lead worker is optional locally.

## Zero-cost Render deployment

The default `render.yaml` is intentionally designed for **$0 Render compute**:

- Frontend: free Render Static Site
- Backend: one Free Render Web Service
- Lead worker: embedded in the API process
- Outreach worker: embedded in the API process
- Database: Turso (external)
- Auth: Firebase (external)

Set these on the API in Render:

```text
APP_ENV=production
BACKGROUND_JOBS_MODE=embedded
EMBEDDED_WORKERS=true
CORS_ORIGINS=https://YOUR-FRONTEND.onrender.com
FRONTEND_APP_URL=https://YOUR-FRONTEND.onrender.com
PUBLIC_API_URL=https://YOUR-API.onrender.com
ADMIN_EMAILS=YOUR_ADMIN_EMAIL
FIREBASE_PROJECT_ID=...
FIREBASE_SERVICE_ACCOUNT_JSON=...
TURSO_DATABASE_URL=...
TURSO_AUTH_TOKEN=...
CREDENTIAL_ENCRYPTION_KEY=...
```

The free API sleeps after Render's idle period. While the Lead Gen browser tab is
open, the frontend performs a lightweight periodic health check, which keeps the API
responsive during active use. If the browser is closed and Render sleeps, pending
scheduled jobs remain in Turso and resume when the API wakes again.

This no-cost mode is ideal for personal use and testing. For strict always-on
scheduled delivery, `render-scaled.yaml` keeps the separate worker architecture and
requires paid Render compute.

See `docs/PRODUCTION_DEPLOYMENT.md` for the exact deployment sequence.

## Important local files to preserve during ZIP upgrades

Never overwrite or commit:

```text
.git/
backend/.env
backend/.venv/
frontend/.env
frontend/node_modules/
Firebase service-account JSON
```

Also never regenerate `CREDENTIAL_ENCRYPTION_KEY` after provider/sender credentials
have been saved, because existing encrypted credentials depend on it.

## Release validation

Before calling a deployment ready, run:

```text
Backend pytest
Database migration twice (second run must be idempotent)
Frontend TypeScript check
Frontend tests
Frontend production build
One automated discovery run
One export
One Hostinger Quick Send to an address you control
One campaign send
One reply/follow-up test
Admin page test
```

See `docs/FINAL_RELEASE_CHECKLIST.md`.
