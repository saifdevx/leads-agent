# Test Checklist — Admin / Production / Performance

## 1. Automated regression

Backend:
```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
python -m app.db.migrate
```

First migration run after update should apply:

```text
004_admin_operations
```

Run it again. Expected:

```text
Database schema is already up to date.
```

Frontend:
```powershell
cd D:\Leads-Agent\leads-agent\frontend
npm install --include=optional
npm run check
npm run test
npm run build
npm run dev
```

## 2. Existing product regression

- [ ] Firebase login/logout works.
- [ ] Find Leads opens.
- [ ] Automated lead discovery works locally with `BACKGROUND_JOBS_MODE=inline`.
- [ ] My Leads loads lists + leads.
- [ ] Lead search/filter/select works.
- [ ] Bulk delete remains optimistic and rolls back on failure.
- [ ] Enrichment starts and completes.
- [ ] Excel/CSV import works.
- [ ] Excel/CSV export works.
- [ ] Outreach loads campaigns/templates/senders/replies.
- [ ] Hostinger sender remains connected.
- [ ] Quick Send works.
- [ ] Campaign create/preview/approve works.
- [ ] Pause/resume/cancel reacts immediately.
- [ ] Outreach worker sends queued messages.
- [ ] Follow-ups and reply sync still work.

## 3. Admin setup

Add your own Firebase account email to backend `.env`:

```env
ADMIN_EMAILS=your@email.com
```

Restart backend, sign out/in (or refresh the verified session).

- [ ] Admin item appears only for the configured admin.
- [ ] Normal users do not see Admin.
- [ ] Direct `/api/v1/admin/*` access by a normal user returns 403.

## 4. Admin overview

- [ ] User count loads.
- [ ] Lead/list counts load.
- [ ] Sent/reply counts load.
- [ ] Failed/running job counts load.
- [ ] Search-call / website / enrichment activity appears.
- [ ] Provider/sender connection totals load.
- [ ] Manual Refresh works.

## 5. User controls

Use a disposable test account if possible.

- [ ] Suspend user updates UI immediately.
- [ ] Suspended user receives 403 on protected API requests.
- [ ] Reactivate user works.
- [ ] Admin cannot suspend their own admin account.
- [ ] Lead/campaign counts do not reset to zero after status action.

## 6. Jobs

- [ ] Jobs tab lists pending/running/failed/complete jobs.
- [ ] Failed retryable job shows Retry.
- [ ] Retry returns job to pending.
- [ ] Non-failed/non-retryable job cannot be retried through the endpoint.

## 7. Performance checks

With browser Network panel open:

- [ ] Initial My Leads load uses `/api/v1/leads/snapshot` rather than separate leads + lists requests.
- [ ] Initial Outreach load uses `/api/v1/outreach/snapshot` rather than four separate dashboard requests.
- [ ] Duplicate simultaneous provider GETs are reduced/deduplicated.
- [ ] Pause/resume/delete gives immediate visual feedback.
- [ ] Forced Refresh still loads fresh server truth.
- [ ] Logging out/in as another account does not expose previous user's cached data.

## 8. Local workers

Normal local setup:
- API
- frontend
- outreach worker

Local lead discovery can remain inline.

Optional worker-mode test:

Set temporarily:
```env
BACKGROUND_JOBS_MODE=worker
```

Start:
```powershell
python -m app.jobs.worker
```

- [ ] Find Leads creates a pending job.
- [ ] Lead worker claims it.
- [ ] Browser refresh does not stop it.
- [ ] Job completes and leads appear.

Return to `BACKGROUND_JOBS_MODE=inline` for normal local development unless intentionally testing worker mode.

## 9. Production smoke test

After Render deployment:

- [ ] `/health` is healthy.
- [ ] Frontend login works on Render domain.
- [ ] Admin → System says production / worker mode.
- [ ] lead-worker heartbeat is healthy.
- [ ] outreach-worker heartbeat is healthy.
- [ ] Discovery continues after closing browser.
- [ ] Hostinger live webhook can be enabled.
- [ ] Controlled reply appears automatically without manual sync.
