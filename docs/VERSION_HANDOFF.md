# Handoff

## Working features

- React/Vite application shell
- FastAPI API
- Firebase authentication and server verification
- Turso persistence and migrations
- User sync from Firebase to Turso
- Free lead search-plan generation
- Manual search-result import
- Public contact extraction and dedupe
- Lead-list persistence
- My Leads table

## Current providers

No external search/enrichment provider is required for the free flow.

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
```

Never store the values in handoff documents or Git.

## Next logical feature

Automated free/search-provider integration (for example Brave/Serper adapters) and website crawling, only after the manual free workflow is validated with real lead searches.
