# Lead Gen — Current Project Context

This file is the handoff for continuing Lead Gen in another chat or coding session.

## Product

Lead Gen is a simple, premium-looking lead discovery and outreach web app.

User flow:

```text
Find Leads -> My Leads -> Outreach
```

Normal users see only:
- Find Leads
- My Leads
- Outreach
- Settings

Admins additionally see:
- Admin

## Current capabilities

- Firebase authentication
- Turso persistence
- Serper / Brave automated search
- Website crawling
- Gemini / OpenAI BYOK
- Prospeo / Apollo enrichment
- AI + deterministic lead cleanup
- Business-level deduplication/merge
- Excel/CSV import
- Excel/CSV export
- Hostinger Agentic Mail sender
- Optional Gmail sender
- Quick Send
- Templates
- Campaign preview/approval
- Persistent sending queue
- 20-second+ intervals
- Optional sending windows
- Follow-up sequences
- Reply sync + Hostinger live webhooks
- Stop on reply
- Suppression/unsubscribe
- Reply inbox
- Campaign analytics
- Admin dashboard
- Job retry / worker health
- Frontend response caching + request deduplication
- Turso connection pooling/batching
- Optimistic UI mutations

## Branding

Product name: **Lead Gen**

Colors:
- Purple `#7B61FF`
- Secondary `#9D84FF`
- Light purple `#B39CFF`
- Lime `#BCE953`
- Ink `#14151C`
- Slate `#4B4F5E`
- Lavender `#E8EAF3`
- White `#FFFFFF`

Fonts:
- Manrope headings
- Inter body/UI

The user-supplied logo assets live under `frontend/public/`.

## Stack

Frontend: React + Vite + TypeScript + Tailwind
Backend: FastAPI + Python
Auth: Firebase
Database: Turso
Hosting target: Render
Mail: Hostinger first, Gmail optional

## Zero-cost Render mode

The default `render.yaml` creates:
- free Static Site
- free Web Service

The API starts embedded lead + outreach workers while the free service is awake.
Pending jobs are durable in Turso. If Render sleeps, scheduled work can be delayed until
an incoming request wakes the service. While the app is open, the frontend periodically
checks `/health`, keeping the API responsive during active use.

`render-scaled.yaml` is the optional always-on multi-service architecture.

## Local development

Backend:

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m app.db.migrate
pytest -q
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install --include=optional
npm run check
npm run test
npm run build
npm run dev
```

Outreach worker locally:

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m app.outreach.worker
```

## Secrets

Never commit:
- backend/.env
- frontend/.env
- Firebase service-account JSON
- provider API keys
- Turso auth token
- Hostinger token
- `CREDENTIAL_ENCRYPTION_KEY`

Do not regenerate `CREDENTIAL_ENCRYPTION_KEY` after encrypted credentials exist.

## Future work

The planned core product is complete. Future work should be driven by real usage rather
than adding complexity by default. Potential optional integrations include CRM systems,
dedicated outbound platforms, billing/team workspaces and deeper analytics.
