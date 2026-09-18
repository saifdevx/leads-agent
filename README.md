# Lead Platform

A free-first lead generation web app built with React/Vite, FastAPI, Firebase Authentication and Turso.

## Current capabilities

- Firebase email/password and Google authentication
- Server-side Firebase token verification
- Turso persistence
- Simple navigation: Find Leads, My Leads, Outreach, Settings
- Free lead-search plan generation
- Google-style query generation for websites and social profiles
- Manual paste/import of visible search-result text
- Contact extraction for public business emails, phone numbers, websites and social URLs
- In-list deduplication before saving
- Lead lists and a searchable My Leads table

Paid search, AI enrichment and email outreach are intentionally not enabled yet.

## Updating an existing local project

Copy this package over the existing repository and allow source files to be replaced.

Keep these local/private items:

```text
.git/
backend/.env
backend/.venv/
frontend/.env
frontend/package-lock.json
frontend/node_modules/
```

Do not replace or commit real `.env` files.

## Local environment update

Your existing Turso/Firebase settings stay the same. Only update the backend application version if you keep it in your real `.env`:

```env
APP_VERSION=0.4.0
```

No new Firebase, Turso or frontend environment variables are required.

## Frontend

No new npm dependency is required.

```powershell
cd D:\Leads-Agent\leads-agent\frontend
npm install --include=optional
npm run check
npm run test
npm run build
npm run dev
```

## Backend

No new Python dependency is required.

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload --port 8000
```

No new database migration is required for the free lead finder because the existing `lead_lists` and `leads` schema already supports it. Running the migration command is still safe:

```powershell
python -m app.db.migrate
```

It should report that the database schema is already up to date.

## Free lead workflow

1. Sign in.
2. Open **Find Leads**.
3. Enter niche, location and target lead count.
4. Click **Create free search plan**.
5. Open one of the generated Google searches.
6. Copy visible result text from relevant results/pages.
7. Paste the text into Lead Platform.
8. Click **Extract & save leads**.
9. Open **My Leads** to review saved contacts.

The parser is best-effort. It extracts public data that is present in the pasted text; it does not fabricate missing contact details.

## Important limitation

This release does not automatically scrape Google, Instagram, LinkedIn or Facebook. It generates useful queries and processes text the user chooses to paste. Automated search-provider integrations come later through supported APIs/adapters.

## Source control

After local tests and a real import test pass, commit normally using your preferred professional commit message. No Git tag or public checkpoint naming is required.

See `docs/TEST_CHECKLIST.md` for acceptance tests and `docs/ROLLBACK.md` for rollback guidance.
