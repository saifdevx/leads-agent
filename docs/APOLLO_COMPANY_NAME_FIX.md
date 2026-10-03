# Apollo discovery and company-name patch

Prepared 2026-10-03 for the user's uploaded `leads-agent-main.zip`.

## Read this before deployment

This is a targeted source patch, not a redesign or a new deployment. Use the changed-files ZIP with the checked installer for an existing project. The full-source ZIP is an alternative reference/fresh source copy; do not apply both.

**Verification is partial, not a production certification.** 157 backend tests passed in the available environment. All 25 frontend TS/TSX source files passed a syntax-transpile check, and 8 provider-selection smoke assertions passed. The full backend suite could not collect five Firebase-dependent modules because the SDK could not be installed. The actual frontend type check, Vitest run and production build could not run because dependencies could not be downloaded. Run all normal project checks below before deploying. See `PATCH_TEST_REPORT.md` for the exact commands, versions and exclusions.

The source ZIP identifies commit `2749a8e3d890a83ff4f56f3f497e052694c2825b`. It already includes smart-template alias/HTML support; the September 26 context still describes that patch as pending. This patch builds on the uploaded code, not on that older description. No live GitHub repository or deployed service was changed or used as the source of truth.

## 1. What changed

### Apollo on Find Leads

Previously, Apollo was classified only as an enrichment provider, while the search selector, request validation and discovery worker accepted only Serper/Brave. Adding a dropdown item alone would not have fixed the backend.

The patch adds **Apollo / Companies** in Advanced options and includes connected Apollo accounts in the Search connection card/readiness check. Provider state refreshes when Find Leads mounts and when the window regains focus. Failed connection refreshes have an explicit retry, rather than silently looking disconnected.

The saved, encrypted Apollo key is reused. There is no new key field, workflow service, database table or provider category migration. Apollo deliberately remains in its original enrichment category in Settings and is also recognized as discovery-capable.

Selection policy:

- Apollo is the only connected discovery source: **Smart / automatic** uses Apollo.
- Serper or Brave is also connected: automatic mode retains the existing web-source preference. Select **Apollo / Companies** explicitly to use Apollo.
- OpenAI/Gemini alone is not a search connection. Prospeo remains contact enrichment, not an invented search adapter.

Apollo company discovery uses `POST /api/v1/mixed_companies/search`, company keyword filters, headquarters location and bounded pagination. It maps real organization fields. It does not invent an email or verification state, and does not automatically call paid contact-unlock endpoints. Public website checking can find public contact information when enabled. Existing **Auto-enrich contacts** remains a separate user-controlled action.

Apollo's documentation checked on 2026-10-03 specifies one credit per organization-search page, up to 100 results per page, endpoint-specific key access and account eligibility requirements. This patch caps a job at at most 10 pages (often fewer). A key marked connected can still lack access to this particular endpoint. A 401/403/429 is surfaced as a failed job with the provider error; the patch does not silently disconnect an Apollo key that could still work for enrichment. Headquarters matching is not a search across all branch offices. Use an unambiguous location, such as `Manchester, United Kingdom` versus `Manchester, Connecticut, United States`.

Official endpoint documentation:

```text
https://docs.apollo.io/reference/organization-search
```

### Safer names in leads and new campaign messages

The old renderer accepted almost any non-empty `company_name`. This let social-post titles become email greetings, subjects and body text.

A shared validator now rejects obvious captions, truncation, post IDs, generic placeholders, HTML, sentence-style marketing copy and unusable emoji-only values. Decorative emojis are removed from otherwise plausible names. Real punctuation, accents and legitimate names such as `M21 Roofing LTD`, `A & B Roofing`, `Jim's Roofers` and `3M` are retained.

Deterministic name resolution uses a plausible existing name, an explicitly named business in a caption, an owned website/business email domain, a business-like free-mailbox handle, or a genuine business social profile. Social post IDs and personal LinkedIn profiles are not names. When there is no defensible name, templates use `your company` and `Hi there,` instead of sending the caption.

Existing lead rows receive read-time cleanup; imports and new discovery candidates also use the same checks. No destructive bulk update of historical company fields is performed.

Before a **new campaign draft** is rendered, ambiguous original names can receive optional homepage research and one grounded AI cleanup batch using the saved OpenAI key (or Gemini when OpenAI is not connected). Research happens before preview and approval, not at delivery. A website-declared name can supersede an inferred domain label. AI is permitted to select a name from that lead's evidence, not invent a company or copy a neighbouring lead's identity. Provider failures keep the deterministic fallback.

Cost/latency bounds are intentional: every recipient gets deterministic cleanup; optional homepage research covers at most four distinct domains with an eight-second scheduling budget; a started HTTP request can finish after that budget. A homepage probe makes at most two requests, including a redirect, with a two-second per-operation timeout. At most ten unresolved records enter one AI request, with a twelve-second per-operation timeout. These are not a guaranteed total wall-clock deadline. Not every recipient in a 500-lead campaign gets fresh website/AI research. Stable existing names and wholly static templates do not trigger this extra research. Existing model settings/defaults are preserved, and model availability was not tested live.

