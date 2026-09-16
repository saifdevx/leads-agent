# Delivery — v0.2.0

## PURPOSE

Add secure Firebase Authentication without changing the simplified lead-generation product flow.

## ADD NEW

```text
backend/app/auth/__init__.py
backend/app/auth/schemas.py
backend/app/auth/firebase.py
backend/app/auth/dependencies.py
backend/app/api/auth.py
backend/tests/test_auth.py

frontend/src/auth/AuthContext.tsx
frontend/src/auth/errors.ts
frontend/src/auth/errors.test.ts
frontend/src/lib/firebase.ts
frontend/src/pages/AuthPage.tsx
frontend/src/pages/AuthSetupPage.tsx
frontend/src/pages/AuthLoadingPage.tsx
frontend/src/pages/AuthVerificationErrorPage.tsx

docs/FIREBASE_SETUP.md
```

## REPLACE / UPDATE

```text
.gitignore
README.md
CHANGELOG.md
RELEASE_MANIFEST.txt
render.yaml

backend/.env.example
backend/requirements.txt
backend/app/main.py
backend/app/core/config.py

frontend/.env.example
frontend/package.json
frontend/src/main.tsx
frontend/src/App.tsx
frontend/src/lib/api.ts
frontend/src/lib/api.test.ts
frontend/src/components/PageShell.tsx
frontend/src/components/Sidebar.tsx
frontend/src/components/Icon.tsx
frontend/src/pages/FindLeadsPage.tsx

docs/DELIVERY.md
docs/ROLLBACK.md
docs/TEST_CHECKLIST.md
docs/VERSION_HANDOFF.md
```

## KEEP PRIVATE / DO NOT REPLACE WITH EXAMPLES

```text
.git/
backend/.env
backend/.venv/
frontend/.env
```

Update real `.env` values manually after copying the new `.env.example` files.

## IMPORTANT

Never commit Firebase Admin JSON credentials.
