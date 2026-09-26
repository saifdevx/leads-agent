# Lead Gen — Master Project Context / Handoff

> Upload this file into a new AI conversation when continuing development. Treat it as the authoritative handoff unless the repository itself shows a newer implementation.

**Last updated:** 2026-09-26  
**Repository:** https://github.com/saifdevx/leads-agent  
**Production frontend:** https://lead-gen-web-rq8w.onrender.com  
**Production API:** https://lead-gen-api-bp7i.onrender.com  
**API health:** https://lead-gen-api-bp7i.onrender.com/health

---

# 1. What this project is

Lead Gen is a custom lead-discovery and outreach web application.

It is not an n8n workflow.

The intended user experience is deliberately simple:

```text
Find Leads
    ↓
Review / Enrich
    ↓
Export or Outreach
    ↓
Follow-ups / Replies
```

The backend may contain provider adapters, jobs, workers, caching, retries, enrichment waterfalls, and security controls, but those details should stay behind the interface.

Normal navigation:

- Find Leads
- My Leads
- Outreach
- Settings

Admin users additionally see:

- Admin

---

# 2. Product philosophy

## Free-first + BYOK

The product should remain useful with low-cost/free sources while supporting higher-quality paid services through Bring Your Own Key.

Do not make premium APIs mandatory for the basic product.

## Simple outside, capable inside

Do not expose infrastructure concepts unless they materially help the user.

The user should think:

> Tell Lead Gen what businesses I want, review the results, then contact the useful ones.

## Evidence before invention

AI may clean, structure, classify, score, or personalize retrieved information.

It should not fabricate business emails, phone numbers, business identities, or factual claims.

## Provider independence

Provider-specific behavior should remain behind adapters so Serper, Brave, OpenAI, Gemini, Prospeo, Apollo, Hostinger, etc. can be replaced or extended later.

---

# 3. Current production state

The app is deployed and working in production.

Production URLs:

```text
Frontend:
https://lead-gen-web-rq8w.onrender.com

API:
https://lead-gen-api-bp7i.onrender.com

Health:
https://lead-gen-api-bp7i.onrender.com/health
```

Deployment platform:

- Render Static Site — frontend
- Render Free Web Service — FastAPI
- embedded lead worker
- embedded outreach worker
- Turso external durable database
- Firebase authentication

The deployed backend uses `APP_ENV=production`.

The current production deployment has been manually tested for:

- login,
- lead searching,
- lead persistence,
- template creation,
- Hostinger email sending,
- provider connections,
- exports,
- admin access.

---

# 4. Current repository / Git workflow

Repository:

```text
https://github.com/saifdevx/leads-agent
```

The user prefers a clean professional Git history.

Do not require visible “Checkpoint 1 / v0.x.x” tags.

Preferred commits are human descriptions such as:

```text
Added automated lead discovery
Added Hostinger mail integration
Improved campaign analytics
Fixed smart template rendering
```

Always push a known-working state before larger changes.

At the time of this handoff, the deployed final-polish code came from the repository's current final-release line. Check Git before changing code because production may have been redeployed since this file was generated.

---

# 5. Current tech stack

## Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Firebase Web SDK

## Backend

- Python
- FastAPI
- Pydantic / pydantic-settings
- httpx
- Firebase Admin
- XlsxWriter
- openpyxl

## Authentication

Firebase Authentication:

- email/password
- Google login
- password reset
- persistent browser sessions
- server-side Firebase ID-token verification

Firebase is for authentication, not the application database.

## Database

Turso using SQL-over-HTTP.

Turso is the source of truth for application data.

## Search

- Serper
- Brave Search

## AI

BYOK:

- OpenAI
- Gemini

## Enrichment

BYOK:

- Prospeo
- Apollo

## Mail

Primary:

- Hostinger Agentic Mail

Optional:

- Gmail

## Hosting

Render:

- frontend Static Site
- backend Free Web Service
- embedded workers for no-cost deployment

---

# 6. Branding and UI

Product name:

**Lead Gen**

Visual direction:

- professional B2B SaaS
- light workspace
- dark/ink sidebar
- restrained purple accents
- lime only as a small high-attention accent
- compact, useful data views
- no generic “AI-generated” design language

