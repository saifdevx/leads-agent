# Delivery Notes — v0.1.1

## VERSION
`0.1.1`

## PURPOSE
Fix the Windows frontend install failure caused when npm omits Rolldown's platform-specific native optional dependency.

## REPLACE
Use this ZIP as the full Checkpoint 1 replacement.

## KEEP
- Your existing local backend `.env`
- Any local frontend `.env` values
- All Checkpoint 0 product decisions

## CHANGED
- `frontend/package.json`
- `frontend/.npmrc` (new)
- `README.md`
- `CHANGELOG.md`
- `render.yaml`
- version documentation

## UNCHANGED
- React application source
- FastAPI source
- API contract
- UI design

## INSTALL — WINDOWS HOTFIX

```powershell
cd frontend
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
Remove-Item -Force package-lock.json -ErrorAction SilentlyContinue
npm cache verify
npm install --include=optional
npm run dev
```

## TEST

```powershell
npm run check
npm run test
npm run build
```

Backend regression:

```powershell
cd ..\backend
pytest -q
```

## ROLLBACK
See `docs/ROLLBACK.md`.
