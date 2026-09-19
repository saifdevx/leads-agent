# Rollback

If this update causes a regression:

1. Stop frontend/backend processes.
2. Use Git to restore the previous pushed working commit.
3. Keep local `.env` files and secrets unchanged.
4. Do not regenerate `CREDENTIAL_ENCRYPTION_KEY`.
5. Reinstall dependencies only if the restored commit requires it.
6. Run frontend checks and `pytest -q` again.

No database migration is included in this update, so reverting source code does not require a schema rollback.
