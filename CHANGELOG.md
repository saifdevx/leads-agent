# Changelog

## Replies, follow-ups, analytics & responsiveness update

- Added campaign follow-up sequences using separate templates and configurable delays.
- Added stop-on-reply, enabled by default for new campaigns.
- Added Hostinger reply synchronization for local development.
- Added webhook-ready Hostinger `message.received` support for production HTTPS deployment.
- Added Reply Inbox with classifications: interested, reply, not interested, unsubscribe, and out of office.
- Unsubscribe replies now add the sender address to the suppression list automatically.
- Future queued/waiting messages are cancelled when stop-on-reply is enabled.
- Added campaign detail drawer with sequence steps, per-message status, replies, reply rate, and follow-up counts.
- Added safe manual retry for failed messages.
- Added campaign reply analytics cards and per-campaign reply counts.
- Added optimistic campaign pause/resume/cancel/delete so controls respond immediately instead of waiting on Turso round trips.
- Added optimistic bulk lead deletion with rollback on backend failure.
- Added short-lived authenticated frontend response caching for leads, lead lists, templates, senders, campaigns, details, and replies.
- Mutations invalidate relevant caches automatically.
- Added subtle page/card/row/drawer/button animations with `prefers-reduced-motion` support.
- Added migration `003_replies_followups`.
- Fixed the all-day sending window so `0 → 24` truly allows sending at all hours.
- Added regression coverage for follow-up scheduling, stop-on-reply, unsubscribe suppression, duplicate replies, unique campaign reply counts, all-day sending, and scoped bulk lead deletion.
