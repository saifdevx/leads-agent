# Changelog

## 0.2.0 — Checkpoint 2: Firebase Authentication

### Added

- Firebase email/password registration and sign-in
- Google sign-in
- Password reset email
- Firebase auth session handling
- Protected frontend application shell
- Firebase setup-required screen
- Backend verification-error screen with retry/sign-out
- Firebase Admin server integration
- Protected `GET /api/v1/auth/me`
- Authentication tests and user-friendly error mapping
- `docs/FIREBASE_SETUP.md`

### Changed

- Application version updated to 0.2.0
- Header now displays authenticated account identity and sign-out control
- HTTP exceptions preserve authentication headers
- Render config includes Firebase build/runtime variables
- `.gitignore` protects common service-account JSON filenames
- Find Leads copy now reflects Checkpoint 2

### Preserved

- v0.1.1 Windows Rolldown fix
- Existing visual design system
- Simplified Find Leads / My Leads / Outreach / Settings navigation
- Health API and request IDs
- No lead-search functionality yet

## 0.1.1 — Checkpoint 1 hotfix

- Hardened Windows Rolldown optional dependency installation.
- Corrected version-aware health test behavior.

## 0.1.0 — Checkpoint 1 foundation

- Initial React/Vite frontend and FastAPI backend foundation.
