"""Single-database policy and legacy database consolidation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import os
import sqlite3
from typing import Dict, Iterable, List, Optional, Sequence

from .storage import RelayCoreStorage, memory_status_to_decision_status, resolve_database_path

CANONICAL_DB_FILENAME = "relaycore.db"
LEGACY_DB_FILENAMES = frozenset(("echomemory.db",))
ALLOW_CUSTOM_DB_ENV = "RELAYCORE_ALLOW_CUSTOM_DB"
_TABLES_WITH_PRIMARY_KEYS = {
    "sessions": "session_id",
    "commands": "command_id",
    "agent_states": "agent_id",
    "session_digests": "digest_id",
    "memory_candidates": "candidate_id",
    "memory_clusters": "cluster_id",
    "artifacts": "artifact_id",
    "rejected_knowledge": "rejected_id",
}
_MERGE_TABLES = (
    "sessions",
    "commands",
    "agent_states",
    "session_digests",
    "memory_candidates",
    "memory_occurrences",
    "memory_clusters",
    "artifacts",
    "rejected_knowledge",
    "audit_logs",
)


class SingleDBConstraintError(ValueError):
    """Raised when runtime operations would split project memory across DB files."""


@dataclass(frozen=True)
class DatabaseInventory:
    path: Path
    session_count: int
    memory_count: int
    digest_count: int


@dataclass(frozen=True)
class ConsolidationReport:
    source_path: Path
    target_path: Path
    backup_path: Path
    archive_path: Optional[Path]
    imported_counts: Dict[str, int]
    skipped_counts: Dict[str, int]


def inspect_database(path: Path) -> DatabaseInventory:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        return DatabaseInventory(path=resolved, session_count=0, memory_count=0, digest_count=0)
    connection = sqlite3.connect(str(resolved))
    try:
        return DatabaseInventory(
            path=resolved,
            session_count=_count_rows(connection, "sessions"),
            memory_count=_count_rows(connection, "memory_candidates"),
            digest_count=_count_rows(connection, "session_digests"),
        )
    finally:
        connection.close()


def enforce_single_runtime_db(db_path: os.PathLike[str] | str | None = None) -> Path:
    resolved = resolve_database_path(db_path)
    if os.environ.get(ALLOW_CUSTOM_DB_ENV) == "1":
        return resolved
    if resolved.name != CANONICAL_DB_FILENAME:
        raise SingleDBConstraintError(
            "Local RelayCore runtime is constrained to {}. "
            "Received {}. Set {}=1 only for an intentional advanced override.".format(
                CANONICAL_DB_FILENAME,
                resolved,
                ALLOW_CUSTOM_DB_ENV,
            )
        )
    conflicts = legacy_databases_with_data(resolved)
    if conflicts:
        details = ", ".join(
            "{} (sessions={}, memory={}, digests={})".format(
                inventory.path.name,
                inventory.session_count,
                inventory.memory_count,
                inventory.digest_count,
            )
            for inventory in conflicts
        )
        raise SingleDBConstraintError(
            "Legacy RelayCore databases still contain project memory next to {}: {}. "
            "Consolidate them into {} before starting local services.".format(
                resolved,
                details,
                resolved,
            )
        )
    return resolved


def legacy_databases_with_data(db_path: os.PathLike[str] | str | None = None) -> List[DatabaseInventory]:
    resolved = resolve_database_path(db_path)
    inventories: List[DatabaseInventory] = []
    for name in sorted(LEGACY_DB_FILENAMES):
        legacy_path = resolved.parent / name
        if legacy_path == resolved or not legacy_path.exists():
            continue
        inventory = inspect_database(legacy_path)
        if inventory.session_count or inventory.memory_count or inventory.digest_count:
            inventories.append(inventory)
    return inventories


def consolidate_legacy_database(
    *,
    source_path: os.PathLike[str] | str,
    target_path: os.PathLike[str] | str,
    archive_source: bool = True,
) -> ConsolidationReport:
    resolved_source = resolve_database_path(source_path)
    resolved_target = resolve_database_path(target_path)
    if resolved_source == resolved_target:
        raise SingleDBConstraintError("source and target database paths must be different")
    if not resolved_source.exists():
        raise FileNotFoundError("legacy database {!r} does not exist".format(str(resolved_source)))
    if resolved_target.name != CANONICAL_DB_FILENAME:
        raise SingleDBConstraintError(
            "Legacy consolidation target must be {} instead of {}.".format(
                CANONICAL_DB_FILENAME,
                resolved_target.name,
            )
        )

    target = RelayCoreStorage(resolved_target)
    source = sqlite3.connect(str(resolved_source))
    source.row_factory = sqlite3.Row
    backup_path = _build_backup_path(resolved_target)
    imported_counts = {table: 0 for table in _MERGE_TABLES}
    skipped_counts = {table: 0 for table in _MERGE_TABLES}
    archive_path: Optional[Path] = None
    try:
        target.backup_database(backup_path)
        for table in _MERGE_TABLES:
            imported, skipped = _merge_table(source, target.connection, table)
            imported_counts[table] = imported
            skipped_counts[table] = skipped
        target.connection.commit()
    finally:
        source.close()
        target.close()

    if archive_source:
        archive_path = _archive_path_for(resolved_source)
        resolved_source.rename(archive_path)

    return ConsolidationReport(
        source_path=resolved_source,
        target_path=resolved_target,
        backup_path=backup_path,
        archive_path=archive_path,
        imported_counts=imported_counts,
        skipped_counts=skipped_counts,
    )


def _count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    if not _table_exists(connection, table_name):
        return 0
    row = connection.execute("SELECT COUNT(*) FROM {}".format(table_name)).fetchone()
    return int(row[0]) if row is not None else 0


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _column_names(connection: sqlite3.Connection, table_name: str) -> List[str]:
    rows = connection.execute("PRAGMA table_info({})".format(table_name)).fetchall()
    return [str(row[1]) for row in rows]


def _merge_table(source: sqlite3.Connection, target: sqlite3.Connection, table_name: str) -> tuple[int, int]:
    if not _table_exists(source, table_name) or not _table_exists(target, table_name):
        return 0, 0
    source_columns = _column_names(source, table_name)
    target_columns = _column_names(target, table_name)
    excluded_columns = set()
    if table_name == "memory_occurrences":
        excluded_columns.add("id")
    if table_name == "audit_logs":
        excluded_columns.add("id")
    shared_columns = [column for column in source_columns if column in target_columns and column not in excluded_columns]
    if not shared_columns and table_name not in {"memory_candidates", "session_digests"}:
        return 0, 0

    rows = source.execute("SELECT * FROM {}".format(table_name)).fetchall()
    imported = 0
    skipped = 0
    primary_key = _TABLES_WITH_PRIMARY_KEYS.get(table_name)

    for row in rows:
        payload = {column: row[column] for column in shared_columns}
        payload.update(_table_default_overrides(table_name, row, source_columns, target_columns))
        columns = list(payload.keys())
        placeholders = ", ".join("?" for _ in columns)
        values = [payload[column] for column in columns]
        insert_sql = "INSERT INTO {} ({}) VALUES ({})".format(table_name, ", ".join(columns), placeholders)
        insert_ignore_sql = "INSERT OR IGNORE INTO {} ({}) VALUES ({})".format(
            table_name,
            ", ".join(columns),
            placeholders,
        )
        if primary_key:
            cursor = target.execute(insert_ignore_sql, values)
            if cursor.rowcount:
                imported += 1
            else:
                skipped += 1
            continue
        if _row_exists(target, table_name, columns, values):
            skipped += 1
            continue
        target.execute(insert_sql, values)
        imported += 1
    return imported, skipped


def _table_default_overrides(
    table_name: str,
    row: sqlite3.Row,
    source_columns: Sequence[str],
    target_columns: Sequence[str],
) -> Dict[str, object]:
    values: Dict[str, object] = {}
    if table_name == "memory_candidates":
        if "memory_level" in target_columns and "memory_level" not in source_columns:
            values["memory_level"] = _default_memory_level(str(row["type"] or ""))
        if "decision_status" in target_columns and "decision_status" not in source_columns:
            values["decision_status"] = memory_status_to_decision_status(str(row["status"] or "pending"))
        if "node_id" in target_columns and "node_id" not in source_columns:
            values["node_id"] = "legacy-memory-{}".format(row["candidate_id"])
        if "trace_refs" in target_columns and "trace_refs" not in source_columns:
            values["trace_refs"] = "[]"
        if "artifact_refs" in target_columns and "artifact_refs" not in source_columns:
            values["artifact_refs"] = "[]"
    if table_name == "session_digests":
        if "node_id" in target_columns and "node_id" not in source_columns:
            values["node_id"] = "legacy-digest-{}".format(row["digest_id"])
        if "trace_refs" in target_columns and "trace_refs" not in source_columns:
            values["trace_refs"] = "[]"
        if "artifact_refs" in target_columns and "artifact_refs" not in source_columns:
            values["artifact_refs"] = "[]"
        if "task_canvas" in target_columns and "task_canvas" not in source_columns:
            values["task_canvas"] = ""
    if table_name == "artifacts":
        if "trace_refs" in target_columns and "trace_refs" not in source_columns:
            values["trace_refs"] = "[]"
        if "metadata" in target_columns and "metadata" not in source_columns:
            values["metadata"] = "{}"
    if table_name == "rejected_knowledge":
        if "trace_refs" in target_columns and "trace_refs" not in source_columns:
            values["trace_refs"] = "[]"
        if "artifact_refs" in target_columns and "artifact_refs" not in source_columns:
            values["artifact_refs"] = "[]"
        if "metadata" in target_columns and "metadata" not in source_columns:
            values["metadata"] = "{}"
    return values


def _row_exists(
    connection: sqlite3.Connection,
    table_name: str,
    columns: Sequence[str],
    values: Sequence[object],
) -> bool:
    clauses = []
    parameters: List[object] = []
    for column, value in zip(columns, values):
        if value is None:
            clauses.append("{} IS NULL".format(column))
        else:
            clauses.append("{} = ?".format(column))
            parameters.append(value)
    sql = "SELECT 1 FROM {} WHERE {} LIMIT 1".format(table_name, " AND ".join(clauses))
    row = connection.execute(sql, parameters).fetchone()
    return row is not None


def _build_backup_path(target_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = target_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir / "{}-pre-consolidation-{}.db".format(target_path.stem, stamp)


def _archive_path_for(source_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = source_path.with_name("{}-archived-{}.db".format(source_path.stem, stamp))
    counter = 1
    while candidate.exists():
        counter += 1
        candidate = source_path.with_name("{}-archived-{}-{}.db".format(source_path.stem, stamp, counter))
    return candidate


def _default_memory_level(memory_type: str) -> str:
    normalized = memory_type.strip().lower()
    if normalized in {"scenario", "workflow"}:
        return "L2"
    return "L1"


__all__ = [
    "ALLOW_CUSTOM_DB_ENV",
    "CANONICAL_DB_FILENAME",
    "ConsolidationReport",
    "DatabaseInventory",
    "LEGACY_DB_FILENAMES",
    "SingleDBConstraintError",
    "consolidate_legacy_database",
    "enforce_single_runtime_db",
    "inspect_database",
    "legacy_databases_with_data",
]
