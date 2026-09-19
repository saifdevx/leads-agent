# Lead Platform

A free-first/BYOK lead-generation web application built with React/Vite, FastAPI, Firebase Authentication and Turso.

## What this build adds

The main Find Leads workflow is now automated when a supported search provider is connected.

A user can enter:

```text
Niche: Solar panel installers
Location: Texas, USA
Leads wanted: 100
```

and click **Find Leads**. The backend then:

1. Generates high-signal prospecting queries based on the proven Google workflow.
2. Searches through the selected provider. Smart mode prefers Serper for Google-style results and falls back to Brave when Serper is not connected.
3. Extracts contact/business information from search-result evidence.
4. Optionally uses Gemini or OpenAI structured output to improve extraction and relevance filtering.
5. Checks public company websites for missing email/phone/social contact information.
6. Deduplicates results.
7. Grounds AI-returned contact fields back to actual search evidence, then saves useful leads to Turso in batches.
8. Exposes live progress in the UI.

The existing manual copy/paste workflow remains available as a fallback.

## BYOK integrations

Settings now supports encrypted user-owned API keys for:

- **Serper** — Google-style automated search. Recommended primary discovery source.
- **Brave Search** — independent web-search coverage.
- **Gemini** — optional AI cleanup / structured extraction.
- **OpenAI** — optional AI cleanup / structured extraction.

Plaintext API keys are validated by the backend and encrypted before they are stored in Turso. They are never returned to the browser after saving.

## Important design decision

Google Places is not used as a persistent lead-data source in this build. Google Maps Platform places restrictions on storing/caching Places API content. We can revisit a compliant Places integration later if it materially improves the product.

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

## New backend environment variable

Generate one Fernet encryption key and keep it stable for the lifetime of the stored provider credentials:

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the generated value into `backend/.env`:

```env
APP_VERSION=0.5.0
CREDENTIAL_ENCRYPTION_KEY=PASTE_GENERATED_VALUE_HERE
```

Keep your existing Firebase and Turso values unchanged.

**Do not regenerate this key after provider credentials have been saved.** Existing encrypted keys would no longer be decryptable.

## Frontend setup

No new frontend package is required.

```powershell
cd D:\Leads-Agent\leads-agent\frontend
npm install --include=optional
npm run check
npm run test
npm run build
npm run dev
```

## Backend setup

This build explicitly adds `cryptography` as a direct dependency for BYOK credential encryption. It may already exist through Firebase, but install from the requirements file so the dependency is intentional and reproducible.

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
python -m app.db.migrate
uvicorn app.main:app --reload --port 8000
```

There is no new database migration because `provider_connections` and `jobs` already exist in the current schema.

## First automated-search test

1. Sign in.
2. Open **Settings**.
3. Connect **Serper** or **Brave Search**.
4. Optionally connect Gemini or OpenAI.
5. Return to **Find Leads**.
6. Enter a niche/location and request 25 leads for the first test.
7. Click **Find Leads**.
8. Watch progress until complete.
9. Open **My Leads** and review quality/source data.

For the first real quality test, connect **Serper + Gemini** (or OpenAI). Serper most closely automates the prior Google-search workflow; AI improves structured extraction and relevance filtering without being allowed to invent missing contact details.

## Search behavior and cost control

The app uses a bounded search budget (up to 30 search API calls per run in this build) and stops when either:

- the requested number of useful unique leads is reached, or
- the search-call budget is reached.

The automated workflow does not directly scrape Google HTML, Instagram, LinkedIn or Facebook. It uses supported search APIs to retrieve indexed public search results, then optionally visits public company websites.

## AI behavior

Gemini/OpenAI are optional. Search still works without them using deterministic extraction.

When enabled, AI is used to:

- associate search snippets with the correct business,
- reject obviously irrelevant pages/directories/jobs/articles,
- extract structured fields without inventing missing contact details.

The AI prompt explicitly requires evidence-grounded extraction; missing data remains missing.

## Next provider layer

After automated discovery quality is validated, the next provider layer should add verified enrichment/decision-maker sources such as Prospeo and Apollo. That layer should only spend credits on leads that still need verified contact data.

See `docs/TEST_CHECKLIST.md` for acceptance tests and `docs/ROLLBACK.md` for rollback guidance.
