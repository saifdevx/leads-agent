# Lead Gen — Smart Data & Security Hardening

This overlay makes the current production app more self-correcting without turning AI into a requirement.

## Included

- Removes historical empty `(0)` lead-list shells.
- Hides future empty lists unless a search is actively running.
- Removes a list from the dropdown immediately when its final leads are deleted.
- Repairs missing company names from existing lead evidence.
- Fills missing region from the list context.
- Revalidates noisy phone values.
- Uses deterministic extraction before Gemini/OpenAI.
- Calls AI only for ambiguous/low-coverage discovery batches.
- Uses Serper first and Brave as a true fallback instead of spending both by default.
- Adds `Cache-Control: no-store, private` to authenticated API routes.

### Example

```text
saadremodeling@gmail.com
→ Saad Remodeling
```

But:

```text
info@gmail.com
→ no invented company name
```

## Install

1. Push the current working repository.
2. Extract the ZIP.
3. Copy into the repository:

```text
backend/app/leads/smart_data.py
backend/migrations/005_smart_cleanup.sql
backend/tests/test_smart_data.py
tools/apply_smart_hardening.py
```

4. From repository root:

```powershell
python tools/apply_smart_hardening.py
```

5. Backend:

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m app.db.migrate
pytest -q
```

6. Frontend:

```powershell
cd ..\frontend
npm run check
npm run test
npm run build
```

7. Check My Leads and run a small automated search.

No new external dependency, API key, or environment variable is required.

## Rollback

Use the Git commit made before applying this overlay.

Migration 005 deletes only empty lead-list records that contain no lead rows and are not actively searching.
