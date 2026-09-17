# Rollback — v0.3.0

## Trusted code rollback point

`v0.2.0` is the last accepted release before Turso.

Before copying v0.3.0, confirm v0.2.0 is pushed and tagged.

## If v0.3.0 fails before acceptance

Return the source tree to tag `v0.2.0` using your normal Git workflow, or restore your saved v0.2.0 ZIP.

Do not delete Firebase users or credentials.

## Database rollback

Migration `001_initial.sql` only creates new application tables and indexes. It does not alter Firebase or existing application data because no previous application database existed.

For a failed local setup, the simplest safe option is to leave the Turso database in place and restore the v0.2.0 code. v0.2.0 does not know about Turso and will ignore those tables.

Do not manually drop tables once real lead data exists in later checkpoints without a dedicated migration/backup plan.
