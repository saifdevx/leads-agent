# Replies + Follow-ups + Campaign Analytics

This bundle is the first of the final three large product bundles. It focuses on outreach automation while also making common actions feel faster.

## 1. Update safely

Before replacing files, push the currently working project to GitHub.

Copy this complete source over the current project while preserving:

- `.git/`
- `backend/.env`
- `backend/.venv/`
- `frontend/.env`
- `frontend/package-lock.json`
- `frontend/node_modules/`

Do **not** regenerate `CREDENTIAL_ENCRYPTION_KEY`.

## 2. Environment

Keep all existing Firebase, Turso, provider, Hostinger, and optional Gmail configuration.

The only new environment variable is:

```env
# Leave blank during local development.
# After the API is publicly deployed, set this to its HTTPS base URL.
PUBLIC_API_URL=
```

Example after deployment:

```env
PUBLIC_API_URL=https://lead-platform-api.onrender.com
```

This is used to create a real-time Hostinger reply webhook. Local development does not need it because the Reply Inbox has a manual **Sync Hostinger replies** action.

## 3. Apply migration

This bundle adds migration:

`003_replies_followups`

It adds campaign sequence/reply fields, sequence steps, inbound replies, and upgrades `email_messages` to support multiple messages per lead/campaign.

Run:

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
python -m app.db.migrate
```

Expected on first run:

```text
Applied migrations:
  - 003_replies_followups
```

Run it a second time. Expected:

```text
Database schema is already up to date.
```

Because this migration restructures `email_messages`, keep the previous Git source state and a Turso backup/branch before applying it to important production data.

## 4. Backend regression

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```

Then start the API:

```powershell
uvicorn app.main:app --reload --port 8000
```

## 5. Frontend regression

```powershell
cd D:\Leads-Agent\leads-agent\frontend
npm install --include=optional
npm run check
npm run test
npm run build
npm run dev
```

## 6. Worker

Keep the email worker running:

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
python -m app.outreach.worker
```

## 7. Test a follow-up sequence

Use test addresses you control.

1. Create an initial template.
2. Create one or two follow-up templates.
3. Select a test lead in **My Leads** and click **Outreach**.
4. In the campaign form, keep **Stop on reply** enabled.
5. Enable Follow-up 1 and select a follow-up template + delay.
6. Optionally enable Follow-up 2.
7. Preview the campaign.
8. Approve it.
9. Confirm the initial email sends.

For a fast local test, choose a short test delay offered by the UI if present; for real outreach use sensible hour/day delays.

Follow-ups remain `waiting` until the previous sequence step is successfully sent. They are then scheduled relative to that send time.

## 8. Test replies locally

Real-time Hostinger webhooks need a public HTTPS API URL, so local development uses manual sync.

1. Send the initial message to an inbox you control.
2. Reply from the recipient address.
3. Open **Outreach → Inbox**.
4. Click **Sync Hostinger replies**.
5. Confirm the reply appears.
6. Confirm the campaign reply count increases.
7. Confirm future follow-ups for that lead are cancelled when **Stop on reply** is enabled.

Try reply text such as:

- `Yes, tell me more` → interested
- `Please unsubscribe me` → unsubscribe + suppression
- `I am out of office until Monday` → out of office
- `Not interested` → not interested

## 9. Campaign details

Open a campaign's **Details** view to inspect:

- sent/replied/interested metrics
- reply rate
- sequence steps
- initial and follow-up message statuses
- inbound replies
- failed messages
- safe manual Retry action for failed messages

## 10. Faster UI behavior

This bundle intentionally improves perceived speed:

- Pause/resume/cancel/delete update immediately and roll back if the API fails.
- Bulk lead delete updates immediately and rolls back on failure.
- Leads/lists/templates/senders/campaigns/replies use short-lived in-browser response caches.
- Mutations invalidate affected cache groups.
- Sending campaigns still auto-refresh so server truth eventually replaces optimistic state.

The cache is only a UI performance layer. Turso remains the source of truth.

## 11. Production real-time webhook (later bundle)

After the API is deployed to HTTPS:

1. Set `PUBLIC_API_URL`.
2. Restart the backend.
3. Open **Outreach → Senders**.
4. Enable/configure the Hostinger reply webhook for the connected Hostinger sender.

The backend stores Hostinger's webhook secret encrypted inside the existing sender credentials and validates incoming webhook calls before recording replies.

Do not expose that webhook secret.