Colors:

```text
Primary Purple    #7B61FF
Secondary Purple  #9D84FF
Light Accent      #B39CFF
Lime Accent       #BCE953
Ink               #14151C
Slate             #4B4F5E
Lavender Tint     #E8EAF3
White             #FFFFFF
```

Fonts:

- Manrope headings
- Inter body/UI

Logo assets live under:

```text
frontend/public/
```

The supplied Lead Gen logo is used for sidebar branding, authentication, favicon, Apple touch icon, and web-app manifest.

---

# 7. Core capabilities already implemented

## Find Leads

- niche + location search
- target lead count
- automated search
- Serper / Brave adapters
- Google-style query generation
- public website crawling
- AI cleanup when configured
- deterministic fallback
- niche/location relevance filtering
- domain/business deduplication
- adaptive search budget
- durable jobs
- progress status

## My Leads

- lead lists
- search/filtering
- score filters
- email-state filters
- lead source information
- bulk selection
- bulk deletion
- smart enrichment
- Excel / CSV import
- Excel / CSV export
- optimistic UI
- snapshot API for faster initial loading
- short-lived frontend caching

## Enrichment

- Prospeo
- Apollo
- decision-maker/contact enrichment
- verified-email status where provider verification exists
- free/public data should be preferred before paid enrichment

## Outreach

- reusable templates
- Hostinger sender
- optional Gmail
- Quick Send
- campaign creation
- campaign preview
- explicit approval
- persistent queue
- daily limits
- 20-second+ intervals
- optional sending windows
- pause/resume/cancel/delete
- follow-up sequences
- suppression list
- unsubscribe handling
- inbox/reply handling
- stop-on-reply
- analytics
- retry controls

## Admin

Tabs:

- Overview
- Users
- Jobs
- System

Capabilities include:

- user stats
- lead counts
- email metrics
- provider activity
- running/failed jobs
- user suspension/reactivation
- failed-job retry
- worker health
- system health

---

# 8. Performance architecture already implemented

Several earlier performance problems were addressed.

Current optimizations include:

- persistent Turso `httpx.Client`
- HTTP keep-alive pooling
- batched Turso operations where practical
- lead snapshot API
- outreach snapshot API
- frontend in-flight GET deduplication
- short-lived frontend cache
- mutation cache invalidation
- optimistic Pause / Resume / Delete behavior
- transient GET retry for 502/503/504
- cached user access state
- one-round-trip authenticated-user sync
- gzip API responses

Do not remove these casually.

---

# 9. Production architecture

Zero-cost deployment:

```text
Render Static Site
        │
        ▼
Render Free FastAPI Web Service
        │
        ├── embedded lead worker
        ├── embedded outreach worker
        │
        ├── Turso
        ├── Firebase
        ├── Search / AI / enrichment providers
        └── Hostinger Mail
```

Important limitation:

Render Free web services can sleep after inactivity.

Pending work is stored in Turso, but scheduled background work can be delayed while the service is asleep.

The frontend periodically checks `/health` while actively open.

The repository also preserves a scaled/always-on Render configuration for future use.

---

# 10. Production environment structure

Never store real secret values in this document.

Backend uses variables such as:

```text
APP_ENV
APP_VERSION
LOG_LEVEL

CORS_ORIGINS
FRONTEND_APP_URL
PUBLIC_API_URL

FIREBASE_PROJECT_ID
FIREBASE_SERVICE_ACCOUNT_JSON

TURSO_DATABASE_URL
TURSO_AUTH_TOKEN
TURSO_TIMEOUT_SECONDS

CREDENTIAL_ENCRYPTION_KEY

ADMIN_EMAILS

BACKGROUND_JOBS_MODE
EMBEDDED_WORKERS
WORKER_POLL_SECONDS
WORKER_LEASE_SECONDS
USER_ACCESS_CACHE_SECONDS
QUICK_SEND_PER_MINUTE
```

Frontend uses:

