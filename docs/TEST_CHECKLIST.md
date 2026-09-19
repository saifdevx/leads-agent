# Test Checklist

## Regression

### Frontend
```powershell
npm run check
npm run test
npm run build
```

### Backend
```powershell
pytest -q
python -m app.db.migrate
```

Migration should report that the schema is already up to date.

## Provider settings

- [ ] Existing Serper connection still loads.
- [ ] Existing Gemini/OpenAI connection still loads.
- [ ] Prospeo appears in Settings.
- [ ] Apollo appears in Settings.
- [ ] Invalid Prospeo key is rejected.
- [ ] Valid Prospeo key is accepted.
- [ ] Invalid Apollo key is rejected.
- [ ] Valid Apollo key is accepted.
- [ ] Saved provider key is masked after refresh.

## Lead enrichment

- [ ] Select 5–10 leads.
- [ ] Enrich button enables.
- [ ] Smart provider mode starts a background job.
- [ ] Job polling survives temporary database 503 responses.
- [ ] Already-verified lead is not charged/enriched again.
- [ ] Missing contact can receive name/title/email/LinkedIn when provider finds a match.
- [ ] Verified email status displays as Verified.
- [ ] Existing business row is updated; no duplicate lead row is created.
- [ ] Enrichment source is appended to existing source.
- [ ] More than 100 selected leads cannot be enriched in one run.

## Export

- [ ] Export current filtered view to XLSX.
- [ ] Workbook contains `Leads` and `Summary` sheets.
- [ ] XLSX hyperlinks open correctly.
- [ ] Verified email status is visibly highlighted.
- [ ] Export current filtered view to CSV.
- [ ] Select several rows and export selected only.
- [ ] Email-status filter is reflected in filtered export.
- [ ] Minimum-score filter is reflected in filtered export.
- [ ] Empty export produces a clear error instead of a blank file.
