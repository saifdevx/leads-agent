# Changelog

## 0.3.0 — Checkpoint 3: Turso Database Foundation

### Added

- Turso SQL-over-HTTP database client
- Safe Turso value encoding/decoding and error classification
- Versioned migration runner (`python -m app.db.migrate`)
- Initial migration with `users`, `lead_lists`, `leads`, `provider_connections`, and `jobs`
- Automatic Firebase-user upsert into Turso during `/api/v1/auth/me`
- Turso runtime environment variables and Render placeholders
- Database client, migration, repository, and auth-sync tests
- `docs/TURSO_SETUP.md`

### Changed

- Application version updated to 0.3.0
- Auth verification now also persists the application user record
- Database errors are returned using safe public error messages
- Product shell copy reflects the database checkpoint

### Preserved

- Firebase email/password and Google authentication
- Password reset and logout/session behavior
- v0.1.1 Windows Rolldown fix
- Simplified four-item navigation
- Existing visual design system
- No lead-search or email-sending functionality yet

## 0.2.0 — Checkpoint 2: Firebase Authentication

- Added Firebase Authentication and server-side token verification.

## 0.1.1 — Checkpoint 1 hotfix

- Hardened Windows Rolldown optional dependency installation.
- Corrected version-aware health test behavior.

## 0.1.0 — Checkpoint 1 foundation

- Initial React/Vite frontend and FastAPI backend foundation.
