# Delivery

## Replace
Copy all source files in this package over the existing repository.

## Keep locally
- `.git/`
- `backend/.env`
- `backend/.venv/`
- `frontend/.env`
- `frontend/package-lock.json`
- `frontend/node_modules/`

## Environment
Recommended only:

```env
TURSO_TIMEOUT_SECONDS=15
```

Do not regenerate `CREDENTIAL_ENCRYPTION_KEY`.

## Install / test
See the root `README.md` and `docs/TEST_CHECKLIST.md`.

## Rollback
No database schema change exists. Restore the previous Git commit and preserve local secrets.
