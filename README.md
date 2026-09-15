# Lead Platform v0.1.0 — Checkpoint 1

This is the working foundation for the simplified lead-generation web app.

## What this checkpoint includes

- React + Vite + TypeScript frontend
- Tailwind CSS design system using the locked purple / ink / lime palette
- Simplified navigation: **Find Leads / My Leads / Outreach / Settings**
- Responsive sidebar and mobile navigation
- FastAPI backend
- `/health` and `/api/v1/health` endpoints
- Frontend-to-backend health integration
- Request IDs and structured API errors
- Basic JSON logging
- Frontend and backend tests
- Render Blueprint baseline

## What this checkpoint intentionally does NOT include

- Firebase authentication
- Turso database
- Live lead discovery
- Gemini / OpenAI
- Apollo / Prospeo / other enrichment providers
- Gmail sending

Those are added one checkpoint at a time so failures remain easy to isolate and roll back.

## Requirements

- Node.js **20.19+ or 22.12+** (Node 22 recommended)
- Python **3.12+** (the included `.python-version` uses 3.13.5)
- npm

## Local setup

### 1. Backend

```bash
cd backend
python -m venv .venv
```

Activate it:

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create local environment config:

```bash
cp .env.example .env
```

Windows users can copy the file manually if `cp` is unavailable.

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

Expected health URL:

`http://localhost:8000/health`

### 2. Frontend

Open a second terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open:

`http://localhost:5173`

The top-right status should change from **Connecting** to **API connected**.

## Tests

Backend:

```bash
cd backend
pytest -q
```

Frontend:

```bash
cd frontend
npm run check
npm run test
npm run build
```

## Render deployment baseline

A root-level `render.yaml` is included.

Before deploying, set:

- frontend `VITE_API_URL` = the deployed backend URL
- backend `CORS_ORIGINS` = the deployed frontend URL

Do not place secrets in `render.yaml` or commit `.env` files.

## Product rule for this release

The visible product stays simple even as the backend grows:

1. Find Leads
2. Review Leads
3. Contact Leads

Technical provider, queue, retry and AI-routing details stay behind the scenes unless a user explicitly opens advanced settings.
