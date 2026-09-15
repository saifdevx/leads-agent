# Rollback — v0.1.0

Checkpoint 1 is the first code release, so rollback means returning to the clean pre-code specification state.

## Before installing a later checkpoint

1. Keep `lead-platform-v0.1.0.zip` unchanged.
2. Commit the working version to Git.
3. Tag the commit as `v0.1.0`.
4. Never overwrite `.env` files with files from a new ZIP.

Example:

```bash
git add .
git commit -m "Checkpoint 1: foundation"
git tag v0.1.0
```

## Roll back from a future version

```bash
git checkout v0.1.0
```

Or restore the saved ZIP into a new directory and copy only your local `.env` values back manually.

## Important

Never roll back by restoring an old `.env`, credential file, user database or production data file from a ZIP. Release ZIPs intentionally do not contain those files.
