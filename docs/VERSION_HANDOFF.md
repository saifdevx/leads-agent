# Project Handoff

## Current product state

The application is now production-architecture ready with:
- Firebase authentication
- Turso data persistence
- automated lead discovery
- AI cleanup
- public website crawling
- enrichment
- Excel/CSV import/export
- Hostinger/Gmail sender architecture
- templates/campaigns/quick send
- follow-ups/replies/suppression/analytics
- Admin operations
- durable background workers
- Render production Blueprint
- performance optimizations

## Current architecture

```text
React/Vite static frontend
        ↓
FastAPI API
        ↓
Turso database
   ↙          ↘
lead worker   outreach worker
   ↓              ↓
search/AI/       Hostinger/Gmail
crawl/enrich
```

## Local behavior

`BACKGROUND_JOBS_MODE=inline` keeps Find Leads easy to test locally.

Outreach still needs:
```powershell
python -m app.outreach.worker
```
for queued campaign sending.

## Production behavior

`BACKGROUND_JOBS_MODE=worker` means discovery/enrichment jobs are claimed by `lead-platform-lead-worker`.

Outreach is processed by `lead-platform-outreach-worker`.

## Admin

Bootstrap admin access with backend `ADMIN_EMAILS`.

## New migration

`004_admin_operations`

## Next/final planned bundle

**Final UX + security + release polish**

Do not redesign the completed architecture from scratch. Focus next on:
- cohesive visual polish across every page
- dashboard/home experience
- accessibility/responsive details
- loading/empty/error states
- security hardening and abuse limits
- pagination/large-list UX where useful
- audit/history surfaces
- final regression/e2e tests
- final deployment/runbook polish
