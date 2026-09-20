# Leads Agent Project Context

## Product
Custom React/FastAPI lead-generation and outreach web app. Keep the normal UX simple: Find Leads, My Leads, Outreach, Settings.

## Stack
- React + Vite + TypeScript + Tailwind CSS
- FastAPI/Python
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
3. Reviews, filters, enriches and exports leads.
4. Selects leads for Outreach.
5. Creates/edits templates.
6. Connects Hostinger/Gmail sender.
7. Creates campaign, previews and approves.
8. Worker sends using daily limit, optional time window and configurable interval.
9. Quick Send allows one-off manual/testing messages.

## Important local paths
Repo: `D:\Leads-Agent\leads-agent`
Firebase admin secret: outside repo under `D:\Leads-Agent\secrets\`

## Secrets
Never commit `.env`, Firebase JSON, Turso tokens, provider API keys or Hostinger tokens. Never regenerate `CREDENTIAL_ENCRYPTION_KEY` after credentials have been stored.

## Git preference
User prefers normal professional commit messages and does not want public checkpoint/version tags.

## Latest update
- Quick Send
- Excel/CSV upload
- optional sending window
- 20s minimum campaign interval / 30s default
- campaign auto/manual refresh
- progress display
- campaign delete for non-sending campaigns

## Next major product work after this passes
Combine:
- Hostinger reply webhook / reply sync
- stop-on-reply
- multi-step follow-up sequences
- reply inbox
- campaign analytics
- basic admin/usage/system dashboard
- production worker deployment / final performance and UX hardening

Do not redesign completed Firebase, Turso, discovery, enrichment, export or sender systems from scratch.
