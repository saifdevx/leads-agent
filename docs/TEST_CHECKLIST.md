# Test Checklist

Run this checklist before pushing the updated code.

## Automated checks

Backend:

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
pytest -q
python -m app.db.migrate
```

Frontend:

```powershell
cd D:\Leads-Agent\leads-agent\frontend
npm run check
npm run test
npm run build
```

## Authentication regression

- Register/login still works.
- Google sign-in still works.
- Sign out still works.
- Refresh preserves the Firebase session.
- Protected `/api/v1/auth/me` still rejects unauthenticated requests.

## Free lead finder

Use this test input:

```text
Sun Peak Solar
https://sunpeaksolar.com/contact
Email: hello@sunpeaksolar.com
Phone: +1 (214) 555-0198
https://www.instagram.com/sunpeaksolar/

Green Volt Energy
https://greenvolt.example
sales@greenvolt.example
https://www.linkedin.com/company/green-volt/
```

Expected:

- Create a search plan successfully.
- Eight search queries are shown.
- Copy query button works.
- Google button opens a new search tab.
- Paste the sample text and import it.
- Two contacts are extracted and saved on a clean list.
- Re-importing the same sample adds zero new leads and reports duplicates.
- My Leads shows the saved businesses.
- List filter works.
- Search field filters the table.
- Website/social buttons only show when a URL exists.

## Data isolation

If you have a second Firebase test account:

- Sign in as Account A and save a lead.
- Sign out and sign in as Account B.
- Account B must not see Account A's lead list or leads.

## UI

- Desktop sidebar works.
- Mobile navigation works.
- Find Leads remains usable on mobile.
- My Leads table can scroll horizontally on smaller screens.
- No visible checkpoint/version development text appears in the product UI.
