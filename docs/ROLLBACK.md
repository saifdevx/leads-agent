# Rollback — v0.2.0

Checkpoint 1 stable release `v0.1.1` is the rollback point.

## Before applying v0.2.0

Confirm:

```powershell
git status
git tag --list
```

You should already have `v0.1.1` pushed to GitHub.

## Roll back source code

If v0.2.0 cannot be accepted, return to the previous stable tag using your normal Git workflow. One safe approach is to create a rollback branch first:

```powershell
git switch -c rollback-v0.1.1 v0.1.1
```

Or restore `main` to the known-good source only when you intentionally want to discard later changes.

## Local dependencies after rollback

Frontend `package.json` will no longer require Firebase. Clean/reinstall if necessary:

```powershell
cd frontend
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
npm install --include=optional
```

Backend `requirements.txt` will no longer require Firebase Admin. Recreating `.venv` is the cleanest rollback if dependency state matters.

## Secrets

The Firebase project and service-account key do not need to be deleted merely because source code is rolled back. Keep them private. If a credential was accidentally committed or exposed, revoke/rotate it in Google/Firebase immediately.
