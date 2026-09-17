# Version Handoff

PROJECT: Lead Platform
CURRENT VERSION: 0.3.0
CURRENT CHECKPOINT: 3 — Turso Database Foundation

## WHAT WORKS

- React/Vite/Tailwind application shell
- Firebase email/password and Google authentication
- Password reset/logout/session restoration
- FastAPI Firebase token verification
- Turso SQL-over-HTTP backend connection
- Versioned database migrations
- Automatic application-user sync into Turso
- Initial tables for users, lead lists, leads, provider connections, and jobs

## CURRENT STACK

- React 19.3
- Vite 8.3
- TypeScript 6.0
- Tailwind CSS 4.3
- Firebase JS SDK 12.19.0
- FastAPI 0.141.1
- Firebase Admin Python 7.5.0
- Turso Cloud SQL over HTTP through httpx 0.28.1

## DATA

Turso is now the application source of truth. Firebase remains authentication-only.

Current schema version: `001_initial`.

## AUTH + USER SYNC

Firebase verifies identity. The backend then upserts the verified user into Turso using `firebase_uid` as the stable user identifier.

## DO NOT CHANGE WITHOUT A CHECKPOINT

- Simplified four-item navigation
- Firebase as the authentication provider
- Turso as application persistence
- Server-side ownership/security boundary
- Free-first product direction
- Provider secrets never exposed to the frontend

## KNOWN LIMITATIONS

- Lead lists/leads tables exist but no lead CRUD/search UI uses them yet
- Provider connections table exists but credentials are not stored yet
- Jobs table exists but no worker runs yet
- No campaign/email tables yet
- No admin dashboard yet

## NEXT CHECKPOINT

Free/manual Lead Finder foundation: create a lead list, generate/store search intent, paste/import raw results, parse basic public lead data, and persist the results to Turso. Automated providers remain a later incremental step.

## ROLLBACK

Git tag `v0.2.0`.
