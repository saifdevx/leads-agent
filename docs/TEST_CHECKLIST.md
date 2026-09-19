# Test Checklist

## Regression

Frontend:
```powershell
npm install --include=optional
npm run check
npm run test
npm run build
```

Backend:
```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
python -m app.db.migrate
```

Migration should apply `002_outreach` once, then report up to date on the second run.

## Existing lead engine
- [ ] Firebase login/logout still works.
- [ ] Find Leads automated discovery still works.
- [ ] Serper/Brave settings still load.
- [ ] Gemini/OpenAI settings still load.
- [ ] Prospeo/Apollo enrichment still works.
- [ ] Excel/CSV export still works.

## Templates
- [ ] Create template.
- [ ] Edit template.
- [ ] Delete template.
- [ ] Variables render in preview.
- [ ] Unknown variables do not leak literally into emails.

## Gmail connection
- [ ] Gmail API enabled in Google Cloud.
- [ ] OAuth client uses exact local redirect URI.
- [ ] Connect Gmail opens Google consent.
- [ ] Successful callback returns to Outreach > Senders.
- [ ] Sender email appears connected.
- [ ] Gmail tokens never appear in frontend or logs.
- [ ] Disconnect removes sender.

## Campaign safety
- [ ] Select one test lead from My Leads and click Outreach.
- [ ] Draft creation does not send anything.
- [ ] Preview shows correct recipient/subject/body.
- [ ] Suppressed addresses are skipped.
- [ ] Missing email addresses are skipped.
- [ ] Campaign sends only after explicit approval.
- [ ] Pause stops worker from taking new queued messages.
- [ ] Resume continues.
- [ ] Cancel prevents remaining draft/queued messages.
- [ ] Same lead cannot be inserted twice into one campaign.

## Worker
- [ ] Without worker, approved messages remain queued safely.
- [ ] `python -m app.outreach.worker` starts cleanly.
- [ ] First test uses an email address you control.
- [ ] Daily limit is respected.
- [ ] Sending window is respected.
- [ ] Minimum interval is respected.
- [ ] Successful Gmail send increments sent count.
- [ ] Failed send is marked failed and not silently retried.
- [ ] Completed campaign moves to completed when no active messages remain.
