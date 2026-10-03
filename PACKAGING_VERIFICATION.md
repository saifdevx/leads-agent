# Installer and packaging verification

Patch `apollo-company-name-2026-10-03`, prepared 2026-10-03.

The checked installer passed **12 automated tests** on Python 3.13.5/Linux using fresh copies of the user's original ZIP.
Tests covered read-only preflight, apply, no-op reapply, repeat rollback, exact byte restoration, unrelated `.env` preservation,
changed-file refusal, unchanged-contract drift, conflicting new files, tampered payloads, symlink/path-traversal refusal,
protecting subsequent edits during rollback, damaged-backup refusal, and automatic restoration after an injected write failure.
CRLF versions of the source tree were also tested: both initial Windows-style checkout and newline-only changes after apply
were accepted, and original backup bytes were restored. This is not a native Windows OS execution test.

The payload contains **23 replacement/addition files**: 12 existing files changed and 11 new files
(4 new runtime modules, 5 regression-test files, 2 documents). In total 16 runtime files are added or changed.
A further **85 unchanged runtime/dependency/configuration files** are checked for compatibility before applying.
UTF-8 CRLF/LF-only differences are accepted; content differences are not. Backup files preserve original local bytes.

The full source includes all 175 original source files plus the 11 additions. The 163 original files outside the changed-file
set are retained byte-for-byte. The patch and full-source archives are checked for CRC validity and manifest SHA-256 integrity.
No `.git`, `node_modules`, `.venv`, `__pycache__`, actual `.env`, private-key files or local source backups are packaged.
Original `.env.example` templates remain in the full source; they are not active credentials.

`verification/installer-tests.txt` contains the executed installer results. Application results and limitations are in
`docs/PATCH_TEST_REPORT.md`, with supporting logs under `verification/`. The 157 passing backend tests are not a claim that
Firebase-dependent API modules or the actual frontend production build were run.

No installer operation commits/pushes Git, changes an application database, contacts an API or deploys a service.
