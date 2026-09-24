# Gmail Outreach Setup

This release adds templates, Gmail OAuth senders, draft campaigns, approval, a persistent email queue, daily limits, sending windows, pause/resume/cancel, suppression, and basic campaign metrics.

## 1. Google Cloud / Gmail API

Use a Google Cloud project you control.

1. Enable **Gmail API**.
2. Configure the OAuth consent screen.
3. Create an **OAuth client ID** of type **Web application**.
4. For local development, add this exact Authorized redirect URI:

   `http://localhost:8000/api/v1/outreach/gmail/callback`

5. If your OAuth consent screen is in Testing mode, add the Gmail accounts you will connect as test users.

The app asks only for identity information plus the Gmail `gmail.send` scope. It does not request mailbox read access in this release.

## 2. Backend .env

Keep all existing Firebase, Turso, and encryption values. Add:

```env
FRONTEND_APP_URL=http://localhost:5173
GMAIL_OAUTH_CLIENT_ID=YOUR_GOOGLE_OAUTH_CLIENT_ID
GMAIL_OAUTH_CLIENT_SECRET=YOUR_GOOGLE_OAUTH_CLIENT_SECRET
GMAIL_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/outreach/gmail/callback
```

Never commit the client secret.

## 3. Migration

Run:

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
python -m app.db.migrate
```

Expected new migration:

`002_outreach`

It creates:
- email_templates
- sender_connections
- campaigns
- email_messages
- suppression_entries

## 4. Start backend + frontend

Backend:

```powershell
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd D:\Leads-Agent\leads-agent\frontend
npm run dev
```

## 5. Start the email worker

Sending is intentionally handled by a separate durable queue worker rather than the browser request.

Open a third terminal:

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
python -m app.outreach.worker
```

If the worker is not running, approved messages remain safely queued.

## 6. First safe test

1. Open Outreach > Templates and create a template.
2. Open Outreach > Senders and connect Gmail.
3. In My Leads, select **one lead whose email you control**.
4. Click Outreach.
5. Create a campaign with a low daily limit.
6. Review the preview.
7. Click **Approve & queue** only when you intend to send.
8. Keep the worker terminal running.

Do not start with a bulk campaign.

## 7. Sending controls

Each campaign supports:
- explicit approval before sending
- daily limit (1–200)
- sending-window start/end hours
- browser-detected IANA timezone
- minimum interval of at least 30 seconds
- pause
- resume
- cancel
- suppression filtering
- duplicate prevention inside one campaign

The worker does not automatically retry uncertain Gmail send failures, reducing duplicate-send risk if a timeout occurs after Gmail accepted a message.

## 8. Production

For Render production deployment, the API service needs the Gmail OAuth variables and the production callback URL must be registered in Google Cloud.

Email sending also needs an always-on **Background Worker** with:

- Root directory: `backend`
- Start command: `python -m app.outreach.worker`
- Same Firebase/Turso/encryption/Gmail environment variables as the backend API

The default free Render deployment runs the outreach worker inside the API process while the service is awake. Scheduled messages can be delayed if the free API is asleep; the optional scaled deployment uses a separate always-on worker.
