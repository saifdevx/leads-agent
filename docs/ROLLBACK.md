# Rollback

This bundle includes migration `003_replies_followups`, which restructures outreach tables. Treat source rollback and database rollback separately.

## Before update

1. Push the current working source to GitHub.
2. Keep all real `.env`/secret files outside Git as usual.
3. Before applying migration 003 to important data, create a Turso backup/branch/snapshot using the database tools available to your account.
4. Do not regenerate `CREDENTIAL_ENCRYPTION_KEY`.

## Source rollback

If the application code regresses before or after migration:

1. Stop frontend/backend/worker processes.
2. Restore the previous pushed Git commit.
3. Keep local `.env` files and secrets unchanged.
4. Reinstall dependencies only if the restored commit requires it.
5. Run frontend checks and `pytest -q`.

## Database rollback

Do **not** manually try to reverse migration 003 on production data by deleting columns/tables ad hoc.

If a true database rollback is required, restore the Turso backup/branch created before migration 003, then run the previous application commit against that restored database.

For local/test data, recreating the test database is also acceptable if the data is disposable.
