from app.db.client import QueryResult
from app.db import migrate


class FakeDatabase:
    def __init__(self):
        self.sequences = []

    def execute(self, sql, params=(), *, want_rows=True):
        if "SELECT version FROM schema_migrations" in sql:
            return QueryResult(["version"], [], 0, None, 0, 0)
        return QueryResult([], [], 0, None, 0, 0)

    def execute_sequence(self, sql):
        self.sequences.append(sql)


def test_migration_runner_wraps_new_migration_in_transaction(monkeypatch, tmp_path):
    database = FakeDatabase()
    migration_file = tmp_path / "001_initial.sql"
    migration_file.write_text("CREATE TABLE demo (id TEXT PRIMARY KEY);", encoding="utf-8")

    monkeypatch.setattr(migrate, "get_database_client", lambda: database)
    monkeypatch.setattr(migrate, "MIGRATIONS_DIR", tmp_path)

    applied = migrate.run_migrations()

    assert applied == ["001_initial"]
    assert len(database.sequences) == 1
    sequence = database.sequences[0]
    assert sequence.startswith("BEGIN;")
    assert "CREATE TABLE demo" in sequence
    assert "INSERT INTO schema_migrations" in sequence
    assert sequence.rstrip().endswith("COMMIT;")
