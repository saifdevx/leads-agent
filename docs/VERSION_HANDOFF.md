# Handoff

## Working features

- React/Vite application shell
- FastAPI API
- Firebase authentication and server verification
- Turso persistence and migrations
- User sync from Firebase to Turso
- Automated Serper search
- Automated Brave Search
- Encrypted BYOK provider connections
- Optional Gemini structured extraction
- Optional OpenAI structured extraction
- Public website contact crawling
- Search progress jobs
- Batched Turso lead writes
- Manual search-result import fallback
- Lead-list persistence
- My Leads table

## Provider strategy

Current discovery providers:

```text
Serper       Primary Google-style search
Brave        Independent web-search coverage
Gemini       Optional AI cleanup
OpenAI       Optional AI cleanup
```

Future enrichment layer:

```text
Prospeo      Verified email / person enrichment
Apollo       Decision-maker search + enrichment
```

Paid enrichment should only run after free/public discovery so credits are spent on missing information rather than data already found.

## Private local configuration

Environment variable names only:

```text
VITE_API_URL
VITE_FIREBASE_API_KEY
VITE_FIREBASE_AUTH_DOMAIN
VITE_FIREBASE_PROJECT_ID
VITE_FIREBASE_APP_ID
VITE_FIREBASE_MESSAGING_SENDER_ID
VITE_FIREBASE_STORAGE_BUCKET
APP_NAME
APP_VERSION
APP_ENV
CORS_ORIGINS
LOG_LEVEL
FIREBASE_PROJECT_ID
FIREBASE_CREDENTIALS_PATH
FIREBASE_SERVICE_ACCOUNT_JSON
TURSO_DATABASE_URL
TURSO_AUTH_TOKEN
TURSO_TIMEOUT_SECONDS
CREDENTIAL_ENCRYPTION_KEY
```

Never record credential values in handoff documents.

## Do not change casually

- Firebase UID as user ownership key
- Turso as application database
- Server-side verification of Firebase tokens
- Server-side encrypted provider credentials
- Search-provider adapters behind backend APIs
- Database as the source of truth for leads/jobs

## Next logical product layer

Add verified enrichment providers (Prospeo/Apollo) after real-world automated discovery quality is tested with several niches.
