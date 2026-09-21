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

Migration should apply `003_replies_followups` once, then report up to date.

## Existing product
- [ ] Firebase login/logout still works.
- [ ] Automated lead discovery still works.
- [ ] My Leads still loads and filters.
- [ ] Prospeo/Apollo enrichment still works.
- [ ] Excel/CSV import and export still work.
- [ ] Hostinger sender remains connected.
- [ ] Quick Send still works.
- [ ] Existing templates still load.
- [ ] Existing campaigns still load after migration.

## Responsiveness / cache
- [ ] Pause campaign changes UI immediately.
- [ ] Resume changes UI immediately.
- [ ] Cancel changes UI immediately.
- [ ] A failed action rolls the optimistic state back and shows an error.
- [ ] Bulk lead delete removes rows immediately.
- [ ] Refresh forces fresh server state.
- [ ] Logging out/in as another account does not show the previous account's cached data.

## Follow-ups
- [ ] Create campaign with initial + Follow-up 1.
- [ ] Create campaign with initial + two follow-ups.
- [ ] Initial message is the only message queued immediately after approval.
- [ ] Follow-up becomes queued only after prior step is sent.
- [ ] Delay is calculated relative to prior successful send.
- [ ] Cancel campaign cancels unsent sequence messages.
- [ ] All-day sending (`0 → 24`) works even before 9 AM.

## Replies
- [ ] Send to an address you control.
- [ ] Reply from the recipient address.
- [ ] Local **Sync Hostinger replies** detects it.
- [ ] Same provider UID is not duplicated.
- [ ] Multiple replies from the same lead count as one replied lead in campaign reply rate.
- [ ] Stop-on-reply cancels future unsent sequence messages.
- [ ] `unsubscribe` reply adds email to suppression list.
- [ ] `out of office` is classified correctly.
- [ ] `not interested` is classified correctly.
- [ ] interested wording is classified as interested.

## Campaign details / analytics
- [ ] Campaign details drawer opens.
- [ ] Sequence steps render in order.
- [ ] Initial/follow-up statuses are accurate.
- [ ] Sent count includes actually sent messages.
- [ ] Replied count represents unique leads that replied.
- [ ] Interested count is accurate.
- [ ] Reply rate is sensible.
- [ ] Failed message offers Retry.
- [ ] Retry does not bypass suppression or replied-lead safety checks.

## Production webhook readiness
- [ ] Local app works with `PUBLIC_API_URL` empty.
- [ ] Webhook setup clearly requires public HTTPS URL.
- [ ] Webhook rejects missing/incorrect bearer secret.
