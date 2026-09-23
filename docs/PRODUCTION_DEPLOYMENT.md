# Production Deployment — Render

This bundle is designed to deploy the application as four logical services:

1. **lead-platform-web** — React/Vite static site
2. **lead-platform-api** — FastAPI web service
3. **lead-platform-lead-worker** — durable discovery/enrichment worker
4. **lead-platform-outreach-worker** — campaign send/follow-up worker

The exact service names may be changed, but keep the separation.

---

## Deployment profile choice

Two Render Blueprints are included:

### Recommended production — `render.yaml`

- frontend static site
- API web service
- dedicated lead/discovery worker
- dedicated outreach worker

This is the more reliable option because lead research and email scheduling cannot block each other and discovery jobs survive independently of API request processing.

### Lower-cost early deployment — `render-low-cost.yaml`

- frontend static site
- API web service with `BACKGROUND_JOBS_MODE=inline`
- dedicated outreach worker

This removes one paid worker. It is suitable for early personal/small-volume use, but lead discovery/enrichment is less resilient to API restarts/deploys. Upgrade to the full Blueprint when reliability or workload justifies it.

---

## 0. Before deployment

1. Push the fully tested code to GitHub.
2. Take a Turso backup/branch if the current data matters.
3. Locally run:

```powershell
cd backend
.venv\Scripts\Activate.ps1
pytest -q
python -m app.db.migrate

cd ..\frontend
npm run check
npm run test
npm run build
```

4. Confirm local Hostinger sending still works.
5. Keep the current `CREDENTIAL_ENCRYPTION_KEY` safe. Production must use the **same key** if you are using the same Turso database containing encrypted provider/sender credentials.

---

## 1. Create the Render Blueprint

In Render, create a Blueprint from the GitHub repository containing `render.yaml`.

The Blueprint defines:
- the static frontend
- API web service
- lead worker
- outreach worker

The API has a pre-deploy migration command:

```text
python -m app.db.migrate
```

Do not manually run production schema edits after this unless intentionally performing a migration recovery.

---

## 2. API environment values

Set these on `lead-platform-api`.

```env
APP_ENV=production
APP_VERSION=0.11.0
LOG_LEVEL=INFO
BACKGROUND_JOBS_MODE=worker
WORKER_POLL_SECONDS=3
WORKER_LEASE_SECONDS=300
USER_ACCESS_CACHE_SECONDS=30

CORS_ORIGINS=https://YOUR-FRONTEND.onrender.com
FRONTEND_APP_URL=https://YOUR-FRONTEND.onrender.com
PUBLIC_API_URL=https://YOUR-API.onrender.com
ADMIN_EMAILS=YOUR_FIREBASE_LOGIN_EMAIL

FIREBASE_PROJECT_ID=...
FIREBASE_SERVICE_ACCOUNT_JSON=...

TURSO_DATABASE_URL=...
TURSO_AUTH_TOKEN=...
TURSO_TIMEOUT_SECONDS=15

CREDENTIAL_ENCRYPTION_KEY=...

GMAIL_OAUTH_CLIENT_ID=
GMAIL_OAUTH_CLIENT_SECRET=
GMAIL_OAUTH_REDIRECT_URI=https://YOUR-API.onrender.com/api/v1/outreach/gmail/callback
```

If you only use Hostinger Mail, Gmail values can stay empty.

### Firebase service account

For production, prefer `FIREBASE_SERVICE_ACCOUNT_JSON` rather than a local credentials-file path.

Paste the complete service-account JSON as the secret environment value. Never commit it.

---

## 3. Lead worker environment

Set on `lead-platform-lead-worker`:

```env
APP_ENV=production
APP_VERSION=0.11.0
LOG_LEVEL=INFO
WORKER_POLL_SECONDS=3
WORKER_LEASE_SECONDS=300

TURSO_DATABASE_URL=...
TURSO_AUTH_TOKEN=...
TURSO_TIMEOUT_SECONDS=15
CREDENTIAL_ENCRYPTION_KEY=...
```

The lead worker does not need Firebase credentials because it processes jobs already authorized/created by the API.

---

## 4. Outreach worker environment

Set on `lead-platform-outreach-worker`:

```env
APP_ENV=production
APP_VERSION=0.11.0
LOG_LEVEL=INFO

TURSO_DATABASE_URL=...
TURSO_AUTH_TOKEN=...
TURSO_TIMEOUT_SECONDS=15
CREDENTIAL_ENCRYPTION_KEY=...

GMAIL_OAUTH_CLIENT_ID=
GMAIL_OAUTH_CLIENT_SECRET=
```

For Hostinger-only sending, the Gmail settings can remain empty.

---

## 5. Frontend environment values

The Vite values are build-time environment variables on the static site:

```env
VITE_API_URL=https://YOUR-API.onrender.com

VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_APP_ID=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
```

If you change `VITE_API_URL`, redeploy the static site so Vite rebuilds with the new value.

---

## 6. Firebase production domain

In Firebase Authentication, add the Render frontend hostname to the authorized domains list.

Keep `localhost` for local development.

Test:
- email/password login
- Google sign-in if enabled
- logout
- browser refresh/session restore

---

## 7. Verify the production API

Open:

```text
https://YOUR-API.onrender.com/health
```

Expected:
- status `ok`
- environment `production`

Production API docs are intentionally disabled.

---

## 8. Verify workers through Admin

Sign in using the email configured in `ADMIN_EMAILS`.

Open:

**Admin → System**

You should eventually see:
- Database: Healthy
- Background mode: worker
- lead-worker: Online
- outreach-worker: Online
- Public API URL: Configured

A newly started worker can take ~20 seconds to publish its first heartbeat.

---

## 9. Enable real-time Hostinger replies

After `PUBLIC_API_URL` is set and your API is publicly reachable over HTTPS:

1. Open **Outreach → Senders**.
2. Find the Hostinger sender.
3. Click **Enable live replies**.
4. The backend registers the public Hostinger webhook and stores the one-time webhook secret encrypted with the sender credentials.
5. Confirm the sender shows **replies live**.

Then send an email to an address you control and reply to it. The reply should appear without manually pressing Sync.

---

## 10. Production smoke test

Run this small sequence before real use:

1. Login.
2. Find 5 leads.
3. Confirm discovery job continues even if browser is closed/refreshed.
4. Open My Leads and verify lists/leads load quickly.
5. Export CSV or Excel.
6. Quick Send one message to yourself.
7. Create a one-recipient campaign.
8. Confirm outreach worker sends it.
9. Reply to it.
10. Confirm webhook records reply and stops future follow-up.
11. Open Admin → System and verify both workers remain healthy.

---

## 11. Rollback

Application rollback:
- deploy the previous known-good Git commit.

Database:
- migration `004_admin_operations` is additive.
- do not manually delete the new columns/tables during a normal app rollback; older code can ignore them.
- if the database itself must be restored, use the backup/branch taken before deployment.

Secrets:
- never rotate `CREDENTIAL_ENCRYPTION_KEY` as part of an application rollback unless all stored encrypted credentials will be intentionally reconnected.