Subjects, greetings, HTML bodies and scheduled follow-ups in a new campaign are rendered from the same prepared lead row. Existing aliases such as `{{Business Name}}`, `{{company_name}}` and `{{greeting}}` are preserved. Mail transports, HTML sanitization, approval, rate limits, suppression, unsubscribe and stop-on-reply behavior are not replaced.

### Expected examples without a successful website/AI lookup

These are tested outputs from the supplied evidence, **not independent verification of legal or trading names**.

| Input evidence | Deterministic output |
| --- | --- |
| `Another roof DONE RIGHT...` + `mqconstructionct.com` + `mpconstructionct@gmail.com` | `MQ Construction CT` (website-domain fallback) |
| Same caption + only `mpconstructionct@gmail.com` | `MP Construction CT` (mailbox fallback) |
| `Roof replacement installed by James Roofing in Newton ...` | `James Roofing` |
| `dan.roofing ... Boardman Roofing provides 24/7 ...` | `Boardman Roofing` |
| `Jim's Roofers are looking for more people ...` | `Jim's Roofers` |
| `PROJECT COMPLETE ...` + `mscroofinginfo@gmail.com` | `MSC Roofing` |
| `M21 Roofing LTD` | unchanged |
| Emoji/caption only, no usable evidence | `your company` / `Hi there,` |

The first example has a real **MQ versus MP conflict**. The patch prefers the supplied owned website domain to a Gmail handle, and attempts website-declared identity for ambiguous campaign recipients. Neither domain formatting nor AI proves that a scraped website/email pair belongs to the same company. Review conflicting records before approval. A more confident website/AI name used in a campaign preview is not automatically written back over the historical database field.

## 2. Install the recommended changed-files ZIP

First pause affected campaigns in the app and make a source backup/commit of your working project. Stop local development processes while copying files. Do not run the installer against a live server directory with processes editing files.

Extract `lead-agent-apollo-company-name-patch.zip` into a separate folder, for example:

```text
D:\Downloads\lead-agent-apollo-company-name-patch
```

Inside that folder are `APPLY_PATCH.py`, `patch_manifest.json`, `START_HERE.md`, and the replacement `backend`, `frontend`, and `docs` trees.

The target is your **existing repository root**, the folder that already contains `backend` and `frontend`. The context uses `D:\Leads-Agent\leads-agent`; change that path when your actual folder is different.

Run in PowerShell:

```powershell
cd D:\Downloads\lead-agent-apollo-company-name-patch
python .\APPLY_PATCH.py --project "D:\Leads-Agent\leads-agent" --check
```

This is read-only. It checks payload hashes, all replacement destinations, and unchanged source/dependency contracts against the uploaded version. It allows already-applied identical patch files. It refuses differing files instead of overwriting a newer or locally edited version. Do not bypass a refusal by force-copying: compare the named differences first. The installer accepts CRLF/LF-only changes for the known UTF-8 text files to accommodate Git for Windows, while preserving exact local bytes in the backup. Other content changes still cause a refusal.

After a successful check:

```powershell
python .\APPLY_PATCH.py --project "D:\Leads-Agent\leads-agent" --apply
```

The installer creates a backup **outside** your repository, prints its exact path, and preserves original bytes. Typical location:

```text
D:\Leads-Agent\leads-agent-patch-backups\<timestamp>
```

It never reads/writes `.env` secrets, connects to providers, changes Git, edits a database, sends mail or deploys. It preserves `.env` files and unrelated files. An interrupted apply can be restored with the printed rollback command. Keep the extracted package and backup until the deployment is verified.

Manual placement is possible after reviewing the same preflight: merge each package directory into its corresponding existing directory. For example, package `backend/app/providers/apollo_search.py` becomes project `backend/app/providers/apollo_search.py`. **Do not replace the entire backend/frontend folder** and do not create `backend/backend`. Add the new files as well as replacing the old ones. The manifest is the exact file list. The installer is preferable because it gives you a checked backup and rollback.

## 3. Run the full project checks locally

Use the project's Python 3.13 environment and existing dependency pins. Do not downgrade dependencies to match the temporary test environment. No new dependency, migration or environment variable is required by this patch.

