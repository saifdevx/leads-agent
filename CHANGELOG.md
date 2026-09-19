# Changelog

## Discovery quality and reliability update

### Security
- Gemini API keys are now sent in the `x-goog-api-key` header instead of the URL query string.
- Third-party `httpx` / `httpcore` INFO request logging is suppressed so provider request URLs are not printed to application logs.
- Gemini and OpenAI connections now validate an actual tiny generation request rather than only checking account/model listing access.
- Existing encrypted BYOK storage remains unchanged.

### Discovery quality
- Rejects obvious out-of-location results when a different US state is explicitly present.
- Rejects common template/demo, directory, job, course and other low-quality result types.
- Fixes false phone numbers caused by Facebook numeric IDs, dates and other digit strings.
- Company-name extraction now avoids generic page titles such as `Our Services` / `Contact Us` when better evidence is available.
- Website crawler now reads JSON-LD organization names and `og:site_name` metadata.
- Website crawler now uses `mailto:` and `tel:` links as stronger contact evidence.
- Website crawling can improve generic company names as well as missing contact details.
- Business identity now prefers company domain/social identity before email, reducing duplicate rows when an email is discovered later.
- Duplicate discoveries merge new contact details into the existing business instead of creating a second lead.
- AI extraction remains evidence-grounded and cannot save invented contact fields.

### Reliability and cost control
- Turso requests retry transient network/429/5xx failures before surfacing an outage.
- Frontend job polling retries temporary database 503 responses instead of stopping the running search.
- Polling interval increased to reduce database load.
- Automatic AI mode falls back from Gemini to OpenAI when both are connected, then to deterministic extraction if neither AI provider succeeds.
- Invalid AI provider credentials are marked as errors so a broken key is not repeatedly treated as healthy.
- Search budget is now adaptive and slightly larger for low-yield searches, while retaining a hard upper bound.
- Website crawl budget is adaptive and bounded.

### Preserved
- Firebase authentication.
- Turso schema and existing user data.
- Serper and Brave integrations.
- Manual search/import fallback.
- My Leads and export behavior.
- Existing encrypted provider credentials.
