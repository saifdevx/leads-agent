# Rollback — v0.1.1

This is a dependency/install hotfix only. No application data, API, authentication, or database schema changed.

## Roll back to v0.1.0

1. Stop the frontend dev server.
2. Restore the saved `v0.1.0` project or Git tag.
3. Delete `frontend/node_modules` and `frontend/package-lock.json`.
4. Reinstall the restored version.

```powershell
cd frontend
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
Remove-Item -Force package-lock.json -ErrorAction SilentlyContinue
npm install
```

The backend does not need to be rolled back because its source files are unchanged between v0.1.0 and v0.1.1.
