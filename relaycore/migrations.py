"""SQLite schema migrations for RelayCore."""

import argparse
from datetime import datetime, timezone
import sqlite3
from typing import Dict, Iterable, Optional, Sequence

from .storage import DEFAULT_DB_PATH, PRAGMA_STATEMENTS, configure_connection, resolve_database_path

MIGRATION_NAME = "0001_cross_agent_control_plane"

TABLE_STATEMENTS: Sequence[str] = (
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
      name TEXT PRIMARY KEY,
      applied_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
      session_id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      goal TEXT NOT NULL,
      mode TEXT NOT NULL,
      status TEXT DEFAULT 'active',
      created_by TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      metadata TEXT DEFAULT '{}'
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS commands (
      command_id TEXT PRIMARY KEY,
      session_id TEXT NOT NULL,
      target_agent TEXT,
      target_runtime TEXT,
      mode TEXT NOT NULL,
      command_type TEXT NOT NULL,
      payload TEXT NOT NULL,
      status TEXT DEFAULT 'pending',
      priority INTEGER DEFAULT 100,
      created_by TEXT NOT NULL,
      created_at TEXT NOT NULL,
      claimed_by TEXT,
      claimed_at TEXT,
      lease_expires_at TEXT,
      completed_at TEXT,
      result TEXT DEFAULT '{}',
      idempotency_key TEXT,
      permission_level TEXT DEFAULT 'L1'
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_events (
      seq INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id TEXT NOT NULL,
      agent_id TEXT NOT NULL,
      runtime TEXT,
      mode TEXT,
      event_type TEXT NOT NULL,
      content TEXT NOT NULL,
      command_id TEXT,
      parent_seq INTEGER,
      node_id TEXT,
      trace_refs TEXT DEFAULT '[]',
      artifact_refs TEXT DEFAULT '[]',
      metadata TEXT DEFAULT '{}',
      created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_states (
      agent_id TEXT PRIMARY KEY,
      runtime TEXT NOT NULL,
      session_id TEXT,
      role TEXT,
      status TEXT DEFAULT 'idle',
      last_seen_seq INTEGER DEFAULT 0,
      last_heartbeat TEXT,
      current_task TEXT,
      capabilities TEXT DEFAULT '[]',
      metadata TEXT DEFAULT '{}'
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS session_digests (
      digest_id TEXT PRIMARY KEY,
      session_id TEXT NOT NULL,
      from_seq INTEGER NOT NULL,
      to_seq INTEGER NOT NULL,
      summary TEXT NOT NULL,
      decisions TEXT DEFAULT '[]',
      open_questions TEXT DEFAULT '[]',
      rejected_candidates TEXT DEFAULT '[]',
      node_id TEXT,
      trace_refs TEXT DEFAULT '[]',
      artifact_refs TEXT DEFAULT '[]',
      task_canvas TEXT DEFAULT '',
      created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS memory_candidates (
      candidate_id TEXT PRIMARY KEY,
      proposed_by TEXT NOT NULL,
      runtime TEXT,
      session_id TEXT,
      type TEXT NOT NULL,
      title TEXT NOT NULL,
      content TEXT NOT NULL,
      summary TEXT DEFAULT '',
      rejected TEXT DEFAULT '[]',
      tags TEXT DEFAULT '[]',
      status TEXT DEFAULT 'pending',
      similar_to TEXT DEFAULT '[]',
      conflicts_with TEXT DEFAULT '[]',
      recommended_action TEXT DEFAULT '',
      node_id TEXT,
      trace_refs TEXT DEFAULT '[]',
      artifact_refs TEXT DEFAULT '[]',
      memory_level TEXT DEFAULT 'L1',
      decision_status TEXT DEFAULT 'candidate',
      created_at TEXT NOT NULL,
      resolved_at TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS memory_occurrences (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      memory_id TEXT NOT NULL,
      agent_id TEXT NOT NULL,
      runtime TEXT,
      session_id TEXT,
      observed_at TEXT NOT NULL,
      note TEXT DEFAULT ''
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS memory_clusters (
      cluster_id TEXT PRIMARY KEY,
      canonical_memory_id TEXT NOT NULL,
      summary TEXT NOT NULL,
      tags TEXT DEFAULT '[]',
      source_count INTEGER DEFAULT 1,
      quality_score REAL DEFAULT 0.5,
      updated_at TEXT NOT NULL,
      metadata TEXT DEFAULT '{}'
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS artifacts (
      artifact_id TEXT PRIMARY KEY,
      session_id TEXT,
      agent_id TEXT,
      kind TEXT NOT NULL,
      path TEXT NOT NULL,
      sha256 TEXT NOT NULL,
      size_bytes INTEGER DEFAULT 0,
      summary TEXT DEFAULT '',
      trace_refs TEXT DEFAULT '[]',
      metadata TEXT DEFAULT '{}',
      created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS rejected_knowledge (
      rejected_id TEXT PRIMARY KEY,
      session_id TEXT,
      candidate_id TEXT NOT NULL,
      accepted_candidate_id TEXT,
      decision_type TEXT NOT NULL,
      reason TEXT DEFAULT '',
      trace_refs TEXT DEFAULT '[]',
      artifact_refs TEXT DEFAULT '[]',
      metadata TEXT DEFAULT '{}',
      created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      actor TEXT NOT NULL,
      action TEXT NOT NULL,
      resource_type TEXT NOT NULL,
      resource_id TEXT,
      request_id TEXT,
      ip TEXT,
      metadata TEXT DEFAULT '{}',
      created_at TEXT NOT NULL
    );
    """,
)

INDEX_STATEMENTS: Sequence[str] = (
    "CREATE INDEX IF NOT EXISTS idx_commands_session_status_priority ON commands(session_id, status, priority, created_at);",
    "CREATE INDEX IF NOT EXISTS idx_commands_target_runtime_status ON commands(target_runtime, status, created_at);",
    "CREATE INDEX IF NOT EXISTS idx_commands_target_agent_status ON commands(target_agent, status, created_at);",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_commands_idempotency_key ON commands(idempotency_key) WHERE idempotency_key IS NOT NULL;",
    "CREATE INDEX IF NOT EXISTS idx_agent_events_session_seq ON agent_events(session_id, seq);",
    "CREATE INDEX IF NOT EXISTS idx_agent_events_command_id ON agent_events(command_id) WHERE command_id IS NOT NULL;",
    "CREATE INDEX IF NOT EXISTS idx_agent_events_agent_id_created_at ON agent_events(agent_id, created_at);",
    "CREATE INDEX IF NOT EXISTS idx_agent_states_session_status ON agent_states(session_id, status);",
    "CREATE INDEX IF NOT EXISTS idx_session_digests_session_seq ON session_digests(session_id, from_seq, to_seq);",
    "CREATE INDEX IF NOT EXISTS idx_memory_candidates_status_created_at ON memory_candidates(status, created_at);",
    "CREATE INDEX IF NOT EXISTS idx_memory_candidates_session_id ON memory_candidates(session_id) WHERE session_id IS NOT NULL;",
    "CREATE INDEX IF NOT EXISTS idx_memory_occurrences_memory_id ON memory_occurrences(memory_id, observed_at);",
    "CREATE INDEX IF NOT EXISTS idx_artifacts_session_agent ON artifacts(session_id, agent_id, created_at);",
    "CREATE INDEX IF NOT EXISTS idx_rejected_knowledge_session_created ON rejected_knowledge(session_id, created_at);",
    "CREATE INDEX IF NOT EXISTS idx_rejected_knowledge_candidate ON rejected_knowledge(candidate_id, created_at);",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_created_at ON audit_logs(actor, created_at);",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id, created_at);",
)

REQUIRED_COLUMNS: Dict[str, Dict[str, str]] = {
    "agent_events": {
        "node_id": "TEXT",
        "trace_refs": "TEXT DEFAULT '[]'",
        "artifact_refs": "TEXT DEFAULT '[]'",
    },
    "session_digests": {
        "node_id": "TEXT",
        "trace_refs": "TEXT DEFAULT '[]'",
        "artifact_refs": "TEXT DEFAULT '[]'",
        "task_canvas": "TEXT DEFAULT ''",
    },
    "memory_candidates": {
        "node_id": "TEXT",
        "trace_refs": "TEXT DEFAULT '[]'",
        "artifact_refs": "TEXT DEFAULT '[]'",
        "memory_level": "TEXT DEFAULT 'L1'",
        "decision_status": "TEXT DEFAULT 'candidate'",
    },
    "artifacts": {
        "trace_refs": "TEXT DEFAULT '[]'",
        "metadata": "TEXT DEFAULT '{}'",
    },
}


def utc_now() -> str:
    """Return a stable ISO-8601 timestamp for migration bookkeeping."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def apply_pragmas(connection: sqlite3.Connection) -> None:
    """Apply SQLite runtime pragmas needed for this project."""
    configure_connection(connection)


def ensure_base_schema(connection: sqlite3.Connection) -> None:
    """Create all current tables and indexes if they do not already exist."""
    for statement in TABLE_STATEMENTS:
        connection.execute(statement)

    ensure_required_columns(connection)

    for statement in INDEX_STATEMENTS:
        connection.execute(statement)


def ensure_required_columns(connection: sqlite3.Connection) -> None:
    """Backfill newer additive columns for existing user databases."""
    for table_name, columns in REQUIRED_COLUMNS.items():
        existing = current_columns(connection, table_name)
        for column_name, definition in columns.items():
            if column_name in existing:
                continue
            connection.execute(
                "ALTER TABLE {} ADD COLUMN {} {}".format(table_name, column_name, definition)
            )


def current_columns(connection: sqlite3.Connection, table_name: str) -> set:
    rows = connection.execute("PRAGMA table_info({})".format(table_name)).fetchall()
    return {row[1] for row in rows}


def record_migration(connection: sqlite3.Connection, name: str) -> None:
    """Persist the applied migration marker once schema creation succeeds."""
    connection.execute(
        """
        INSERT OR IGNORE INTO schema_migrations(name, applied_at)
        VALUES(?, ?)
        """,
        (name, utc_now()),
    )


def apply_migrations(connection: sqlite3.Connection) -> None:
    """Apply the current schema migration set in an idempotent transaction."""
    apply_pragmas(connection)
    ensure_base_schema(connection)
    record_migration(connection, MIGRATION_NAME)
    connection.commit()


def initialize_database(db_path: Optional[str] = None) -> str:
    """Open the configured database, apply migrations, and return its path."""
    resolved_path = resolve_database_path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(resolved_path))
    try:
        configure_connection(connection)
        apply_migrations(connection)
    finally:
        connection.close()

    return str(resolved_path)


def list_user_tables(connection: sqlite3.Connection) -> Iterable[str]:
    """Return the non-SQLite table names for verification and diagnostics."""
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [row[0] for row in rows]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize the RelayCore SQLite schema.")
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path. Defaults to relaycore.db in the current working directory.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    database_path = initialize_database(args.db)
    print("Initialized RelayCore database at {}".format(database_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
