# Test Checklist — Discovery Quality & Reliability

## Before testing
- [ ] Previous working build is pushed to Git.
- [ ] Real `.env` files were preserved.
- [ ] `CREDENTIAL_ENCRYPTION_KEY` was NOT regenerated.
- [ ] Previously exposed Gemini key was revoked/rotated.
- [ ] `TURSO_TIMEOUT_SECONDS=15` is recommended locally.

## Frontend
- [ ] `npm install --include=optional`
- [ ] `npm run check`
- [ ] `npm run test`
- [ ] `npm run build`
- [ ] `npm run dev`

## Backend
- [ ] `pip install -r requirements.txt`
- [ ] `pytest -q`
- [ ] `python -m app.db.migrate` reports already up to date
- [ ] backend starts on port 8000

## Providers
- [ ] Serper remains connected.
- [ ] New Gemini key can be connected.
- [ ] Invalid Gemini generation access is rejected during connection.
- [ ] Provider API keys do not appear in backend request logs.

## Automated quality benchmark
Search: Pressure washing / Texas, USA / 25 leads.

- [ ] search starts automatically
- [ ] temporary Turso/job-polling failures retry rather than stop the UI
- [ ] no obvious Facebook IDs as phone numbers
- [ ] no date-like phone values
- [ ] explicit out-of-state result such as Central Florida is rejected
- [ ] template/demo sites are rejected
- [ ] duplicate company domains merge into one record
- [ ] company names are better than generic page titles where website metadata exists
- [ ] website crawler failures do not stop the run
- [ ] job completes or reaches bounded search budget cleanly

## Regression
- [ ] Login/logout still work.
- [ ] My Leads still loads.
- [ ] Manual fallback still works.
- [ ] Export still works.
- [ ] Settings connect/disconnect still work.
