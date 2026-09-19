# Changelog

## Automated lead discovery + BYOK integrations

### Added
- Fully automated lead search through Serper and Brave Search.
- User-owned search-provider API keys.
- User-owned Gemini and OpenAI API keys.
- Server-side Fernet encryption for provider credentials.
- Provider validation/connect/disconnect endpoints.
- Functional Settings integration screen.
- Background search jobs with progress polling.
- Website contact-page crawling for missing public contact details.
- Optional AI structured extraction and relevance filtering.
- Automatic fallback to deterministic extraction if no AI provider is connected or AI extraction fails.
- Search-call and website-crawl limits to control cost/runaway work.
- Evidence post-validation for AI-returned emails, phones and URLs.
- Cost-aware Smart search mode: Serper first, Brave fallback.
- Batched Turso writes for lead imports.
- Reduced Turso latency by avoiding repeated user-sync/provider lookups on every protected API call.
- Provider credentials are snapshotted once per discovery job instead of re-reading Turso for every query.
- Manual paste/import kept as a fallback mode.

### Changed
- Find Leads now defaults to one-click automatic discovery.
- Search queries prioritize the proven Instagram/Gmail-style discovery patterns.
- Weak social-only results do not count toward the requested lead target unless a practical contact path is found.
- My Leads receives automatically discovered records from connected providers.

### Preserved
- Firebase authentication.
- Turso persistence and existing schema.
- Manual lead import.
- Existing lead-list and lead-table behavior.
