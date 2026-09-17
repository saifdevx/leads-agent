from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from app.db.dependencies import get_database_client

MIGRATION_NAME = re.compile(r"^[0-9]{3}_[a-z0-9_]+$")
MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _ensure_migration_table() -> None:
    database = get_database_client()
    database.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """,
        want_rows=False,
    )


def _applied_versions() -> set[str]:
    database = get_database_client()
    result = database.execute("SELECT version FROM schema_migrations ORDER BY version")
    return {str(row["version"]) for row in result.rows}


def run_migrations() -> list[str]:
    _ensure_migration_table()
    applied = _applied_versions()
    database = get_database_client()
    newly_applied: list[str] = []

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    for migration_path in migration_files:
        version = migration_path.stem
        if not MIGRATION_NAME.fullmatch(version):
            raise RuntimeError(
                f"Migration filename '{migration_path.name}' must match NNN_name.sql."
            )
        if version in applied:
            continue

        migration_sql = migration_path.read_text(encoding="utf-8").strip()
        if not migration_sql:
            raise RuntimeError(f"Migration '{migration_path.name}' is empty.")

        escaped_version = version.replace("'", "''")
        applied_at = datetime.now(timezone.utc).isoformat().replace("'", "''")
        transaction_sql = (
            "BEGIN;\n"
            f"{migration_sql}\n"
            "INSERT INTO schema_migrations (version, applied_at) "
            f"VALUES ('{escaped_version}', '{applied_at}');\n"
            "COMMIT;"
        )
        database.execute_sequence(transaction_sql)
        newly_applied.append(version)

    return newly_applied


def main() -> None:
    applied = run_migrations()
    if applied:
        print("Applied migrations:")
        for version in applied:
            print(f"  - {version}")
    else:
        print("Database schema is already up to date.")


if __name__ == "__main__":
    main()
