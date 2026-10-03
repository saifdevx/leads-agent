# Patch verification report

Date: 2026-10-03. Patch: `apollo-company-name-2026-10-03`.
Baseline: uploaded `leads-agent-main.zip`, archive commit `2749a8e3d890a83ff4f56f3f497e052694c2825b`.

## Release status

**Targeted tests pass; full deployment verification is still required.** This report does not certify production readiness or live provider access. No production credentials, database, email sender, GitHub push or Render deployment was used.

## Executed successfully

### Backend: 157 tests passed

From `backend/`:

```sh
python -m pytest -q \
  --ignore=tests/test_admin_permissions.py \
  --ignore=tests/test_auth.py \
  --ignore=tests/test_health.py \
  --ignore=tests/test_leads_api.py \
  --ignore=tests/test_quick_send_rate_limit.py
```

Final recorded output:

```text
........................................................................ [ 45%]
........................................................................ [ 91%]
.............                                                            [100%]
157 passed in 1.81s
```

These include the project's existing runnable regression tests, not only tests written for the patch. No existing test file or production dependency pin was edited.

New regression coverage includes:

- Apollo documented endpoint/parameters, response mapping, no implicit contact unlock, 401/403/429/server errors, malformed successful payloads, empty results, explicit/automatic provider choice, source schema, job pagination/deduplication/target and endpoint-denial propagation.
- All supplied bad-company-name examples; clean existing names, punctuation/accents, real alphanumeric brands, emoji removal, neutral fallback, private email handles versus business handles, real social profiles versus post IDs, malformed/shared/numeric hosts, HTML/entity safety and same-record evidence grounding.
- Bad-name discovery candidates triggering AI even with high contact completeness, website/AI merge behavior, preventing cross-record contact/name mixing, homepage metadata, cross-domain redirects, research caps, provider failure and model-request formats.
- Database-backed campaign integration using test SQLite: a legacy caption becomes the same safe company name in initial subject/body/follow-up; the campaign stays draft until approval; queued content matches the reviewed snapshot. Static templates do not trigger name research.

Most external provider/network behavior is mocked. SQLite fixtures exercise application logic but are not a live Turso/Firebase integration test.

### Frontend syntax and focused logic

Used a preinstalled TypeScript 5.8.3 transpiler, not the project's pinned TypeScript 6.0.2. All **25** `.ts`/`.tsx` files under `frontend/src` were individually transpiled without syntax diagnostics. This is **not** type checking, dependency resolution or a Vite production bundle.

Executed **8** Node `assert` checks against the transpiled real `searchProviders.ts` helper: Apollo-only auto/explicit readiness, dual-category handling, selected-but-disconnected rejection, rejecting AI/enrichment-only readiness and preserving web-first automatic behavior when Serper is connected. These are **not** a Vitest run. The four new Vitest cases are shipped but were not run with Vitest here.

### Static checks

From the repository root:

```sh
python -m compileall -q backend/app backend/tests
git diff --check
```

Both passed. No Python syntax or tracked whitespace errors were found.

## Checks blocked by this environment

A full `pytest -q` from `backend/` exits with code 2 during collection:

```text
ERROR tests/test_admin_permissions.py
ERROR tests/test_auth.py
ERROR tests/test_health.py
ERROR tests/test_leads_api.py
ERROR tests/test_quick_send_rate_limit.py
ModuleNotFoundError: No module named 'firebase_admin'
5 errors during collection
```

The unmodified baseline had the same missing-SDK collection problem. Installing the pinned backend dependencies into a separate test virtual environment failed because the package registry could not be reached/resolved. No fake Firebase module was injected to produce misleading green API tests.

Frontend `npm ci --include=optional` also could not reach the registry. An offline attempt could not satisfy the missing cached packages. Therefore these commands were **not completed**:

```sh
npm run check
npm run test
npm run build
```

Do not treat syntax-transpile smoke checks as substitutes for those commands.

### Available environment versus source pins

| Component | Available test environment | Source pin |
| --- | --- | --- |
| Python | 3.13.5 | 3.13.5 in `.python-version` |
| FastAPI | 0.128.2 | 0.141.1 |
| pytest | 9.0.2 | 9.1.1 |
| httpx | 0.28.1 | 0.28.1 |
| pydantic-settings | 2.14.1 | 2.14.2 |
| cryptography | 46.0.4 | 50.0.1 |
| firebase-admin | unavailable | 7.5.0 |
| XlsxWriter | 3.2.9 | 3.2.9 |
| openpyxl | 3.1.5 | 3.1.5 |
| python-multipart | 0.0.29 | 0.0.20 |
| Node / npm | 22.16.0 / 10.9.2 | existing frontend configuration preserved |
| TypeScript smoke transpiler | 5.8.3 | 6.0.2 |

The pins were deliberately not changed to make this environment pass.

## Live behavior not verified here

Apollo account eligibility/endpoint permissions/search results/credits; configured OpenAI or Gemini model access; actual website identity for the user's business examples; Firebase login; real Turso operations/migration startup; live Hostinger/Gmail delivery/reply callbacks; Render deploy/build behavior; Windows-specific native bindings.

Names derived from a domain/mailbox are evidence-based display fallbacks, not externally verified company identities. The MQ/MP mismatch in the first supplied example remains something a human should review.

## Required release gate on the user's project environment

Run the **full** backend suite with the existing pinned requirements. Run frontend check, tests and build with the existing lockfile. Do not carry the exclusions above into production release checks. Preserve normal migration startup. Deploy the backend then frontend and smoke-test login, both discovery paths, saved leads/exports, a new one-recipient campaign preview and controlled delivery, relevant follow-ups/replies and Admin. Keep affected older campaigns paused until their unsent work has been reviewed/recreated.

Installer/packaging verification is recorded in the package's `PACKAGING_VERIFICATION.md` separately so the application code/test report does not need to be changed after its file hashes are computed.
