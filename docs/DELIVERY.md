# Delivery Notes — Free Lead Finder

## Replace

Copy the complete release source over the existing repository.

## Keep locally

```text
.git/
backend/.env
backend/.venv/
frontend/.env
frontend/package-lock.json
frontend/node_modules/
```

## New backend files

```text
backend/app/api/leads.py
backend/app/leads/__init__.py
backend/app/leads/parser.py
backend/app/leads/repository.py
backend/app/leads/schemas.py
backend/app/leads/search_queries.py
backend/tests/test_lead_parser.py
backend/tests/test_lead_repository.py
backend/tests/test_leads_api.py
```

## New frontend file

```text
frontend/src/pages/MyLeadsPage.tsx
```

## Important modified files

```text
backend/app/main.py
backend/app/db/dependencies.py
backend/app/core/config.py
frontend/src/App.tsx
frontend/src/lib/api.ts
frontend/src/lib/api.test.ts
frontend/src/pages/FindLeadsPage.tsx
frontend/src/components/Icon.tsx
frontend/src/components/Sidebar.tsx
```

No new package or database migration is required.
