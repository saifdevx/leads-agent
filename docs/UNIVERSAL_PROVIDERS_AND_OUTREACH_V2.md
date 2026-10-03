# Lead Gen: provider capabilities and outreach identity fix (v2)

Prepared 3 October 2026. This patch builds on the first Apollo/company-name patch, not on the original unpatched ZIP.
The current GitHub main reference was read as `e36380291b7ab4ce06a3d2e6f94813fe8d78b49d`.
The local baseline's complete backend and frontend Git tree hashes match the corresponding trees returned by GitHub:
backend `4df75c4d733f373043c7e3b59ff58d4626943c6d`; frontend `24711f433991d5115b064ee298f6780aee09d825`.
No remote commit, deployment, email, provider credit purchase, or production database write was performed while preparing this package.

## First: pause affected campaigns

Pause old campaigns and waiting follow-ups before deployment. The earlier fix did not reject ranked directory headings such as
“Top 25 Solar installers based in London, United Kingdom”. Do not treat a directory operator's address as a solar installer's address.
Already sent messages cannot be corrected retroactively. Already approved copies are not secretly rewritten by this patch.

## What changed

### Capability-driven integrations, not an Apollo-only dropdown

The backend provider catalogue supplies capabilities, labels, order and usage notes to the frontend.
Settings, discovery source selection, AI selection, connection cards and contact-enrichment choices use these capabilities.
Request validation uses the same catalogue. A regression test checks that every advertised search capability has an implemented adapter.

| Integration | Search | Optional AI cleanup | Contact enrichment |
|---|---|---|---|
| Serper | Web | No | No |
| Brave Search | Web | No | No |
| Tavily (new) | Web | No | No |
| Exa (new) | Web | No | No |
| Prospeo (new search capability) | Companies | No | Yes, existing workflow |
| Apollo | Companies | No | Yes, existing workflow |
| OpenAI | No | Yes | No |
| Gemini | No | Yes | No |

Existing saved Prospeo/Apollo keys are reused. Search and enrichment are separate operations; company search does not reveal
or fabricate contact emails. OpenAI/Gemini are cleanup tools, not independent lead databases in this app. Mail senders are not search sources.
An arbitrary unsupported platform cannot work just by pasting its key: a backend adapter and catalogue entry are still needed.
Once implemented there, it no longer needs another hardcoded frontend dropdown edit.

“Key connected” means the connection validation succeeded, not that every endpoint is permitted or credits are available.
Saving Tavily/Exa keys runs one small search request. Their ordinary discovery requests are bounded: Tavily basic without automatic
parameter/depth upgrades or generated answers; Exa fast, at most 10 results, without deep research or generated summaries.
Check each provider's free quota, billing settings and API access before use. The app cannot guarantee searches stay inside a free tier.

Automatic mode preserves web-first behavior. It tries connected Serper, Brave, Tavily and Exa in catalogue order.
When no web-search provider is connected it tries connected Prospeo, then Apollo. Failure can use credits on another connected source;
explicit source selection never silently switches to another provider. It does not silently fall from connected web sources into paid company databases.
Denied/exhausted discovery sources are skipped for the rest of that job, not retried for every query. An all-failed web search is failed,
not reported as an empty success. A new-search button remains available after terminal jobs.
Search options, including optional enrichment consent, are fixed for the running job rather than read from later checkbox changes.

Company search is capped at 10 page attempts per job across fallback sources. Prospeo has fixed 25-result pages; Apollo uses up to 100.
This means a Prospeo-only job cannot retrieve more than 250 company rows within this cap, even when the requested target is 500.
Targets are not guarantees. Web searches retain the existing job call cap (10–50); Tavily/Exa use at most five distinct queries each,
without pretending that those APIs offer offset pagination. Website checking and optional name research remain separately bounded.
Prospeo locations are resolved through its free suggestions endpoint (at most two suggestion requests, cached across pages).
Ambiguous locations fail with guidance instead of silently searching worldwide. Use a full city/state/country or a country name.

### Apollo's permission error

