# Turso Setup — Checkpoint 3

Checkpoint 3 adds the application database while keeping Firebase as the authentication provider.

## 1. Create the database

The easiest path is the Turso dashboard. Create a database for this project and choose the **Turso Database** engine (not the legacy libSQL engine) when an engine choice is shown.

Suggested database name:

```text
leads-agent
```

If you prefer the Turso CLI, the equivalent command is:

```bash
turso db create leads-agent --tursodb
```

## 2. Get the database URL and token

From the database's connection/credentials area, copy:

```text
TURSO_DATABASE_URL
TURSO_AUTH_TOKEN
```

CLI equivalents:

```bash
turso db show --url leads-agent
turso db tokens create leads-agent
```

Treat the auth token like a password. Never place it in the frontend or commit it to Git.

## 3. Update `backend/.env`

Keep the Firebase values you already configured and add:

```env
APP_VERSION=0.3.0

TURSO_DATABASE_URL=turso://your-database-host.turso.io
TURSO_AUTH_TOKEN=your-private-token
TURSO_TIMEOUT_SECONDS=10
```

Do not add Turso secrets to `frontend/.env`.

## 4. Apply migrations

From `backend/` with the existing virtual environment active:

```powershell
python -m app.db.migrate
```

First run should report:

```text
Applied migrations:
  - 001_initial
```

Run it again:

```powershell
python -m app.db.migrate
```

Expected:

```text
Database schema is already up to date.
```

The migration creates only the small foundation needed now:

- `users`
- `lead_lists`
- `leads`
- `provider_connections`
- `jobs`
- `schema_migrations`

No campaigns/email tables are added yet.

## 5. Test automatic user sync

Start the backend and frontend normally, then sign in.

The existing `GET /api/v1/auth/me` flow now does two things:

1. verifies the Firebase ID token;
2. inserts or updates the corresponding `users` row in Turso.

The frontend response shape is unchanged, so Checkpoint 2's UI remains compatible.

## 6. Verify the row

Use the Turso database shell/dashboard query tool:

```sql
SELECT firebase_uid, email, display_name, status, last_login_at
FROM users;
```

Your signed-in Firebase user should appear once. Signing in again updates that same row instead of creating duplicates.

## Security

- `TURSO_AUTH_TOKEN` is backend-only.
- The frontend never connects directly to Turso.
- User ownership will be enforced server-side using the verified Firebase UID.
- `provider_connections.credentials_ciphertext` is reserved for a later provider-integration checkpoint; plaintext credentials are not stored in this release.
