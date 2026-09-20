# Lead Platform

A custom lead-generation and outreach web app built around a simple workflow:

**Find leads -> review/enrich/import/export -> outreach**

## Current capabilities

- Firebase authentication
- Turso application database
- Automated lead discovery via connected search providers
- Public website research
- Gemini/OpenAI BYOK cleanup
- Prospeo/Apollo BYOK enrichment
- Excel/CSV export
- Excel/CSV lead-sheet import
- Email templates
- Hostinger Mail sender
- Optional Gmail sender
- Campaign preview/approval
- Persistent email queue + worker
- Daily limits and configurable 20s+ send interval
- Optional sending-hour window
- Quick Send for one-off/testing email
- Pause/resume/cancel/delete campaign controls
- Suppression list

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

See `docs/PRODUCTIVITY_SETUP.md` for the latest update instructions.
