# Delivery — v0.3.0

## PURPOSE

Add Turso persistence without expanding the user-facing product or starting lead discovery early.

## ADD NEW

```text
backend/app/db/__init__.py
backend/app/db/client.py
backend/app/db/dependencies.py
backend/app/db/user_repository.py
backend/app/db/migrate.py
backend/migrations/001_initial.sql
backend/tests/test_db_client.py
backend/tests/test_user_repository.py
backend/tests/test_migrations.py
docs/TURSO_SETUP.md
```

## REPLACE / UPDATE

```text
README.md
CHANGELOG.md
RELEASE_MANIFEST.txt
render.yaml

backend/.env.example
backend/app/main.py
backend/app/core/config.py
backend/app/auth/dependencies.py
backend/app/api/auth.py
backend/tests/test_auth.py

frontend/package.json
frontend/src/components/Sidebar.tsx
frontend/src/pages/FindLeadsPage.tsx
frontend/src/App.tsx
frontend/src/lib/api.test.ts
frontend/src/pages/AuthSetupPage.tsx

docs/FIREBASE_SETUP.md
docs/DELIVERY.md
docs/ROLLBACK.md
docs/TEST_CHECKLIST.md
docs/VERSION_HANDOFF.md
```

## KEEP PRIVATE / LOCAL

```text
.git/
backend/.env
backend/.venv/
frontend/.env
frontend/package-lock.json
frontend/node_modules/
D:/Leads-Agent/secrets/firebase-admin.json
```

Update the real `backend/.env` manually with the Turso values.

## NO NEW PACKAGE DEPENDENCY

Checkpoint 3 deliberately reuses `httpx` for Turso SQL over HTTP. This avoids adding a native database driver to the local Windows environment.