The code cannot grant Apollo account permissions. Check that the saved Apollo key permits `api/v1/mixed_companies/search` and
that the Apollo account is eligible for that endpoint. Apollo currently documents a work-email registration requirement and
possible additional eligibility restrictions. Prefer the required endpoint permission rather than unnecessarily broad master-key access.
Account authentication can succeed while company search is denied. The app now explains this without disconnecting working enrichment.
Use another connected source while resolving access with Apollo; the patch does not bypass provider restrictions.

### Company names and recipient identity are checked separately

The original screenshot is treated as a directory/list record, not converted into “RevenueBase”. It is excluded from discovery results
when detected and held out of new outreach when already saved/imported. My Leads displays “Review required” and the reason.
Common directory/listicle/ranking titles, truncated captions, emoji-only strings and generic placeholders are not accepted as company names.
Existing valid names are preserved, including the previously tested M21 Roofing LTD, James Roofing and similar cases.

A name that can be resolved from that lead's own website, email/domain, explicit caption attribution or eligible social handle is cleaned.
Optional homepage/AI research remains limited to four domains and one batch of up to ten unresolved records per campaign; the existing
OpenAI/Gemini keys and configured model IDs are retained. AI results must be grounded in that record's evidence.

A genuinely unknown name can use neutral copy, for example:

    Subject: Free sample
    Hi there,
    I would like to create a homepage concept for your company.

Old `Hi {{Business Name}} team,` templates also get a neutral greeting when no name is available; a trailing “for your company” is
removed from an unknown-name subject. Exact bad literals tied to that lead can be corrected during NEW draft rendering.
Arbitrary hardcoded claims or industry-specific offers are not rewritten by AI. Review the resulting wording, especially unusual HTML/templates.

A mismatched business website and corporate email domain is held for review, not made safe merely by omitting the company name.
Public mailbox domains and same-business subdomains are treated separately. This is a conservative domain comparison, not legal
ownership verification or a complete public-suffix database. Inferred labels are marked as inferred, not “verified”.
A syntactically valid email is not necessarily deliverable or the intended company's contact. No SMTP/mailbox ownership validation is claimed.

Website extraction no longer takes an unrelated corporate-domain footer email when no matching business email exists.
Obvious unrelated organizations in structured website metadata are ignored. Public business mailboxes may still be used when found.
Conservative screening can hold a real business with an unusual name; verify it rather than forcing the automation to invent an identity.

### Checks at all supported sending entry points

New campaign preparation checks recipients, subject, body and follow-ups before database writes. Duplicate recipient emails in the same
campaign are skipped. The draft response reports identity/content holds and duplicates. Unknown names are not automatically blocked.
Directory records, mismatched identities, invalid/no-reply addresses and detected unsafe literals are held.

Approval, resume and retry inspect saved pending copy. The common delivery function checks again before either Hostinger or Gmail is called;
this covers queued initial emails, follow-ups and Quick Send. Quick Send is not turned into an AI composition endpoint: unsafe manual copy
is rejected with guidance, not silently rewritten. When stored lead evidence exists for its recipient, it is checked too.
The worker marks a safety-held message failed and does not incorrectly mark the sender's credentials broken.

The patch does not retroactively re-render old campaigns. Create replacement drafts for unsent intended recipients only, inspect previews,
and approve explicitly. Correct or remove contaminated lead records before re-importing verified data. Do not resend to already contacted
recipients just to test a corrected template. A message already accepted by a mail provider before deployment cannot be recalled by this code.

## Install (recommended)

1. Back up or commit your currently working source. Keep affected campaigns paused.
2. Extract `lead-agent-universal-providers-safety-v2-patch.zip` OUTSIDE your existing project.
3. Open PowerShell in the extracted directory containing `APPLY_V2_PATCH.py` and `patch_manifest.json`.
4. Replace the example project path below if yours differs:

```powershell
python .\APPLY_V2_PATCH.py --project "D:\Leads-Agent\leads-agent" --check
```

This is read-only. It checks changed files, payload hashes and unchanged runtime/dependency interfaces against the verified baseline.
It accepts ordinary UTF-8 CRLF/LF checkout differences. If it reports a conflict, stop and compare it; do not force-copy over newer work.
After a successful check:

