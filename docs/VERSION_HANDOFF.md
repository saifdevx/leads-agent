# Version Handoff

PROJECT: Lead Platform
CURRENT VERSION: 0.2.0
CURRENT CHECKPOINT: 2 — Firebase Authentication

## WHAT WORKS

- React/Vite/Tailwind application shell
- FastAPI health/API foundation
- Windows Rolldown installation hardening from v0.1.1
- Firebase email/password registration and login
- Firebase Google sign-in
- Firebase password reset
- Firebase logout/session restoration
- Protected frontend shell
- Backend Firebase Admin token verification
- Protected `/api/v1/auth/me`

## CURRENT STACK

- React 19.3
- Vite 8.3
- TypeScript 6.0
- Tailwind CSS 4.3
- Firebase JS SDK 12.19.0
- FastAPI 0.141.1
- Firebase Admin Python 7.5.0

## DATA

No application database yet. Firebase is used only for authentication in this checkpoint.

## AUTH

Firebase Authentication. Frontend obtains Firebase ID token; FastAPI independently verifies it before protected application access.

## DO NOT CHANGE WITHOUT A CHECKPOINT

- Simplified 4-item user navigation
- Free-first product direction
- Frontend/backend separation
- Server-side auth verification requirement
- Secret handling rules

## KNOWN LIMITATIONS

- No Turso user record yet
- No role/admin claims yet
- No lead discovery yet
- No email verification enforcement
- No production deployment validation yet

## NEXT CHECKPOINT

Checkpoint 3 — Turso database foundation with a deliberately small schema tied to Firebase UID.

## ROLLBACK

Git tag `v0.1.1`.
