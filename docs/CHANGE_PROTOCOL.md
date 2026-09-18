# Change Protocol

Every future feature or hotfix must follow this sequence:

1. Inspect the currently working files.
2. Identify behavior that must remain working.
3. Define the smallest coherent change.
4. Check runtime/dependency impact.
5. Check database and API compatibility.
6. Implement.
7. Run backend tests.
8. Run frontend type/build/tests.
9. Test the visible user flow.
10. Package a full replacement ZIP.
11. Document ADD / REPLACE / KEEP / BACKUP / TEST / ROLLBACK.

Do not casually rewrite unrelated working modules.
