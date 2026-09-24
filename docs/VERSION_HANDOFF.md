# Lead Gen — Handoff

## What works

Authentication, automated discovery, lead management, enrichment, imports/exports,
Hostinger outreach, templates, campaigns, follow-ups, replies, analytics, admin and
free Render deployment support are implemented.

## Architecture

- React/Vite frontend
- FastAPI backend
- Firebase auth
- Turso database
- Provider adapters
- Durable jobs
- Hostinger/Gmail sender adapters

## Background processing

Local default:
- `BACKGROUND_JOBS_MODE=inline`
- run `python -m app.outreach.worker` separately

Free Render default:
- `BACKGROUND_JOBS_MODE=embedded`
- `EMBEDDED_WORKERS=true`
- both durable workers run inside the API process while the service is awake

Scaled deployment:
- use `render-scaled.yaml`
- separate API, lead worker and outreach worker

## Preserve

- `.git/`
- real `.env` files
- local virtual environments
- `CREDENTIAL_ENCRYPTION_KEY`
- production data

## Final validation

Use `docs/FINAL_RELEASE_CHECKLIST.md` before deployment.
