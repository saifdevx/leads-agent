# Lead Platform — Current Handoff

## Completed

- React/FastAPI foundation
- Firebase authentication
- Turso persistence
- Automated Serper/Brave lead discovery
- Website crawling and quality filtering
- Gemini/OpenAI BYOK
- Prospeo/Apollo enrichment BYOK
- Excel/CSV export
- Email templates
- Hostinger Agentic Mail sender connection (recommended)
- Optional Gmail OAuth sender connection
- Campaign preview + explicit approval
- Persistent email queue
- Daily limits, sending windows, minimum interval
- Pause/resume/cancel
- Suppression filtering
- Separate email worker
- Basic campaign metrics

## UX philosophy

Keep the user experience centered on:

`Find leads → review leads → contact leads`

Do not expose infrastructure concepts unnecessarily.

## Current sender direction

Hostinger Agentic Mail is now the recommended sender because it uses a simple API token and exposes a full mailbox API. User tokens are validated through `GET /api/v1/me`, the allowed mailbox is discovered, and the token is encrypted in Turso using `CREDENTIAL_ENCRYPTION_KEY`.

Gmail remains optional and may be configured later.

## Next combined bundle after one real Hostinger send is validated

Do not split these into tiny checkpoints unless debugging requires it:

- Hostinger incoming-message webhook integration after a public HTTPS backend exists
- reply detection and automatic stop-on-reply
- multi-step follow-ups
- unsubscribe/opt-out workflow improvements
- campaign analytics
- admin overview/users/usage/system
- production deployment hardening
- final UX polish

## Important

Hostinger webhooks require a publicly accessible HTTPS endpoint. Local development should prove the send path first. After deployment, use Hostinger `message.received` webhooks for real-time reply handling instead of polling where possible.
