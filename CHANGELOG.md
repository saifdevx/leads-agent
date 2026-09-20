# Changelog

## Productivity & Outreach update

- Added Quick Send for one-off/testing emails.
- Added Excel (.xlsx) and CSV lead-sheet import from My Leads.
- Added automatic header mapping for common lead columns.
- Added optional campaign sending windows. When disabled, approved campaigns can begin immediately.
- Reduced supported campaign interval to 20 seconds minimum; default is now 30 seconds.
- Added 20/30/45/60/90/120 second interval choices.
- Added automatic Outreach refresh while campaigns are sending plus a manual Refresh button.
- Added campaign progress bars and clearer schedule/interval details.
- Added campaign deletion for non-sending campaigns so test campaigns can be cleaned up.
- Added suppression enforcement to Quick Send.
- Worker now checks the queue every 5 seconds for more responsive testing.
- Added lead-file import tests, all-day campaign tests, campaign-delete tests, suppression tests and sender-service tests.
- No existing Turso migration is required for this update.
