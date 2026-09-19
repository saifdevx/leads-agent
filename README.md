# Lead Platform

A free-first/BYOK lead discovery, enrichment, export, and outreach web application.

## Current product flow

`Find Leads → Enrich → Review/Export → Select Leads → Outreach → Preview → Approve → Queue → Hostinger/Gmail`

## Stack

- React + Vite + TypeScript + Tailwind
- FastAPI
- Firebase Authentication
- Turso SQL-over-HTTP
- Serper / Brave discovery adapters
- Gemini / OpenAI AI adapters
- Prospeo / Apollo enrichment adapters
- Hostinger Agentic Mail API sending
- Optional Gmail OAuth + Gmail API sending
- XlsxWriter exports

## Local startup

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

### Outreach worker

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m app.outreach.worker
```

See `docs/HOSTINGER_SETUP.md` for the recommended Hostinger sender setup. Gmail remains optional; its setup is documented in `docs/OUTREACH_SETUP.md`.

## Security

Do not commit `.env`, Firebase service-account files, Turso tokens, provider API keys, Google OAuth client secrets, or `CREDENTIAL_ENCRYPTION_KEY`.

User provider keys, Hostinger tokens, and Gmail tokens are stored encrypted using the existing credential-encryption key.
