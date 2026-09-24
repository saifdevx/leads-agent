# Lead Gen — Final Release Checklist

## Branding / UX
- [ ] Lead Gen logo appears in sidebar and authentication
- [ ] Browser favicon uses the Lead Gen mark
- [ ] No old "Lead Platform" branding remains
- [ ] Desktop navigation works
- [ ] Mobile navigation works
- [ ] Loading, empty, success and error states are readable
- [ ] Buttons show immediate feedback

## Authentication
- [ ] Email/password sign-in
- [ ] Google sign-in
- [ ] Logout
- [ ] Session refresh
- [ ] Protected API returns 401 while logged out

## Lead discovery
- [ ] Automatic Serper/Brave search works
- [ ] Website crawling works
- [ ] AI cleanup works or deterministic fallback works
- [ ] Deduplication/merge works
- [ ] Lead target stops within configured budget

## Lead database
- [ ] Search/filter works
- [ ] Bulk delete feels immediate
- [ ] Excel/CSV upload works
- [ ] XLSX export works
- [ ] CSV export works

## Enrichment
- [ ] Prospeo connection
- [ ] Apollo connection
- [ ] Smart enrichment
- [ ] Verified-email status persists

## Outreach
- [ ] Hostinger sender connects
- [ ] Quick Send works
- [ ] Template create/edit/delete
- [ ] Campaign preview
- [ ] Explicit approval
- [ ] Pause/resume/cancel
- [ ] 20/30 second intervals work
- [ ] Sending hours optional
- [ ] Follow-up steps schedule correctly
- [ ] Stop-on-reply
- [ ] Suppression/unsubscribe
- [ ] Reply inbox
- [ ] Analytics

## Admin
- [ ] Admin only visible to configured admins
- [ ] Overview loads
- [ ] User suspend/reactivate
- [ ] Failed-job retry
- [ ] System/worker health

## Security
- [ ] No `.env` or private JSON in Git
- [ ] Provider keys encrypted
- [ ] `CREDENTIAL_ENCRYPTION_KEY` backed up securely
- [ ] Production CORS contains only real frontend domains
- [ ] Hostinger webhook secret validation works
- [ ] Quick Send rate limit works
- [ ] Production API docs disabled
- [ ] Security headers present

## Performance
- [ ] `/api/v1/auth/me` completes normally
- [ ] My Leads uses snapshot request
- [ ] Outreach uses snapshot request
- [ ] Optimistic Pause/Delete/Resume feels immediate
- [ ] No duplicate initial GET requests
- [ ] Transient GET 502/503/504 retries once

## Deployment
- [ ] `render.yaml` creates free Static Site + free Web Service
- [ ] Migration runs on API startup
- [ ] Firebase production domain configured
- [ ] Hostinger webhook configured
- [ ] End-to-end production smoke test complete
