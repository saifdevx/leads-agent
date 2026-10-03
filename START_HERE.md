# Lead Gen: Apollo discovery + company-name patch

Use this package against the existing project matching the uploaded source ZIP.
Read `docs/APOLLO_COMPANY_NAME_FIX.md` and `docs/PATCH_TEST_REPORT.md` first.

**157 backend tests passed. Full backend API checks and the actual frontend build remain required locally.**
No production deployment or real email sending has been performed.

Extract the package separately, then run (adjust only the project path):

```powershell
python .\APPLY_PATCH.py --project "D:\Leads-Agent\leads-agent" --check
python .\APPLY_PATCH.py --project "D:\Leads-Agent\leads-agent" --apply
```

The Python 3.10+ standard-library installer checks version/file integrity, backs up touched files outside the project,
and refuses incompatible source versions. Your app uses Python 3.13.5. Keep the printed backup and rollback command.
Do not delete entire source folders or rotate saved encryption keys.
Run the complete backend suite and frontend check/test/build before deployment; deploy backend first, then frontend.

Apollo reuses the saved key; search access/credits still depend on Apollo. Automatic mode uses Apollo when it is the only
connected discovery source. Select Apollo explicitly when Serper/Brave is also connected.

Name cleanup applies to template rendering/new campaign snapshots. Pause affected old campaigns, recreate unsent work,
and preview before approval. Already-queued/sent copy and arbitrary Quick Send prose are not silently rewritten.
Inferred display names are not verified legal identities.

The exact 23 application/test/document replacement files and unchanged compatibility guards are in `patch_manifest.json`.
This installer does not change Git, database data, credentials or hosted services.
