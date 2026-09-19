# Test Checklist

## Existing regression

Frontend:

```powershell
npm run check
npm run test
npm run build
```

Backend:

```powershell
pytest -q
python -m app.db.migrate
```

Expected backend regression in this package: **24 tests passed** (dependency deprecation warnings may still appear).

The migration should report that the database is already up to date.

## BYOK security

- Settings loads without exposing any plaintext stored key.
- Connect Serper or Brave with a valid key.
- The UI shows only a masked key hint after saving.
- Refresh the browser; provider remains connected.
- Disconnect the provider; it shows disconnected.
- Reconnect it successfully.
- Confirm `backend/.env`, provider API keys and the Firebase Admin credential are not visible in Git status.

## Automated discovery

Start small:

```text
Niche: Solar panel installers
Location: Texas, USA
Leads: 25
```

- Click Find Leads.
- Search starts without opening Google manually.
- Smart mode uses Serper when connected; Brave is the fallback/default alternative when Serper is unavailable.
- Progress updates automatically.
- Job reaches `complete` or returns a clear provider error.
- At least some useful leads appear in My Leads when the provider returns relevant results.
- Search stops at/before the configured search-call budget.
- Duplicate records are not repeatedly inserted into the same list.

## AI extraction

Test once without AI and once with Gemini/OpenAI connected.

- Without AI: deterministic extraction still produces results.
- With AI: obvious directories/articles/jobs should be filtered more aggressively.
- AI-returned email, phone and URL fields are post-validated against search evidence; unsupported values are discarded.
- AI must not fabricate email addresses that are absent from search/website evidence.

## Website crawler

Use several discovered company websites.

- Public contact emails/phones/social links may be added.
- Private/local network URLs are rejected by crawler safety checks.
- Crawler failure for one website does not stop the whole search.

## Manual fallback

- Switch to Manual fallback.
- Generate queries.
- Paste sample search text.
- Extract & save still works.

## My Leads

- Lead-list filter works.
- Text search works.
- Website/social links open correctly.
- Sources show Serper/Brave/AI/manual as appropriate.
