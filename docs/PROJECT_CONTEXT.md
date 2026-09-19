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
- Gmail OAuth sender connection
- Campaign preview + approval
- Persistent email queue
- Daily limits, sending windows, min interval
- Pause/resume/cancel
- Suppression filtering
- Separate email worker
- Basic campaign metrics

## UX philosophy

Keep the user experience centered on:

`Find leads → review leads → contact leads`

Do not expose infrastructure concepts unnecessarily.

## Next combined bundle after outreach validation

Do not split these into tiny checkpoints unless debugging requires it:

- Gmail reply synchronization
- automatic stop-on-reply
- multi-step follow-ups
- unsubscribe/opt-out workflow improvements
- campaign analytics
- admin overview/users/usage/system
- production deployment hardening
- final UX polish

## Important

The Gmail send scope is deliberately send-only in the current release. Reply synchronization will require an additional Gmail read/metadata scope later and may affect Google OAuth verification requirements.
