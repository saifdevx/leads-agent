# Delivery

## Purpose

Add the second final product bundle: **Admin + production deployment + performance**.

## Replace

Replace normal tracked source files with the contents of this bundle.

## Keep locally

- `.git/`
- `backend/.env`
- `backend/.venv/`
- `frontend/.env`
- `frontend/package-lock.json`
- `frontend/node_modules/`
- Firebase private JSON
- all real secrets

## Additions

- Admin backend/API/UI
- Migration 004
- durable lead worker
- worker heartbeats
- live Hostinger webhook enablement UI/status
- Render Blueprint
- production deployment guide
- performance snapshot endpoints
- connection pooling / frontend request dedupe

## Environment additions

```env
ADMIN_EMAILS=
BACKGROUND_JOBS_MODE=inline
WORKER_POLL_SECONDS=3
WORKER_LEASE_SECONDS=300
USER_ACCESS_CACHE_SECONDS=30
PUBLIC_API_URL=
```

`PUBLIC_API_URL` remains blank locally.

## Migration

```powershell
python -m app.db.migrate
```

Expected new migration: `004_admin_operations`.

## Validation

Follow `TEST_CHECKLIST.md`.
