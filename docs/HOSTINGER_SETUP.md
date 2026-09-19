# Hostinger Mail setup

This build supports Hostinger Agentic Mail as a first-class sender. Gmail remains optional.

## 1. Create a Hostinger API token

In hPanel:

`Emails → your domain → Agentic mail → API access → Create API token`

Prefer **Selected mailboxes** and choose only the sender mailbox you plan to use.

Copy the token when Hostinger shows it. Do not put it in `.env`, source code, or Git.

## 2. Connect it inside Lead Platform

Start the normal backend/frontend, then open:

`Outreach → Senders → Hostinger Mail`

Paste the token.

- If the token has access to exactly one mailbox, leave **Mailbox email** empty.
- If the token has access to multiple mailboxes, enter the exact mailbox you want, e.g. `sales@example.com`.
- Sender name is optional.

Click **Connect Hostinger**.

The backend validates the token using Hostinger `GET /api/v1/me`, discovers the mailbox resource ID, encrypts the token with the existing `CREDENTIAL_ENCRYPTION_KEY`, and stores only encrypted credentials in Turso.

## 3. Start the outreach worker

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
python -m app.outreach.worker
```

The worker supports both Hostinger and Gmail senders.

## 4. Safe first send

Use an email address that you personally control.

1. Make sure that address exists as a lead.
2. Select one lead in **My Leads**.
3. Click **Outreach**.
4. Choose a template.
5. Choose the Hostinger sender.
6. Preview the campaign.
7. Click **Approve & queue** only when the preview is correct.
8. Keep the outreach worker running.

The Hostinger Mail API sends through:

`POST /api/v1/mailboxes/{mailboxResourceId}/send`

The campaign's daily limit, sending window, minimum interval, suppression list, and duplicate protection still apply.

## 5. Gmail is optional

You can leave all Gmail OAuth variables empty if you only use Hostinger. The Gmail Connect button will simply report that Gmail is not configured if clicked.

## 6. Replies / webhooks

Hostinger supports `message.received` webhooks, but Hostinger requires a publicly accessible HTTPS webhook URL. We will wire reply handling after the backend is deployed (or when using a secure development tunnel). The current local milestone proves sending first.

## Security reminders

Never share or commit:

- Hostinger API token
- `CREDENTIAL_ENCRYPTION_KEY`
- Turso token
- Firebase Admin credentials
- `.env`

If a Hostinger token is accidentally exposed, revoke it in hPanel and connect a new token.
