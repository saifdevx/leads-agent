# Test Checklist — v0.2.0

Do not move to Checkpoint 3 until this list passes.

## A. Installation

- [ ] `npm install --include=optional` succeeds.
- [ ] Windows Rolldown binding remains installed (`Test-Path node_modules\@rolldown\binding-win32-x64-msvc` returns `True`).
- [ ] `pip install -r requirements.txt` succeeds.
- [ ] Real `.env` files are not tracked by Git.
- [ ] Firebase Admin service-account JSON is outside the repository.

## B. Automated frontend checks

From `frontend/`:

```powershell
npm run check
npm run test
npm run build
```

- [ ] TypeScript check passes.
- [ ] Vitest tests pass.
- [ ] Production Vite build succeeds.

## C. Automated backend checks

From `backend/` with `.venv` active:

```powershell
pytest -q
```

Expected suite includes both health and authentication tests.

- [ ] Health tests pass.
- [ ] `/api/v1/auth/me` requires authentication.
- [ ] Auth route test with a verified identity passes.
- [ ] Invalid-token behavior test passes.

## D. Backend runtime

Start:

```powershell
uvicorn app.main:app --reload --port 8000
```

- [ ] `http://127.0.0.1:8000/health` returns HTTP 200.
- [ ] Health payload reports version `0.2.0`.
- [ ] `http://127.0.0.1:8000/docs` loads.
- [ ] Unauthenticated `GET /api/v1/auth/me` returns HTTP 401.

## E. Frontend Firebase configuration behavior

Temporarily omit Firebase frontend configuration and run Vite.

- [ ] The app shows the Firebase configuration-required screen.
- [ ] It does not pretend authentication is available.

Restore the correct Firebase values and restart Vite.

## F. Email/password registration

- [ ] Register a new test account.
- [ ] Firebase Console shows the new user.
- [ ] The application verifies the Firebase token with the backend.
- [ ] The protected application shell opens.
- [ ] Refreshing the browser keeps the valid session.

## G. Logout and login

- [ ] Sign out from the top-right button.
- [ ] Protected UI disappears.
- [ ] Sign back in with email/password.
- [ ] Protected UI opens again only after backend verification.

## H. Password reset

- [ ] Enter the test email on the login screen.
- [ ] Click **Forgot password?**.
- [ ] UI confirms that the reset email was requested.
- [ ] Firebase sends the reset email (allow for spam/junk filtering).

## I. Google authentication

- [ ] Click **Continue with Google**.
- [ ] Google account selection opens.
- [ ] Google sign-in succeeds.
- [ ] Backend verifies the resulting Firebase ID token.
- [ ] Protected app opens.

## J. Server-side protection test

Stop the backend or intentionally remove the backend Firebase Admin credential, then sign in/retry verification.

- [ ] Frontend does not open protected application features.
- [ ] A clear verification/configuration error is shown.
- [ ] User can retry or sign out.

Restore backend credentials afterwards.

## K. Regression

- [ ] Sidebar still contains only Find Leads, My Leads, Outreach, Settings.
- [ ] Find Leads page renders correctly.
- [ ] Advanced options toggle works.
- [ ] API health status still works after authentication.
- [ ] Mobile navigation still opens/closes.
- [ ] No real lead search is enabled yet.

## Acceptance

Checkpoint 2 is accepted only after all relevant checks above pass.
