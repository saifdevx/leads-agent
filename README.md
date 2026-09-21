# Lead Platform

A custom lead-generation and outreach web app built around a simple workflow:

**Find leads → review/enrich/import/export → outreach → replies/follow-ups**

## Current capabilities

- Firebase authentication
- Turso application database
- Automated lead discovery via connected search providers
- Public website research
- Gemini/OpenAI BYOK cleanup
- Prospeo/Apollo BYOK enrichment
- Excel/CSV import and export
- Email templates
- Hostinger Mail sender
- Optional Gmail sender
- Campaign preview + explicit approval
- Persistent email queue + worker
- Quick Send
- Daily limits, configurable 20s+ interval, optional sending window
- Pause/resume/cancel/delete campaign controls
- Suppression list
- Multi-step follow-up sequences
- Reply Inbox + manual Hostinger reply sync for local development
- Stop-on-reply
- Interested / unsubscribe / out-of-office reply classification
- Campaign reply analytics and message-level retry controls
- Optimistic UI for common actions + short-lived frontend response cache
- Bulk lead deletion with instant UI feedback
- Subtle UI motion with reduced-motion support

## Local processes

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

Outreach worker:
```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m app.outreach.worker
```

See `docs/REPLIES_FOLLOWUPS_SETUP.md` for this bundle's update and test guide.
