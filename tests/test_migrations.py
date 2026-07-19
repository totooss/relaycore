from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from echomemory.migrations import MIGRATION_NAME, apply_migrations, initialize_database
from echomemory.storage import bootstrap_database, connect_database


EXPECTED_TABLES = {
    "agent_events",
    "agent_states",
    "artifacts",
    "audit_logs",
    "commands",
    "memory_candidates",
    "memory_clusters",
    "memory_occurrences",
    "schema_migrations",
    "session_digests",
    "sessions",
}


def fetch_table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()
    return {row[0] for row in rows}


def test_initialize_database_creates_expected_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "echomemory.db"

    resolved = initialize_database(str(database_path))

    with sqlite3.connect(resolved) as connection:
        assert EXPECTED_TABLES.issubset(fetch_table_names(connection))
        migration_rows = connection.execute(
            "SELECT name FROM schema_migrations WHERE name = ?",
            (MIGRATION_NAME,),
        ).fetchall()
        assert len(migration_rows) == 1


def test_apply_migrations_is_idempotent(tmp_path: Path) -> None:
    database_path = tmp_path / "idempotent.db"

    with connect_database(database_path) as connection:
        apply_migrations(connection)
        apply_migrations(connection)

        migration_count = connection.execute(
            "SELECT COUNT(*) FROM schema_migrations WHERE name = ?",
            (MIGRATION_NAME,),
        ).fetchone()[0]
        assert migration_count == 1

        index_names = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'index'
                  AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()
        }
        assert "idx_commands_session_status_priority" in index_names
        assert "idx_agent_events_session_seq" in index_names


def test_bootstrap_database_applies_sqlite_pragmas(tmp_path: Path) -> None:
    database_path = bootstrap_database(tmp_path / "pragmas.db")

    with connect_database(database_path) as connection:
        journal_mode = connection.execute("PRAGMA journal_mode;").fetchone()[0]
        synchronous = connection.execute("PRAGMA synchronous;").fetchone()[0]
        busy_timeout = connection.execute("PRAGMA busy_timeout;").fetchone()[0]

        assert journal_mode.lower() == "wal"
        assert synchronous == 1
        assert busy_timeout == 5000
