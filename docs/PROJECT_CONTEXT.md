# Leads Agent — Current Project Context

Use this file as a handoff if development moves to a new chat.

## Product
A custom, simple B2B lead-generation web app. Normal user flow:

`Find Leads → My Leads → Outreach → Settings`

The user should enter a niche, location and lead target; the app should automate search, extraction, website research, deduplication, enrichment, exports and eventually safe outreach.

## Product principles
- Free-first, but BYOK paid providers are supported.
- Keep the UI simple even when the backend is sophisticated.
- Do not expose workflow/queue/model-router complexity to normal users.
- Deterministic extraction before AI where practical.
- AI must not invent contact data; evidence-grounded cleanup only.
- Deduplicate before paid enrichment and before outreach.
- Preserve working code and deliver complete ZIPs with tests/rollback docs.
- Do not put checkpoint/version labels in public Git history unless the user asks.

## Stack
- Frontend: React + Vite + TypeScript + Tailwind
- Backend: FastAPI + Python
- Auth: Firebase Authentication
- Database: Turso over SQL/HTTP
- Hosting target: Render
- BYOK secrets: encrypted server-side using `CREDENTIAL_ENCRYPTION_KEY`
- Source repo: https://github.com/saifdevx/leads-agent
- Typical local root: `D:\Leads-Agent\leads-agent`

## Working features before this update
- Firebase email/password + Google sign-in + password reset
- server-side Firebase ID-token verification
- Turso persistence
- Serper automated discovery
- Brave provider support
- Gemini + OpenAI BYOK AI cleanup
- public business-site crawler
- relevance filtering
- business-level duplicate merge
- manual Google-style fallback/import
- My Leads
- CSV/basic export

## This update adds
- Prospeo BYOK
- Apollo BYOK
- Smart enrichment waterfall (`Prospeo → Apollo`)
- role targeting for Owner / Founder / CEO / President / Managing Director
- verified email / decision-maker data merged into existing business leads
- bulk selected-lead enrichment
- optional automatic enrichment after discovery
- My Leads selection, filters and quality stats
- formatted Excel export with `Leads` + `Summary` sheets
- CSV export
- export current filtered view or selected leads

## Provider strategy
Discovery:
`Serper → Brave fallback/manual fallback`

Free research:
`search evidence → public website crawl → AI cleanup`

Paid enrichment:
`Prospeo → Apollo`

Do not spend enrichment credits on already-good/verified records.
Mobile/phone paid enrichment is intentionally disabled for now.

## Environment variable names
Frontend:
- `VITE_API_URL`
- Firebase VITE variables

Backend:
- `APP_NAME`
- `APP_VERSION`
- `APP_ENV`
- `CORS_ORIGINS`
- `LOG_LEVEL`
- Firebase variables
- `TURSO_DATABASE_URL`
- `TURSO_AUTH_TOKEN`
- `TURSO_TIMEOUT_SECONDS`
- `CREDENTIAL_ENCRYPTION_KEY`

Never overwrite real `.env` files or regenerate `CREDENTIAL_ENCRYPTION_KEY` after credentials have been saved.

## Design direction
Premium but restrained B2B SaaS.
- Primary Purple `#7B61FF`
- Secondary `#9D84FF`
- Light Purple `#B39CFF`
- Lime `#BCE953` sparingly
- Ink `#14151C`
- Slate `#4B4F5E`
- Lavender `#E8EAF3`
- White `#FFFFFF`
- Manrope headings, Inter body/UI
- no glassmorphism/excessive gradients/glows/giant radii

## Update/install rules
When copying a new release over the repo, preserve:
- `.git/`
- `backend/.env`
- `backend/.venv/`
- `frontend/.env`
- `frontend/package-lock.json`
- `frontend/node_modules/`

Never commit secrets.

## Validation commands
Backend:
```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
python -m app.db.migrate
uvicorn app.main:app --reload --port 8000
```

Frontend:
```powershell
cd D:\Leads-Agent\leads-agent\frontend
npm install --include=optional
npm run check
npm run test
npm run build
npm run dev
```

## Recommended test for this update
1. Connect Prospeo and/or Apollo under Settings.
2. Open My Leads and filter to leads with missing/unverified emails.
3. Select only 5–10 real businesses with domains for the first paid test.
4. Click Enrich; leave Smart mode on.
5. Verify name, role, verified email and LinkedIn improvements.
6. Export filtered verified-email view as XLSX and CSV.
7. Open XLSX and verify `Leads` and `Summary` sheets.
8. Once manual paid enrichment is validated, test a new 25-lead discovery with `Auto-enrich contacts` enabled.

## Next major build after this passes
Combine the first safe outreach MVP:
- user-defined templates
- Gmail OAuth sender connection
- campaign creation
- preview + approval
- queue / sending windows / daily limits
- duplicate-send protection
- suppression / unsubscribe handling
- basic campaign status

Follow-ups and reply classification should come after the first outbound flow is stable.
