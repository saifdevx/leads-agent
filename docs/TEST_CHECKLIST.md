# Test Checklist — v0.3.0

Do not move to the lead-discovery checkpoint until this list passes.

## A. Preserve v0.2.0

- [ ] Git tag `v0.2.0` exists remotely.
- [ ] `backend/.env`, `frontend/.env`, Firebase Admin JSON, `.venv`, and `node_modules` are not tracked.

## B. Automated frontend checks

```powershell
cd D:\Leads-Agent\leads-agent\frontend
npm install --include=optional
npm run check
npm run test
npm run build
```

- [ ] TypeScript check passes.
- [ ] 6 frontend tests pass.
- [ ] Production build succeeds.

## C. Automated backend checks

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```

- [ ] 12 backend tests pass.
- [ ] Existing Firebase tests still pass.
- [ ] Turso HTTP client tests pass.
- [ ] Migration test passes.
- [ ] User repository sync test passes.

## D. Turso configuration

- [ ] Turso Database created.
- [ ] `TURSO_DATABASE_URL` added only to backend `.env`.
- [ ] `TURSO_AUTH_TOKEN` added only to backend `.env`.
- [ ] Token is not visible in Git status/diff.

## E. Migration

```powershell
python -m app.db.migrate
```

- [ ] First run applies `001_initial`.
- [ ] Second run reports schema is already up to date.
- [ ] Turso shows `schema_migrations`, `users`, `lead_lists`, `leads`, `provider_connections`, and `jobs`.

## F. Runtime

```powershell
uvicorn app.main:app --reload --port 8000
```

- [ ] `/health` returns HTTP 200 and version `0.3.0`.
- [ ] `/docs` loads.
- [ ] Logged-out `/api/v1/auth/me` returns 401.

## G. Live user sync

- [ ] Start frontend and sign in with an existing Firebase user.
- [ ] Protected app opens normally.
- [ ] Turso `users` table contains that Firebase UID.
- [ ] Email/display name/provider match the Firebase identity.
- [ ] Sign out and sign in again.
- [ ] The same row is updated; a duplicate user row is not created.

## H. Failure behavior

Temporarily use an invalid Turso token, restart backend, and try authenticated verification.

- [ ] Protected app does not pretend verification succeeded.
- [ ] Backend returns a safe database configuration error.
- [ ] Raw token and SQL are not returned to the browser.

Restore the correct token afterwards.

## I. Regression

- [ ] Email/password login still works.
- [ ] Google login still works.
- [ ] Logout still works.
- [ ] Password reset still works.
- [ ] Sidebar remains Find Leads / My Leads / Outreach / Settings.
- [ ] Find Leads remains intentionally non-functional.

## Acceptance

Checkpoint 3 is accepted only after automated tests and live Turso user sync pass.
