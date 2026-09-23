# Rollback

## Before updating

1. Push the current working source to GitHub.
2. For important data, create a Turso backup/branch before migration `004_admin_operations`.
3. Preserve all existing secrets.

## Application rollback

Deploy/copy the previous known-good Git commit/source bundle.

Migration `004_admin_operations` is additive. Older application code can ignore the new role/worker/webhook/admin tables and columns, so normal code rollback does **not** require dropping them.

## Production rollback on Render

Redeploy the previous known-good commit for:
- static frontend
- API
- lead worker
- outreach worker

Workers and API should all use code from the same compatible commit during rollback.

## Data rollback

Only restore the Turso backup/branch if the database itself is damaged or an explicit data rollback is required.

Do not casually reverse migrations by deleting columns/tables in production.

## Secrets

Never rotate or replace `CREDENTIAL_ENCRYPTION_KEY` during rollback unless you intend to reconnect every encrypted provider/sender credential.

Do not overwrite:
- backend/.env
- frontend/.env
- Firebase Admin credentials
- Turso auth token
- Hostinger tokens
- provider keys
