# Changelog

## Hostinger Mail sender support

- Added Hostinger Agentic Mail API token connection
- Validates tokens against `GET /api/v1/me` and discovers allowed mailboxes
- Supports tokens scoped to one or multiple mailboxes
- Encrypts Hostinger API tokens with the existing credential encryption key
- Added Hostinger sending to the existing outreach worker
- Existing campaign approval, daily limits, sending windows, minimum interval, suppression, pause/resume/cancel behavior remain unchanged
- Gmail remains available as an optional sender
- Added Hostinger-specific backend tests and setup documentation
- No database migration required; the existing generic `sender_connections` table is reused

## Combined Outreach MVP

Added a larger feature bundle to accelerate the project:

- Email template CRUD with personalization variables
- Gmail OAuth sender connection (server-side authorization)
- Encrypted Gmail OAuth token storage
- Select leads in My Leads and hand them directly to Outreach
- Draft campaign creation and message preview
- Explicit human approval gate before any external send
- Persistent email queue stored in Turso
- Separate background email worker
- Gmail API `messages.send` integration
- Daily sender limits
- Sending-hour windows and timezone handling
- Minimum send interval
- Pause, resume, and cancel controls
- Suppression table/filtering
- Duplicate-send protection inside campaigns
- Basic outreach metrics and campaign history
- New additive database migration `002_outreach`

Not included yet: reply synchronization, automatic stop-on-reply, multi-step follow-ups, advanced admin controls, and production deliverability analytics. These are planned as a later combined polish bundle after the core sending path is validated.
