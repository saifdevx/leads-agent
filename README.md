# Lead Platform — Enrichment + Better Exports

This build combines multiple next steps so the product reaches an outreach-ready lead workflow faster.

## What this update adds

### 1. Prospeo BYOK
Users can connect a Prospeo API key from **Settings**. The backend validates the key, encrypts it, and never returns it in plaintext.

Prospeo is used for:
- decision-maker discovery when a company/domain is known,
- verified work-email enrichment,
- person/job-title/company enrichment.

Phone/mobile enrichment is intentionally disabled because it is much more expensive than email enrichment.

### 2. Apollo BYOK
Users can connect an Apollo API key from **Settings**.

Apollo is used for:
- owner/founder/CEO/decision-maker discovery by company domain,
- person enrichment,
- email enrichment when available under the user's Apollo plan.

### 3. Smart enrichment waterfall
From **My Leads**, select up to 100 leads and click **Enrich**.

Default Smart mode:

```text
Prospeo
  ↓ if no usable contact
Apollo
  ↓
merge better contact data into the existing lead
```

The enrichment job prioritizes:
- owner/founder/CEO/President/Managing Director,
- verified work email,
- full contact name,
- job title,
- LinkedIn URL,
- location details.

Existing verified leads are skipped so credits are not wasted.

### 4. Better My Leads workspace
My Leads now includes:
- row selection,
- select all visible,
- contact name + role,
- score badges,
- email verification badges,
- email-state filter,
- minimum-score filter,
- visible-lead stats,
- bulk enrichment.

### 5. Better exports
Exports can now be generated as:
- **Excel (.xlsx)**
- **CSV (.csv)**

Export either:
- currently filtered leads, or
- selected leads.

Excel exports contain:
- a formatted `Leads` worksheet,
- a `Summary` worksheet,
- frozen header row,
- filters,
- readable column widths,
- clickable URLs,
- verified-email highlighting,
- score conditional formatting.

The export includes company/contact/email/phone/social/source/score/list fields so it is ready for CRM or outreach workflows.

## Updating the existing project

First push your current working code to GitHub.

Then copy this package over your existing repository and allow source files to be replaced.

Keep these local/private items:

```text
.git/
backend/.env
backend/.venv/
frontend/.env
frontend/package-lock.json
frontend/node_modules/
```

Do not regenerate `CREDENTIAL_ENCRYPTION_KEY`.

## Backend dependency update

This build adds:

```text
XlsxWriter==3.2.9
```

Install backend requirements again:

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

No database migration is required.

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

Expected migration output:

```text
Database schema is already up to date.
```

## Connect Prospeo

1. Open **Settings**.
2. Find **Prospeo**.
3. Click **Connect**.
4. Paste your Prospeo API key.
5. The backend validates the key using Prospeo account information before storing it.

## Connect Apollo

1. Open **Settings**.
2. Find **Apollo**.
3. Click **Connect**.
4. Paste an Apollo API key with access to the people-search/person-enrichment endpoints you want to use.
5. The backend validates the key with Apollo's auth-health endpoint.

Apollo plan/API scopes can vary. A valid API key can still receive a provider-level error later if that Apollo plan or scoped key does not include a particular people endpoint.

## Recommended test

Use an existing discovery list such as:

```text
Pressure washing — Texas, USA
```

Then:

1. Open **My Leads**.
2. Filter to `Missing email` or `Unverified email` leads.
3. Select 5–10 leads with real business domains.
4. Click **Enrich**.
5. Leave provider on **Smart — Prospeo then Apollo**.
6. Leave target roles as:

```text
Owner, Founder, CEO, President, Managing Director
```

7. Start enrichment.
8. Wait for the completion notice.
9. Refresh the list and check:
   - decision-maker names,
   - job titles,
   - verified email badges,
   - LinkedIn URLs,
   - source now including `prospeo` and/or `apollo`.

Then test exports:

1. Filter to `Verified email`.
2. Choose `Excel (.xlsx)`.
3. Click **Export view**.
4. Open the workbook and verify both `Leads` and `Summary` worksheets.
5. Repeat with CSV.

## Cost-control behavior

The app deliberately does not enrich mobile/phone data through Prospeo/Apollo in this build.

The intended order remains:

```text
Serper / Brave discovery
→ public website crawl
→ AI cleanup
→ dedupe
→ Prospeo/Apollo only for the good candidates
```

That prevents paid credits from being spent on noisy search results.

## Next combined step after this passes

Once enrichment + exports are stable, the fastest path to a complete usable MVP is to combine:

- email templates,
- Gmail OAuth sender connection,
- campaign creation,
- queue + daily limits,
- preview/approval before send,
- unsubscribe/suppression safety,
- basic campaign status.

Advanced follow-ups/reply classification can follow after the first safe outbound flow works.