```text
VITE_API_URL

VITE_FIREBASE_API_KEY
VITE_FIREBASE_AUTH_DOMAIN
VITE_FIREBASE_PROJECT_ID
VITE_FIREBASE_STORAGE_BUCKET
VITE_FIREBASE_MESSAGING_SENDER_ID
VITE_FIREBASE_APP_ID
```

Optional Gmail variables exist only when Gmail is used.

---

# 11. Secrets that must never be lost or exposed

Never commit:

- backend `.env`
- frontend `.env`
- Firebase service-account JSON
- Turso auth token
- Hostinger token
- Serper / Brave / OpenAI / Gemini / Apollo / Prospeo keys
- `CREDENTIAL_ENCRYPTION_KEY`

Critical rule:

> Do not regenerate `CREDENTIAL_ENCRYPTION_KEY` after provider or sender credentials have been saved.

Previously stored encrypted credentials depend on it.

---

# 12. Database history

Migrations are additive and must be preserved.

Current schema evolved through migrations including:

- initial database foundation
- outreach
- replies/follow-ups
- admin/operations

Always run:

```powershell
python -m app.db.migrate
```

before deployment/startup as documented.

Migrations should be idempotent.

Never delete old migrations to “clean up” the repo.

---

# 13. Local development commands

Project path used during development:

```text
D:\Leads-Agent\leads-agent
```

Backend:

```powershell
cd D:\Leads-Agent\leads-agent\backend

.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m app.db.migrate
pytest -q

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

Outreach worker locally:

```powershell
cd D:\Leads-Agent\leads-agent\backend

.venv\Scripts\Activate.ps1
python -m app.outreach.worker
```

---

# 14. Windows Vite / Rolldown history

A Windows npm optional-dependency issue happened early in development:

```text
Cannot find native binding
```

Recovery if it reappears:

```powershell
cd frontend

Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
Remove-Item -Force package-lock.json -ErrorAction SilentlyContinue

npm cache verify
npm install --include=optional
```

The project explicitly accounts for the Windows Rolldown binding.

Do not change this dependency handling without testing Windows.

---

# 15. Current deployment URLs

Production:

```text
Frontend:
https://lead-gen-web-rq8w.onrender.com

Backend:
https://lead-gen-api-bp7i.onrender.com

Health:
https://lead-gen-api-bp7i.onrender.com/health
```

Production CORS must include the frontend URL.

Firebase Authorized Domains must include:

```text
lead-gen-web-rq8w.onrender.com
```

---

# 16. Hostinger mail

Hostinger Agentic Mail is the primary current sender.

It is used for:

- Quick Send
- campaign sends
- reply handling / webhook flow

The production backend public URL enables a real Hostinger webhook.

Keep Gmail support optional rather than removing it.

---

# 17. Outreach safety / product rules

Do not weaken these controls by default:

- campaign preview
- explicit approval
- daily caps
- configurable interval
- optional sending windows
- suppression
- unsubscribe handling
- stop on reply
- duplicate-send prevention
- activity tracking
- Quick Send rate protection

The app should not be positioned as a system for bypassing email-provider restrictions.

---

# 18. Current known template issue / immediate next patch

At the moment this context file was generated, the deployed application had a confirmed email-template issue:

A user wrote template variables like:

```text
{{Business Name}}
```

and HTML such as:

```html
<br>
<strong>...</strong>
<a href="...">...</a>
```

The delivered email showed the placeholder and HTML tags literally.

A patch has already been prepared separately as:

```text
lead-gen-smart-templates.zip
```

but the user explicitly asked for this documentation package **before implementing that patch**.

The prepared patch is intended to add:

- alias support such as `{{Business Name}}` → `{{company_name}}`
- `{{greeting}}`
- company-name fallback from real lead evidence:
  - existing company name
  - domain / website
  - business email domain
  - business-like Gmail username
  - social handle
  - safe `your company` fallback
- HTML email rendering
- plain-text fallback
- sanitized HTML

Do not assume this patch has been merged. Check Git before continuing.

Recommended next action after this documentation update:

1. preserve the current production state,
2. apply/test the smart-template patch,
3. create a new campaign after deployment because existing campaign messages were rendered earlier,
4. verify a controlled email renders business name and HTML correctly.

---

# 19. Template direction after the patch

Preferred variables:

```text
{{greeting}}
{{company_name}}
{{first_name}}
{{last_name}}
{{contact_name}}
{{job_title}}
{{niche}}
{{email}}
{{phone}}
{{website}}
{{domain}}
{{location}}
{{linkedin_url}}
{{instagram_url}}
{{facebook_url}}
{{sender_name}}
{{sender_email}}
```

Recommended greeting behavior:

```text
first name exists
→ Hi John,

