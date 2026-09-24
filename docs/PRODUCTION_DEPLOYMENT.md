# Lead Gen — Zero-Cost Render Deployment

The default deployment is intentionally designed around Render's Free web-service
and Static Site tiers.

## Architecture

```text
Render Static Site (free)
        |
        v
Render FastAPI Web Service (free)
        |
        +-- embedded lead worker
        +-- embedded outreach worker
        |
        +-- Turso
        +-- Firebase
        +-- Search / AI / enrichment providers
        +-- Hostinger Mail
```

## Trade-off of the free mode

Render Free web services sleep after a period without inbound traffic. Lead Gen stores
pending discovery, enrichment and outreach work durably in Turso, so it is not lost,
but scheduled work can be delayed until the API wakes again.

While a user has Lead Gen open, the frontend sends a lightweight health check every
few minutes. This keeps the API responsive during active sessions and allows embedded
workers to process the queue.

For personal use/testing, this keeps Render compute at $0. For strict always-on
scheduling, use `render-scaled.yaml` later.

## 1. Push the repository

Push the tested code to GitHub.

## 2. Create a Render Blueprint

In Render:

1. New -> Blueprint
2. Select the repository
3. Use the repository's default `render.yaml`
4. Apply the Blueprint

It creates:

- `lead-gen-web` — free Static Site
- `lead-gen-api` — free Python Web Service

## 3. API environment variables

Configure:

```text
CORS_ORIGINS=https://YOUR-FRONTEND.onrender.com
FRONTEND_APP_URL=https://YOUR-FRONTEND.onrender.com
PUBLIC_API_URL=https://YOUR-API.onrender.com
ADMIN_EMAILS=YOUR_ADMIN_EMAIL

FIREBASE_PROJECT_ID=...
FIREBASE_SERVICE_ACCOUNT_JSON=...

TURSO_DATABASE_URL=...
TURSO_AUTH_TOKEN=...
CREDENTIAL_ENCRYPTION_KEY=...
```

Optional Gmail variables can stay blank if Hostinger is your sender.

The Blueprint already sets:

```text
APP_ENV=production
BACKGROUND_JOBS_MODE=embedded
EMBEDDED_WORKERS=true
WORKER_POLL_SECONDS=3
WORKER_LEASE_SECONDS=300
USER_ACCESS_CACHE_SECONDS=60
QUICK_SEND_PER_MINUTE=6
```

## 4. Frontend environment variables

Set:

```text
VITE_API_URL=https://YOUR-API.onrender.com
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_APP_ID=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
```

Vite values are build-time variables. Trigger a new frontend deployment after changing
them.

## 5. Firebase production domain

Add the Render frontend hostname to Firebase Authentication authorized domains.

## 6. Hostinger live replies

After `PUBLIC_API_URL` is set, open:

Outreach -> Senders -> your Hostinger sender -> Enable live replies

This registers the public HTTPS webhook so replies can reach Lead Gen even while the
browser is closed. The incoming webhook also wakes a sleeping free API.

## 7. Smoke test

1. Sign in.
2. Find a small lead list.
3. Open My Leads.
4. Export an XLSX.
5. Send a Quick Send email to yourself.
6. Send a 1-recipient campaign.
7. Reply and verify Inbox/stop-on-reply.
8. Open Admin and check System.

## Optional always-on architecture

`render-scaled.yaml` preserves separate API, lead worker and outreach worker services.
Use it only when delayed jobs caused by free-service sleep are no longer acceptable.
