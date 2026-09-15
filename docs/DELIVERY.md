# Delivery Notes — v0.1.0

## VERSION
`0.1.0`

## PURPOSE
Create the smallest working foundation for the simplified lead-generation product before authentication, database, providers, AI, or email automation are introduced.

## ADD
Everything in this ZIP is new for Checkpoint 1.

## REPLACE
Nothing. This is the first code release.

## KEEP
Keep the approved Checkpoint 0 product decisions and the simplified product flow:

1. Find Leads
2. Review Leads
3. Contact Leads

## BACKUP
Keep this ZIP unchanged and commit/tag it as `v0.1.0` before installing Checkpoint 2.

## DEPENDENCIES
Frontend dependencies are pinned in `frontend/package.json`.
Backend dependencies are pinned in `backend/requirements.txt`.

## ENVIRONMENT CHANGES
Create local `.env` files from the included `.env.example` templates. Do not commit real `.env` files.

## DATABASE CHANGES
None. Turso begins in a later checkpoint.

## INSTALL
Follow the root `README.md` exactly.

## TEST
Run:

```bash
cd backend
pytest -q
```

Then:

```bash
cd frontend
npm run check
npm run test
npm run build
```

Also complete `docs/TEST_CHECKLIST.md`.

## EXPECTED RESULT
- Backend `/health` returns HTTP 200.
- Frontend loads the simplified product shell.
- Top-right API status changes to `API connected` when backend is running.
- Four navigation items work.
- No screen pretends unfinished lead-search functionality exists.

## KNOWN LIMITATIONS
- No authentication yet.
- No database yet.
- No live lead search yet.
- No AI or provider connections yet.
- No email sending yet.

## ROLLBACK
See `docs/ROLLBACK.md`.
