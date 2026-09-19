# Project Handoff — Discovery Quality & Reliability

## Current working foundation
- React/Vite/TypeScript frontend
- FastAPI backend
- Firebase Authentication
- Turso SQL-over-HTTP persistence
- BYOK credential encryption
- Serper + Brave automated search
- Gemini + OpenAI optional AI extraction
- public website crawling
- My Leads + export
- manual search fallback

## This update changes
- provider key/log safety
- AI provider validation/fallback
- Turso transient retry behavior
- frontend job-poll resilience
- phone parsing
- location/niche/result filtering
- business-name extraction
- duplicate business merging
- adaptive search/crawl budgets

## No schema migration
Existing Turso data is preserved. No migration is required.

## Do not change during rollout
- Firebase service-account credential
- Turso database/token
- `CREDENTIAL_ENCRYPTION_KEY`
- real `.env` files

## Security note
The prior Gemini key was visible in historical local logs because the old implementation placed the key in the request URL. Rotate it before reconnecting Gemini. This update moves authentication to the `x-goog-api-key` header and suppresses third-party HTTP request INFO logs.

## Next product decision
Repeat the Pressure washing / Texas / 25-lead benchmark. Only after lead quality is materially cleaner should the project add Prospeo/Apollo enrichment. Outreach remains later.
