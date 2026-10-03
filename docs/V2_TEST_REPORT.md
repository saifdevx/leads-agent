# V2 verification report

Prepared 3 October 2026. See the accompanying installation guide for scope and external API references.

## Application checks executed

- Backend runnable suite: **244 passed**. This includes the existing regression suite and new provider/identity/delivery tests.
- Five Firebase-dependent test modules could not be collected: admin permissions, authentication, health, leads API, Quick Send rate limit.
  The complete `pytest -q` run stopped with five collection errors because `firebase_admin` is absent.
- A download probe for the pinned `firebase-admin==7.5.0` found no available distribution in this environment. No Firebase stub was substituted.
- All backend application modules passed Python byte compilation.
- All **25 TS/TSX** source/test files passed syntax transpilation using available TypeScript **5.8.3**.
- **10 isolated provider-selection smoke assertions** passed against the transpiled actual `searchProviders.ts` module.
  These are not a React render, a full TypeScript project check, or a Vitest suite.
- `npm ci --include=optional` was attempted and timed out without completing dependency installation.
  An independent npm registry probe failed with `EAI_AGAIN` resolving `registry.npmjs.org`.
- `npm run check` and `npm run build` failed because dependency type definitions were missing; `npm run test` could not find Vitest.
  The project's actual frontend production build and full frontend tests remain unverified here.

## Coverage of new regressions

Provider capabilities and schema validation; secret-free connection metadata; Prospeo actual endpoint/filter/header shape;
canonical location alias resolution, ambiguity refusal and cross-page caching; null company fields; no contact reveal or fabricated email;
provider error payloads and quota handling; Tavily basic/Exa fast request bounds; no unsupported pagination; actual key-validation dispatch;
company fallback vs explicit source selection; counted failed search attempts; no repeated denied-source loop; no false all-failed success;
job-wide company page budget; catalogue-to-adapter coverage; directory filtering before inference.

Ranked list titles and the user's RevenueBase example; old rooftop-caption cases; unknown-name plain/HTML greeting and subject fallback;
exact per-lead legacy literal cleanup during new rendering; inferred-name vs identity-review states; custom-domain conflicts and public-email
exceptions; email syntax/system-mailbox holds; unrelated website footer/structured-org evidence; campaign recipient dedupe; all-unsafe/no-write
behavior; initial/follow-up snapshots; approval/resume guards; final send gates before provider calls; worker safety holds without sender
credential errors; stored historical directory records, neutral Quick Send rejection and tenant-isolated evidence lookups.

## Environment and limits

Python 3.13.5, pytest 9.0.2, FastAPI 0.128.2, Pydantic 2.13.4, pydantic-settings 2.14.1, httpx 0.28.1 and cryptography 46.0.4 were available.
Several versions differ from the project's pins. Requirements, package.json and package-lock.json were not changed to accommodate this environment.
Node was 22.16.0; the project's pinned TypeScript is 6.0.2, not the 5.8.3 used for syntax-only smoke checks.

No native Windows execution, live Firebase authentication, live Turso database, real provider-account permission/credit test,
Render deployment, or actual email delivery was performed. Requests to external providers in regression tests were mocked.
Passing mocked contract tests is not proof of live account access or that the provider's dataset contains the requested leads.
No claim of complete production readiness is made. Run the full checks with pinned dependencies and a controlled smoke test before deployment.

## Package checks

- **12 installer regression tests passed**: read-only preflight, exact backups/rollback, no-op reapply, CRLF preservation,
  conflicting source/new files, unchanged-interface drift, payload integrity, unsafe manifest paths, protection against later edits,
  corrupted backup rejection, and injected mid-install write failure recovery.
- The replacement package contains **39 payload files: 30 replacements and 9 additions**. It also checks **78 unchanged
  runtime/dependency/configuration files** against the verified first-patch baseline.
- No dependencies, lockfiles, migrations, actual `.env` files or credentials are included as changes.
- The final ZIP was extracted into a fresh directory and its own installer was applied to a clean first-patch source copy.
  The installed source passed the same **244-test runnable backend suite**, **25-file syntax transpilation**, and
  **10 isolated provider-selection assertions**. Every installed payload SHA-256 was compared to the package manifest.
- ZIP integrity and package file exclusions were checked. Local source installation is verified; hosted deployment is not.

The installer is standard-library-only. Application and packaging command logs are included under `verification/` in the replacement ZIP.
Installer regression tests can be rerun separately by setting `LEADGEN_V2_BASELINE` to a clean first-patch source tree and running
`python -m pytest -q verification/test_v2_installer.py` from the extracted package. That test file is not installed into the application.
