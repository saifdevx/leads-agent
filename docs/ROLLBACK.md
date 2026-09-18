# Rollback

This change is additive at the application level and does not add a database migration.

If the free lead finder causes an issue:

1. Use Git to restore the last stable commit.
2. Keep the existing Firebase and Turso credentials unchanged.
3. Restart backend and frontend.
4. Run backend/frontend regression tests again.

Leads imported before a code rollback remain in Turso because this release uses the existing `lead_lists` and `leads` tables. A code rollback does not delete user data.

Do not delete Turso tables as part of a normal rollback.
