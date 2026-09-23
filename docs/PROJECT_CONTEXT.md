# Leads Agent — Current Project Context

Use this file as the authoritative handoff if the conversation is lost.

## Product goal

A custom Lead Generation + Outreach web app with a simple user-facing workflow:

**Find Leads → My Leads → Outreach → Settings**

Admin is shown only to administrators.

The user wants the complex provider/worker/database systems hidden behind a simple, premium B2B SaaS interface.

## Stack

Frontend:
- React + Vite + TypeScript + Tailwind

Backend:
- FastAPI + Python

Auth:
- Firebase Authentication
- server-side Firebase token verification

Database:
- Turso SQL-over-HTTP

Search / AI / enrichment:
- Serper / Brave
- Gemini / OpenAI
- Prospeo / Apollo

Email:
- Hostinger Agentic Mail primary
- Gmail optional

Production target:
- Render static frontend
- Render FastAPI API
- Render lead/discovery worker
- Render outreach worker

## Working feature set

- Firebase login/register/Google/password reset
- Turso user/application data
- automated lead discovery
- website crawling
- AI cleanup
- lead deduplication
- Prospeo/Apollo enrichment
- Excel/CSV import
- Excel/CSV export
- My Leads filters/bulk operations
- Hostinger sender
- Gmail optional sender
- Quick Send
- templates
- campaigns + preview/approval
- configurable intervals and optional sending window
- suppression list
- follow-up sequences
- reply sync/inbox
- stop-on-reply
- reply classification
- campaign analytics/detail/retry
- optimistic UI/cache for common actions

## Latest bundle: Admin + production + performance

Adds:
- Admin UI: Overview / Users / Jobs / System
- `ADMIN_EMAILS` admin bootstrap
- user suspension/reactivation
- server-side suspended-user enforcement
- admin audit log
- failed-job retry controls
- provider/worker/webhook health
- durable lead/enrichment worker
- job claiming/locks/stale-release
- lead/outreach worker heartbeats
- Render production Blueprint
- real Hostinger live-webhook setup after public deployment
- persistent Turso HTTP connection pooling
- lead database snapshot endpoint
- outreach dashboard snapshot endpoint
- frontend in-flight GET request deduplication
- short-lived user access-state cache

## New migration

`004_admin_operations`

Adds:
- `users.role`
- `jobs.locked_at`
- `jobs.locked_by`
- sender webhook status/url
- `worker_heartbeats`
- `admin_audit_log`

## New/important environment names

Backend:
```text
ADMIN_EMAILS
BACKGROUND_JOBS_MODE
WORKER_POLL_SECONDS
WORKER_LEASE_SECONDS
USER_ACCESS_CACHE_SECONDS
PUBLIC_API_URL
```

Keep all previously configured Firebase/Turso/provider/email values.

Never regenerate `CREDENTIAL_ENCRYPTION_KEY` while stored encrypted credentials exist.

## Local mode

Recommended:
```env
BACKGROUND_JOBS_MODE=inline
PUBLIC_API_URL=
ADMIN_EMAILS=your-own-login@example.com
```

Local processes:
- FastAPI
- Vite frontend
- outreach worker

Lead worker is optional locally unless testing worker mode.

## Production mode

Render API:
```env
BACKGROUND_JOBS_MODE=worker
PUBLIC_API_URL=https://YOUR-API.onrender.com
CORS_ORIGINS=https://YOUR-FRONTEND.onrender.com
FRONTEND_APP_URL=https://YOUR-FRONTEND.onrender.com
ADMIN_EMAILS=your-admin-login@example.com
```

Production includes both background workers.

After deploy, enable Hostinger live replies from Outreach → Senders.

## Design direction

Professional B2B SaaS. Avoid generic AI-template aesthetics.

Colors:
- Purple #7B61FF
- Secondary Purple #9D84FF
- Light Accent #B39CFF
- Lime #BCE953 sparingly
- Ink #14151C
- Slate #4B4F5E
- Lavender #E8EAF3
- White #FFFFFF

Typography:
- Manrope headings
- Inter UI/body

## Git / delivery preference

Repository:
https://github.com/saifdevx/leads-agent

User prefers normal professional commit messages and no public checkpoint/version tags.

Deliver complete ZIP bundles with setup/test/rollback docs.

Do not overwrite:
- `.git`
- `.env` files
- `.venv`
- local `node_modules`
- Firebase private JSON
- secrets

## Next and final planned bundle

**Final UX + Security + Release Polish**

This should include:
- cohesive UI refinement across every screen
- better dashboard/home summary
- final responsive/mobile pass
- accessibility
- loading/empty/error/success consistency
- security/rate-limit/abuse hardening
- final audit/history usability
- production smoke/e2e/regression coverage
- final release/runbook documentation

Do not restart completed Firebase/Turso/discovery/enrichment/outreach architecture.