```powershell
python .\APPLY_V2_PATCH.py --project "D:\Leads-Agent\leads-agent" --apply
```

The installer replaces/adds only manifest files and creates an exact backup outside the repository. Reapplying is a checked no-op.
It does not touch `.env`, keys, encrypted credentials, migrations, your database, Git history or Render settings.
Do not regenerate `CREDENTIAL_ENCRYPTION_KEY`. Do not delete whole backend/frontend folders. Do not apply the previous v1 ZIP again.

Manual installation: first run the read-only check, then copy each manifest file to the SAME relative path in your project.
`REPLACED_FILES_V2.md` lists every new/replaced file. All changes are needed together; copying only the frontend dropdown is not sufficient.
Folder contents may be merged in Windows Explorer, but never delete/replace entire existing project folders or copy secret files.
The installer is preferable because it checks compatibility, takes a backup, and avoids missing the new modules.

## Test and deploy both services

Use the unchanged project-pinned dependencies, not the older packages available in the packaging environment.

```powershell
cd D:\Leads-Agent\leads-agent\backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q

cd D:\Leads-Agent\leads-agent\frontend
npm ci --include=optional
npm run check
npm run test
npm run build
```

Stop if any check fails. This package does not include a completed production frontend build. Preserve your normal existing migration/startup
command, even though this patch adds no migrations. Do not alter the lockfile or downgrade dependencies just to match this test environment.

Once all local checks pass, stage only the manifest's files. From the extracted patch directory:

```powershell
$Project = "D:\Leads-Agent\leads-agent"
$Files = (Get-Content .\patch_manifest.json -Raw | ConvertFrom-Json).files.path
git -C $Project status --short
git -C $Project branch --show-current
git -C $Project add -- $Files
git -C $Project diff --cached --stat
git -C $Project diff --cached
```

Review the staged diff, including anything that was staged before these commands. No `.env`, tokens, service-account files, ZIPs, backups,
`node_modules` or virtual environments should be committed. Commit only the intended patch. Push to the branch your Render services actually
watch; do not assume or force a different branch. Both backend and frontend must deploy the same new commit. Deploy backend first when
controlling the sequence; automatic deployments may start in parallel. Wait until BOTH services are live before testing or resuming work.

After a hard refresh, confirm Prospeo / Companies, Tavily and Exa in Settings/Find Leads. Start with 25 requested companies and automatic
contact enrichment OFF. Check provider permissions and costs before optional enrichment. Use one safe internal/test recipient and preview
the initial email plus follow-ups. Recheck login, My Leads, export, suppression, sender connection and pause/resume.

## Rollback

Keep the backup path printed by the installer. From the extracted patch folder:

```powershell
python .\APPLY_V2_PATCH.py --project "D:\Leads-Agent\leads-agent" --rollback "D:\Leads-Agent\leads-agent-patch-backups\THE_PRINTED_TIMESTAMP"
```

Rollback refuses to overwrite subsequent content edits. It restores exact original file bytes and removes newly added patch files.
This restores LOCAL SOURCE ONLY: deploy the restored source to roll back hosted services. Keep affected campaigns paused because the old
version still has the reported identity issue. No database rollback is required by this patch.

## Official API references checked on 3 October 2026

- Prospeo company search: https://prospeo.io/api-docs/search-company
- Prospeo filters: https://prospeo.io/api-docs/filters-documentation
- Prospeo canonical locations: https://prospeo.io/api-docs/search-suggestions
- Prospeo nullable company schema: https://prospeo.io/api-docs/company-object
- Apollo organization search/access: https://docs.apollo.io/reference/organization-search
- Tavily search contract: https://docs.tavily.com/documentation/api-reference/endpoint/search
- Tavily quota/billing: https://docs.tavily.com/documentation/api-credits
- Exa search contract: https://exa.ai/docs/reference/search
- Exa quota/billing: https://exa.ai/pricing

Contracts were checked against documentation and tested with mocked responses. No live account key, paid search or real delivery was used.
See `docs/V2_TEST_REPORT.md` for executed checks and limitations. These protections address specific failure classes; they do not guarantee
that every retrieved company identity, recipient relationship or geographic/industry match is correct.