no person, company exists
→ Hi Acme Roofing team,

no reliable person/company
→ Hi there,
```

Never invent a business name when evidence is insufficient.

---

# 20. Testing discipline

Before deploying code changes:

Backend:

```powershell
pytest -q
python -m app.db.migrate
```

Frontend:

```powershell
npm run check
npm run test
npm run build
```

Then smoke-test:

1. login,
2. Find Leads,
3. My Leads,
4. export,
5. Quick Send,
6. one-recipient campaign,
7. reply handling if relevant,
8. Admin.

Do not call a change complete because it merely builds.

---

# 21. UI direction

The user wants the application to look polished and human-designed.

Do not reintroduce:

- huge gradients,
- glassmorphism everywhere,
- excessive rounded cards,
- giant marketing headings inside work screens,
- excessive purple,
- unnecessary illustrations,
- generic “AI magic” language.

Prefer:

- compact useful tables,
- strong spacing hierarchy,
- restrained shadows,
- clear forms,
- immediate button feedback,
- subtle animation,
- professional empty/loading/error states,
- desktop-first responsiveness.

Current screenshots are stored in the documentation package under:

```text
docs/screenshots/
```

---

# 22. Future roadmap

Core product is deployed.

Future work should now be based on real usage.

Potential future additions:

## Lead quality / research

- Google Places
- more verification sources
- saved ICP/search recipes
- stronger region/city expansion
- industry-specific query strategies
- deeper business-site research

## Outreach

- dedicated outbound integrations such as Instantly / Smartlead
- richer sequence builder
- more analytics
- meeting-booking workflows
- improved reply classification

## CRM

- HubSpot
- Pipedrive
- other CRMs
- lead sync / campaign sync

## SaaS / teams

- workspaces
- teams
- permissions
- billing
- usage plans
- client/agency accounts
- white-labeling

## Scale

- dedicated always-on workers
- queue service if needed
- provider cost accounting
- monitoring / alerts
- larger dataset optimizations

Do not build these merely because they are possible. Add them when real usage justifies the complexity.

---

# 23. Engineering rules for future AI sessions

A future assistant should:

1. inspect existing code before modifying it,
2. preserve working behavior,
3. use the repository/current files as source of truth,
4. implement the smallest coherent change,
5. keep provider-specific code behind adapters where practical,
6. never expose secrets to the frontend,
7. use database migrations for schema changes,
8. run tests/regression checks,
9. provide complete replacement files/ZIPs when practical,
10. include rollback instructions,
11. keep UI simple,
12. do not restart completed Firebase/Turso/deployment work.

Do not rewrite the project from scratch.

---

# 24. Message to use in a future chat

Upload this file and say:

> Use this Lead Gen project context as the authoritative handoff. Continue from the current repository and production state. Do not redesign or restart completed authentication, Turso, Render deployment, lead discovery, outreach, or admin work. Inspect the existing code before changing it, preserve working behavior, run regression tests, and provide complete replacement files/ZIPs for significant changes. Check the “Current known template issue / immediate next patch” section first.

---

# 25. Current status summary

Working and deployed:

- Lead Gen branding
- Firebase authentication
- Google login
- Turso database
- automated search
- public website crawling
- AI provider integrations
- enrichment providers
- lead scoring / dedupe
- My Leads
- CSV/XLSX import/export
- templates
- Hostinger sending
- Quick Send
- campaigns
- follow-ups
- reply handling
- suppression/unsubscribe
- analytics
- admin
- caching/performance optimizations
- Render deployment

Immediate pending improvement:

**Smart template rendering / personalization patch.**

That is the next change unless real production usage reveals a more urgent bug.
