# Leads Agent Project Context

## Product
Custom React/FastAPI lead-generation and outreach web app. Keep the normal UX simple: **Find Leads → My Leads → Outreach → Settings**.

## Stack
- React + Vite + TypeScript + Tailwind CSS
- FastAPI / Python
- Firebase Auth
- Turso SQL-over-HTTP
- Serper/Brave search adapters
- Gemini/OpenAI BYOK
- Prospeo/Apollo enrichment
- Hostinger Agentic Mail primary sender
- Gmail optional sender

## Current working flow
1. User signs in.
2. Finds leads automatically or imports Excel/CSV.
3. Reviews, filters, enriches, deletes and exports leads.
4. Selects leads for Outreach.
5. Creates templates.
6. Connects Hostinger/Gmail sender.
7. Creates a campaign, optionally adds follow-up templates, previews and approves.
8. Worker sends the initial message and schedules later follow-ups.
9. Reply sync/webhook records replies and stop-on-reply cancels future steps.
10. Reply Inbox and campaign details show outreach outcomes.

## Latest bundle
**Replies + follow-ups + campaign analytics + responsiveness**

Adds:
- follow-up sequences
- stop-on-reply
- Reply Inbox
- manual Hostinger reply sync locally
- Hostinger webhook-ready production endpoint
- interested/not-interested/unsubscribe/out-of-office classification
- unsubscribe suppression
- campaign details + reply rate + message statuses
- failed-message retry
- optimistic campaign controls
- optimistic bulk lead deletion
- short-lived frontend response cache
- subtle animations
- fix for all-day sending window

## New migration
`003_replies_followups`

## New environment variable
`PUBLIC_API_URL=` — leave blank locally; set to deployed API HTTPS base URL later.

## Local paths
Repo: `D:\Leads-Agent\leads-agent`
Firebase Admin secret: outside repo under `D:\Leads-Agent\secrets\`

## Secrets
Never commit `.env`, Firebase JSON, Turso tokens, provider API keys, Hostinger tokens, Gmail OAuth secret, or webhook secrets. Never regenerate `CREDENTIAL_ENCRYPTION_KEY` after credentials have been stored.

## Git preference
User prefers normal professional commit messages and does not want public checkpoint/version tags.

## Remaining final roadmap
The project is intentionally finishing in three large bundles:

1. **Replies + follow-ups + campaign analytics** — THIS BUNDLE.
2. **Admin + production deployment + deeper performance optimization**.
3. **Final UX + security + release polish**.

Do not redesign completed Firebase, Turso, discovery, enrichment, export, import, sender, campaign, or reply systems from scratch.
