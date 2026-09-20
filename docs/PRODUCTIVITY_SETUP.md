# Productivity & Outreach Update

This update combines several usability improvements into one release.

## New user-facing features

### 1. Quick Send
Outreach -> Quick Send lets the user choose a connected sender, type any recipient address, subject and body, then send one message immediately.

Use this for testing or genuine one-off emails. It does not create a campaign. Suppressed addresses remain blocked.

### 2. Optional sending hours
The campaign sending window is OFF by default.

When OFF:
- Approval queues the campaign immediately.
- Only daily limit and interval apply.

When ON:
- Choose start/end hour using a 24-hour clock.
- The worker waits until the local campaign window.

### 3. Faster intervals
Available interval choices:
- 20 sec
- 30 sec (default)
- 45 sec
- 60 sec
- 90 sec
- 2 min

These are application scheduling intervals, not a guarantee of mailbox-provider acceptance. Users remain responsible for provider limits and sender reputation.

### 4. Lead sheet import
My Leads -> Import Excel / CSV accepts:
- .xlsx
- .csv
- maximum 10 MB
- maximum 5,000 lead rows

Common headers are mapped automatically, including:
- Company / Business Name
- Contact Name / First Name / Last Name
- Job Title
- Email / Email Status
- Phone
- Website / Domain
- LinkedIn / Instagram / Facebook
- City / State / Country
- Lead Score

A sample file is included at `docs/LEAD_IMPORT_TEMPLATE.csv`.

### 5. Campaign refresh and cleanup
Outreach now:
- refreshes sending campaigns automatically every 15 seconds,
- includes a manual Refresh button,
- shows progress bars,
- shows interval and schedule information,
- allows deletion of non-sending campaigns.

## Update procedure

Copy this complete source over the current project while preserving:
- `.git/`
- `backend/.env`
- `backend/.venv/`
- `frontend/.env`
- `frontend/package-lock.json`
- `frontend/node_modules/`

Do not change `CREDENTIAL_ENCRYPTION_KEY`.

## Backend dependencies

Two packages were added:

```text
openpyxl==3.1.5
python-multipart==0.0.20
```

Run:

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
python -m app.db.migrate
uvicorn app.main:app --reload --port 8000
```

No new database migration is expected. `python -m app.db.migrate` should report the schema is already up to date.

## Frontend

```powershell
cd D:\Leads-Agent\leads-agent\frontend
npm install --include=optional
npm run check
npm run test
npm run build
npm run dev
```

## Worker

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
python -m app.outreach.worker
```

## Recommended tests

1. Quick Send an email to an address you control.
2. Upload `docs/LEAD_IMPORT_TEMPLATE.csv` from My Leads and confirm a new lead list appears.
3. Create a campaign with sending-hours OFF and 30-second interval.
4. Approve it and confirm the worker begins processing without waiting for a time window.
5. Create another campaign with sending-hours ON and verify the schedule is displayed.
6. Delete a completed/cancelled/draft test campaign.
7. Verify Refresh updates campaign counts.
