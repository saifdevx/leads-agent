# Lead Platform v0.3.0

Checkpoint 3 adds the persistent Turso database foundation on top of the stable Firebase-authenticated v0.2.0 release.

## What works in this release

- Everything from v0.2.0 remains intact
- Turso Cloud connection through SQL over HTTP
- Versioned database migrations
- Minimal initial schema: users, lead lists, leads, provider connections, jobs
- Firebase users automatically synced into Turso after server-side token verification
- Database configuration/unavailable/query errors return safe API responses
- Database unit tests use mocked HTTP and do not require a paid/live database
- Lead search remains intentionally disabled

## Why SQL over HTTP

The backend talks to Turso over its documented HTTP protocol using the existing `httpx` dependency. This avoids a native libSQL extension and keeps local Windows/Python 3.14 setup predictable.

## Updating from v0.2.0

Your v0.2.0 should already be committed and tagged. Copy the complete v0.3.0 source over the existing repository and allow source files to be replaced.

Keep these private/local items:

```text
.git/
backend/.env
backend/.venv/
frontend/.env
frontend/package-lock.json
frontend/node_modules/
```

Do not replace or commit the real `.env` files.

## 1. Frontend

There are no new frontend packages in this checkpoint. After copying:

```powershell
cd D:\Leads-Agent\leads-agent\frontend
npm install --include=optional
npm run check
npm run test
npm run build
```

## 2. Backend

There are no new Python package dependencies in this checkpoint.

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```

## 3. Configure Turso

Follow `docs/TURSO_SETUP.md`.

Your existing `backend/.env` keeps its Firebase values and adds:

```env
APP_VERSION=0.3.0
TURSO_DATABASE_URL=turso://...
TURSO_AUTH_TOKEN=...
TURSO_TIMEOUT_SECONDS=10
```

## 4. Run the migration

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
python -m app.db.migrate
```

First run should apply `001_initial`; the second run should report that the schema is already up to date.

## 5. Run locally

Backend:

```powershell
uvicorn app.main:app --reload --port 8000
```

Frontend in another terminal:

```powershell
cd D:\Leads-Agent\leads-agent\frontend
npm run dev
```

Open `http://localhost:5173` and sign in.

## 6. What happens on sign-in now

```text
Firebase login
    ↓
Frontend gets Firebase ID token
    ↓
FastAPI verifies token
    ↓
FastAPI upserts the user into Turso
    ↓
Protected app opens
```

The frontend auth response has not changed, so this is an additive backend capability rather than a UI rewrite.

## 7. Acceptance tests

Use `docs/TEST_CHECKLIST.md` before accepting the checkpoint.

Expected automated suites after copying/configuring:

```text
Frontend: 6 tests
Backend: 12 tests
```

The exact warning count may vary with installed dependency versions; warnings are not failures.

## 8. Git after acceptance

Only after all tests and live Turso sync pass:

```powershell
cd D:\Leads-Agent\leads-agent
git status
git add .
git commit -m "feat: add Turso database foundation v0.3.0"
git push origin main
git tag -a v0.3.0 -m "Checkpoint 3 Turso database foundation"
git push origin v0.3.0
```

## Rollback

See `docs/ROLLBACK.md`. Git tag `v0.2.0` remains the trusted code rollback point. The initial Turso migration is additive and does not modify Firebase.
