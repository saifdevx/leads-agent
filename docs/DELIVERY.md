# Delivery Notes — Automated Lead Discovery

## Replace

Copy the complete package source over the existing repository and allow source files to be replaced.

## Keep locally

```text
.git/
backend/.env
backend/.venv/
frontend/.env
frontend/package-lock.json
frontend/node_modules/
```

## Important additions

Backend:

```text
backend/app/providers/
backend/app/jobs/
backend/app/leads/crawler.py
backend/app/leads/discovery.py
backend/app/api/providers.py
backend/app/api/jobs.py
backend/tests/test_provider_security.py
```

Frontend:

```text
frontend/src/pages/SettingsPage.tsx
```

## Important modified areas

```text
backend/app/api/leads.py
backend/app/core/config.py
backend/app/db/client.py
backend/app/leads/parser.py
backend/app/leads/repository.py
backend/app/leads/search_queries.py
backend/app/main.py
backend/requirements.txt
backend/.env.example

frontend/src/App.tsx
frontend/src/lib/api.ts
frontend/src/pages/FindLeadsPage.tsx
frontend/package.json

render.yaml
```

## Environment change

Add one stable server-side encryption key:

```env
CREDENTIAL_ENCRYPTION_KEY=
```

Generate it with:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Do not regenerate the key after credentials are stored.

## Database

No migration is required. The existing `provider_connections` and `jobs` tables are used.

## Rollback

See `ROLLBACK.md`. The source update can be rolled back without a database schema rollback.