```powershell
cd D:\Leads-Agent\leads-agent\backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

If `.venv` does not exist, create it with your project's Python interpreter first (`python -m venv .venv`). Ensure the full suite collects and passes; the partial-suite exclusions in the test report are not a release gate.

Frontend:

```powershell
cd D:\Leads-Agent\leads-agent\frontend
npm ci --include=optional
npm run check
npm run test
npm run build
```

Run each command and check its exit code before proceeding. Keep `package-lock.json` and the existing Windows optional-binding configuration. On a native-binding error, follow your existing Windows troubleshooting rather than replacing the lockfile as part of this patch.

The patch adds no migration. Preserve your existing startup step, `python -m app.db.migrate`. For a manual migration check, use your development/test database, not an unintended production connection. The existing Render start command already runs the idempotent migration step before the API starts.

## 4. Deploy both services

Only after the complete checks pass, review `git diff` and stage the changed/new `backend`, `frontend` and `docs` files. Never stage `.env`, service-account JSON, local backups, `.venv` or `node_modules`. Commit with a descriptive message such as `Fix Apollo discovery and company-name personalization`, then push to the branch your existing Render services deploy.

Deploy the API/backend first, then the frontend Static Site from the same patch commit. The old frontend remains compatible with the updated backend; a new frontend pointed at the old API would still have Apollo rejected by validation. Use your existing deploy configuration. Do not recreate the services, Firebase project or Turso database. Do not rotate `CREDENTIAL_ENCRYPTION_KEY`; saved provider/sender credentials depend on its original value.

The patch does not change `APP_VERSION`; checking only that value is not proof that both services picked up the patch. Inspect the deployment commit/build logs and verify the new Apollo option after a browser hard refresh.

## 5. Controlled post-deployment check

Confirm login, provider connections and your existing lead lists still work. Return from Settings to Find Leads and verify Apollo appears connected in the source selector and Search card. Select it explicitly and run a small, intentional company search; this may consume Apollo credits. Check the resulting source is `apollo`. An email is not guaranteed by company search. A denied endpoint should show an actionable error instead of a misleading successful empty search.

Next create a **new draft campaign** for a controlled test recipient using:

```text
Subject: A quick idea for {{Business Name}}

{{greeting}}
I have a homepage idea for {{company_name}}.
```

Use a test lead with a deliberately caption-like original name and a real business website, then inspect the subject, greeting, HTML and follow-up preview. Verify no emoji/caption appears as the company name. Approve only that controlled test after reviewing it, and confirm the delivered email. Also smoke-test your usual Serper/Brave flow, exports, one follow-up/reply flow where relevant and Admin. No test message has been sent on your behalf while preparing this package.

## 6. Existing campaigns and text that this does not rewrite

Existing campaigns contain previously rendered message snapshots. This patch deliberately **does not re-render already-approved, queued, waiting, or sent messages**, since that would change copy after approval.

Pause affected old campaigns before more sends. Recreate campaigns after deployment for **unsent intended recipients only**, preview the new copy and approve explicitly. Cancel the old queued work as appropriate to prevent duplicate sends. Do not include delivered recipients again merely to fix their company label. Pausing the campaign also matters for waiting follow-ups that contain the old text.

Use placeholders in your templates. A bad company name pasted literally into the template is still literal text. The existing Quick Send interface accepts a manually composed subject/body without a lead-template association; this patch does not rewrite arbitrary Quick Send prose or auto-personalize a pasted name there.

The supplied screenshot also says **“For an accounting firm”** while the examples are roofing businesses. This is separate hardcoded template copy. Replace it with suitable roofing wording or neutral `For a business like yours, ...`; a company-name fix cannot reliably repair a template's niche claims. Existing `{{niche}}`/`{{industry}}` aliases can use actual lead/list data, but review their value too.

## 7. Roll back

Stop local processes and keep affected live campaigns paused. Run the exact rollback command printed by the installer, substituting its backup directory:

```powershell
cd D:\Downloads\lead-agent-apollo-company-name-patch
python .\APPLY_PATCH.py --project "D:\Leads-Agent\leads-agent" --rollback "D:\Leads-Agent\leads-agent-patch-backups\<timestamp>"
```

Rollback checks for subsequent edits before writing, restores original files, and removes newly added patch files. It does not delete unrelated files or modify your database. Later edits are not silently discarded. For production, deploy the restored source or roll both services back to the previous known-good commit using your normal release process. Local rollback alone does not change hosted services. There is no new schema to reverse.

## 8. Change map

| Area | Files |
| --- | --- |
| Search UI/types | `frontend/src/pages/FindLeadsPage.tsx`, `frontend/src/lib/api.ts`, new `frontend/src/lib/searchProviders.ts` |
| Apollo routing/adapter | `backend/app/api/leads.py`, `backend/app/leads/schemas.py`, `backend/app/leads/discovery.py`, `backend/app/providers/catalog.py`, new `backend/app/providers/apollo_search.py` |
| Shared name quality | new `backend/app/leads/company_names.py`, `backend/app/leads/smart_data.py`, `backend/app/leads/crawler.py` |
| Grounded AI/draft rendering | `backend/app/providers/ai.py`, new `backend/app/outreach/personalization.py`, `backend/app/outreach/rendering.py`, `backend/app/outreach/repository.py`, `backend/app/outreach/dependencies.py` |
| Added tests | `backend/tests/test_apollo_search.py`, `backend/tests/test_company_name_safety.py`, `backend/tests/test_name_personalization.py`, `backend/tests/test_name_campaign_integration.py`, `frontend/src/lib/searchProviders.test.ts` |
| Patch documents | this file and `docs/PATCH_TEST_REPORT.md` |

The full-source ZIP preserves the original release documents; this patch guide and patch manifest describe the new changes. Do not rerun an older smart-template patch on top of this one.
