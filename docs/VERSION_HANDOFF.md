# Project Handoff — Enrichment + Export Upgrade

## Current working foundation
- React/Vite/TypeScript frontend
- FastAPI backend
- Firebase Authentication
- Turso SQL-over-HTTP persistence
- encrypted BYOK provider credentials
- Serper + Brave automated discovery
- Gemini + OpenAI optional AI extraction
- public website crawling
- quality filtering + business-level dedupe/merge
- My Leads database
- manual search fallback

## This update adds
- Prospeo BYOK connection/validation
- Apollo BYOK connection/validation
- Smart enrichment waterfall: Prospeo → Apollo
- decision-maker search by company domain and target roles
- verified-email/contact enrichment without mobile/phone-credit usage
- bulk selected-lead enrichment
- optional automatic post-discovery enrichment
- stronger My Leads filtering/selection/stats
- filtered or selected-lead export
- formatted Excel (.xlsx) export
- CSV export
- Excel Leads + Summary worksheets

## No schema migration
Existing Turso data is preserved. Run the migration command only as a safety check; it should report that the schema is already up to date.

## New backend dependency
- `XlsxWriter==3.2.9`

## Do not change during rollout
- Firebase service-account credential
- Turso database/token
- `CREDENTIAL_ENCRYPTION_KEY`
- real `.env` files

## Recommended rollout test
1. Connect Prospeo and/or Apollo in Settings.
2. Pick 5–10 real discovered businesses with domains.
3. Run Smart enrichment.
4. Confirm decision-maker name/title/email/LinkedIn fields improve without duplicate rows.
5. Filter to verified emails.
6. Export Excel and CSV.
7. Open the XLSX and verify Leads + Summary worksheets.
8. Only after the manual enrichment test works, enable `Auto-enrich contacts` for a small 25-lead search.

## Next product step
After this build passes locally, move to the first safe outreach MVP in one combined delivery:
- user-defined templates,
- Gmail OAuth sender connection,
- campaign creation,
- preview/approval,
- queue + daily limits/sending windows,
- suppression/unsubscribe safety,
- basic campaign status.

Follow-ups and reply classification can come after the first outbound flow is stable.
