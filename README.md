# Lead Platform

A custom lead-generation and outreach web app built around a simple workflow:

**Find leads → review/enrich/import/export → outreach → replies/follow-ups**

The interface stays simple while provider adapters, durable jobs, workers, caching and operational controls run behind it.

## Current capabilities

### Lead generation
- Firebase authentication
- Turso application database
- Automated discovery with Serper / Brave
- Public website research
- Gemini / OpenAI BYOK cleanup
- Prospeo / Apollo enrichment
- Excel / CSV import and export
- Deduplication, filtering and bulk actions

### Outreach
- Email templates
- Hostinger Agentic Mail sender
- Optional Gmail sender
- Quick Send
- Campaign preview + explicit approval
- Daily limits, 20s+ intervals and optional sending windows
- Pause / resume / cancel / delete
- Suppression list
- Multi-step follow-ups
- Reply inbox and reply classification
- Stop-on-reply
- Campaign analytics and failed-message retry
- Hostinger live reply webhook support after production deployment

### Operations / production
- Admin-only dashboard
- User suspension/reactivation
- Job inspection and retry
- Provider and worker health visibility
- Durable lead-discovery and enrichment worker
- Separate outreach worker
- Production Render Blueprint
- Worker heartbeats
- Admin audit logging
- User access-state cache
- Persistent Turso HTTP connection pooling
- Lead-page and Outreach-page snapshot APIs to reduce database round trips
- Frontend in-flight request deduplication and short-lived caching

## Local development

Backend:
```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Frontend:
```powershell
cd frontend
npm run dev
```

Outreach worker (required to actually send queued campaigns locally):
```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m app.outreach.worker
```

Lead worker is **not required locally** while `BACKGROUND_JOBS_MODE=inline`. Production uses a dedicated lead worker.

## Admin access

Add your own Firebase login email to the backend `.env`:

```env
ADMIN_EMAILS=you@example.com
```

Restart the backend and sign in again. The **Admin** navigation item will appear after `/api/v1/auth/me` returns the admin role.

## Production

See:
- `docs/PRODUCTION_DEPLOYMENT.md`
- `docs/PERFORMANCE.md`
- `docs/TEST_CHECKLIST.md`

Two deployment profiles are included: `render.yaml` (recommended, separate lead + outreach workers) and `render-low-cost.yaml` (early low-cost mode with discovery running inline in the API).
