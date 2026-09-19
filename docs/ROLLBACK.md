# Rollback

The previous stable code is already preserved in GitHub.

If this automated-discovery update causes a blocking issue:

1. Stop frontend/backend servers.
2. Restore the previous commit from Git.
3. Keep existing `.env` files and Turso data.
4. Restart the previous backend/frontend.

No database migration is introduced by this update, so rolling back source code does not require a schema rollback.

The new `CREDENTIAL_ENCRYPTION_KEY` may remain in `.env`; older code simply ignores it.

Do not delete provider connection rows manually unless intentionally removing saved BYOK credentials.
