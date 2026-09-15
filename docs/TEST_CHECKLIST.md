# Checkpoint 1 v0.1.1 Test Checklist

## Clean-install checks

- [ ] Backend virtual environment created from scratch
- [ ] `pip install -r requirements.txt` completes
- [ ] `pytest -q` passes
- [ ] `uvicorn app.main:app --reload --port 8000` starts
- [ ] `GET /health` returns HTTP 200
- [ ] Response includes `status`, `service`, `version`, `environment`, `timestamp`, `request_id`
- [ ] `X-Request-ID` response header is present
- [ ] Frontend clean install with `npm install --include=optional` completes
- [ ] `node_modules/@rolldown/binding-win32-x64-msvc` exists on Windows x64
- [ ] `npm run check` passes
- [ ] `npm run test` passes
- [ ] `npm run build` passes
- [ ] `npm run dev` starts on port 5173

## User-visible checks

- [ ] Find Leads is the default screen
- [ ] Sidebar only exposes Find Leads, My Leads, Outreach, Settings
- [ ] Navigation switches screens correctly
- [ ] Mobile menu opens and closes
- [ ] API badge becomes `API connected` when backend is running
- [ ] API badge becomes `API unavailable` when backend is stopped
- [ ] Advanced options open and close
- [ ] Find Leads button does not pretend live search exists
- [ ] UI remains readable at 375px mobile width
- [ ] UI remains readable at 1440px desktop width

## Regression rule

Do not start Checkpoint 2 until every critical item above passes in the user's environment.
