# Lead Platform — Discovery Quality & Reliability Update

This update improves the existing automated discovery build rather than adding another major feature. The goal is to make the current **Niche + Location + Lead target → Find Leads** workflow more accurate and resilient before spending credits on Prospeo/Apollo enrichment.

## Important security action first

A Gemini API key appeared in earlier local HTTP logs. Treat that key as exposed.

Before using Gemini again:

1. Revoke/regenerate the old Gemini key in Google AI Studio / Google Cloud.
2. Do not paste the replacement key into chat or source files.
3. After installing this update, use **Settings → Gemini → Replace key**.

This build sends the Gemini key through the `x-goog-api-key` header and suppresses third-party HTTP request INFO logs so provider keys are not printed in URLs.

## What changed

- Better relevance/location filtering.
- False social IDs and dates are no longer accepted as phone numbers.
- Obvious template/demo/directory/job/course results are filtered out.
- Website metadata/JSON-LD improves business names.
- Duplicate businesses merge contact data rather than creating duplicate rows.
- Gemini validation now performs an actual generation request.
- Gemini default model for new connections is `gemini-3.5-flash-lite`.
- OpenAI validation also checks the generation path used by discovery.
- Smart AI mode tries Gemini, then OpenAI when both are connected, then deterministic extraction.
- Temporary Turso failures retry automatically.
- Temporary job-status 503 responses no longer stop frontend polling.
- Search and crawl budgets adapt to low-yield runs while staying bounded.

No database migration and no new package are required.

## Updating the existing project

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

## Backend environment

Keep all current Firebase, Turso and credential-encryption values.

Recommended change in `backend/.env`:

```env
TURSO_TIMEOUT_SECONDS=15
```

Do **not** regenerate `CREDENTIAL_ENCRYPTION_KEY`.

## Frontend checks

```powershell
cd D:\Leads-Agent\leads-agent\frontend
npm install --include=optional
npm run check
npm run test
npm run build
npm run dev
```

## Backend checks

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
python -m app.db.migrate
uvicorn app.main:app --reload --port 8000
```

Expected migration result:

```text
Database schema is already up to date.
```

## Reconnect Gemini

After rotating the leaked key:

1. Open **Settings**.
2. Choose **Gemini → Replace key**.
3. Leave the suggested model `gemini-3.5-flash-lite` unless you intentionally want another compatible model.
4. Connect.

The backend now tests a real `generateContent` request before accepting the key. A key that can list models but cannot generate will no longer appear healthy.

If Gemini still cannot generate, leave AI cleanup on **Automatic** if OpenAI is connected, or switch AI cleanup **Off** temporarily. Search and deterministic extraction still work.

## Recommended repeat test

Use the same benchmark as the previous run:

```text
Business / niche: Pressure washing
Location: Texas, USA
Leads wanted: 25
Search source: Smart / automatic
AI cleanup: Automatic
Check company websites: On
```

Review the resulting list for:

- actual Texas relevance,
- real company names,
- plausible phone numbers,
- email count,
- duplicate businesses,
- demo/template sites,
- total search calls and runtime.

Examples that should now be filtered/fixed:

- `2024-05-15` must not become a phone number.
- long Facebook numeric IDs must not become phone numbers.
- an explicit `Central Florida` result should not be saved for a Texas search.
- `themereserve.com` demo/template results should not count as leads.
- two rows from the same business domain should merge contact data into one business.

## Next step after this quality test

Do not add outreach yet. If this benchmark is materially cleaner, the next provider layer should be:

1. **Prospeo** — verify/fill missing emails.
2. **Apollo** — identify owners/founders/decision makers where needed.

Paid enrichment should be applied only after free/public discovery and deduplication, so credits are spent on good candidate businesses rather than noisy search results.
