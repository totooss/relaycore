"""Storage helpers and repository implementation for RelayCore."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Sequence, Union

from .models import (
    AgentEventRecord,
    AgentStateRecord,
    AuditLogRecord,
    CommandRecord,
    MemoryCandidateRecord,
    MemoryClusterRecord,
    MemoryOccurrenceRecord,
    SessionDigestRecord,
    SessionRecord,
)
from .token_budget import redact_structure

PathLike = Union[str, os.PathLike[str]]

DEFAULT_DB_PATH = Path("relaycore.db")
PRAGMA_STATEMENTS = (
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA busy_timeout=5000;",
    "PRAGMA foreign_keys=ON;",
)
COMMAND_STATUSES = ("pending", "claimed", "completed", "failed")
COMMAND_STATUS_TRANSITIONS = {
    "pending": frozenset(("claimed", "failed")),
    "claimed": frozenset(("pending", "completed", "failed")),
    "completed": frozenset(),
    "failed": frozenset(("pending",)),
}
MEMORY_CANDIDATE_STATUSES = frozenset(
    ("pending", "active", "merged", "corrected", "superseded", "archived", "rejected")
)


class StorageError(Exception):
    """Base class for storage-layer failures."""


class NotFoundError(StorageError):
    """Raised when a requested record does not exist."""


class InvalidTransitionError(StorageError):
    """Raised when a state transition is not allowed."""


class ValidationError(StorageError):
    """Raised when repository input fails basic validation."""


def resolve_database_path(db_path: Optional[PathLike] = None) -> Path:
    """Resolve the configured database path without creating files eagerly."""
    configured = db_path or os.environ.get("RELAYCORE_DB") or DEFAULT_DB_PATH
    return Path(configured).expanduser().resolve()


def connect_database(db_path: Optional[PathLike] = None) -> sqlite3.Connection:
    """Open a SQLite connection with the row factory needed by later phases."""
    resolved_path = resolve_database_path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(resolved_path))
    return configure_connection(connection)


def configure_connection(connection: sqlite3.Connection) -> sqlite3.Connection:
    """Apply the shared connection settings used across the project."""
    connection.row_factory = sqlite3.Row
    for statement in PRAGMA_STATEMENTS:
        connection.execute(statement)
    return connection


def bootstrap_database(db_path: Optional[PathLike] = None) -> Path:
    """Initialize the database schema and return the resolved database path."""
    from .migrations import apply_migrations

    resolved_path = resolve_database_path(db_path)
    with connect_database(resolved_path) as connection:
        apply_migrations(connection)

    return resolved_path


def utc_now() -> str:
    """Return a stable ISO-8601 timestamp for storage-layer writes."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def dumps_json(value: Any) -> str:
    """Serialize structured values consistently for SQLite."""
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def loads_json(value: Optional[str], default: Any) -> Any:
    """Deserialize stored JSON text with a predictable default."""
    if value in (None, ""):
        return default
    return json.loads(value)


def ensure_json_object(name: str, value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValidationError("{} must be a JSON object".format(name))
    return value


def ensure_json_list(name: str, value: Optional[List[Any]]) -> List[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError("{} must be a JSON list".format(name))
    return value


def row_to_session(row: sqlite3.Row) -> SessionRecord:
    return SessionRecord(
        session_id=row["session_id"],
        name=row["name"],
        goal=row["goal"],
        mode=row["mode"],
        status=row["status"],
        created_by=row["created_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        metadata=loads_json(row["metadata"], {}),
    )


def row_to_command(row: sqlite3.Row) -> CommandRecord:
    return CommandRecord(
        command_id=row["command_id"],
        session_id=row["session_id"],
        target_agent=row["target_agent"],
        target_runtime=row["target_runtime"],
        mode=row["mode"],
        command_type=row["command_type"],
        payload=loads_json(row["payload"], {}),
        status=row["status"],
        priority=row["priority"],
        created_by=row["created_by"],
        created_at=row["created_at"],
        claimed_by=row["claimed_by"],
        claimed_at=row["claimed_at"],
        lease_expires_at=row["lease_expires_at"],
        completed_at=row["completed_at"],
        result=loads_json(row["result"], {}),
        idempotency_key=row["idempotency_key"],
        permission_level=row["permission_level"],
    )


def row_to_agent_event(row: sqlite3.Row) -> AgentEventRecord:
    return AgentEventRecord(
        seq=row["seq"],
        session_id=row["session_id"],
        agent_id=row["agent_id"],
        runtime=row["runtime"],
        mode=row["mode"],
        event_type=row["event_type"],
        content=loads_json(row["content"], {}),
        command_id=row["command_id"],
        parent_seq=row["parent_seq"],
        metadata=loads_json(row["metadata"], {}),
        created_at=row["created_at"],
    )


def row_to_agent_state(row: sqlite3.Row) -> AgentStateRecord:
    return AgentStateRecord(
        agent_id=row["agent_id"],
        runtime=row["runtime"],
        session_id=row["session_id"],
        role=row["role"],
        status=row["status"],
        last_seen_seq=row["last_seen_seq"],
        last_heartbeat=row["last_heartbeat"],
        current_task=row["current_task"],
        capabilities=loads_json(row["capabilities"], []),
        metadata=loads_json(row["metadata"], {}),
    )


def row_to_session_digest(row: sqlite3.Row) -> SessionDigestRecord:
    return SessionDigestRecord(
        digest_id=row["digest_id"],
        session_id=row["session_id"],
        from_seq=row["from_seq"],
        to_seq=row["to_seq"],
        summary=row["summary"],
        decisions=loads_json(row["decisions"], []),
        open_questions=loads_json(row["open_questions"], []),
        rejected_candidates=loads_json(row["rejected_candidates"], []),
        created_at=row["created_at"],
    )


def row_to_memory_candidate(row: sqlite3.Row) -> MemoryCandidateRecord:
    return MemoryCandidateRecord(
        candidate_id=row["candidate_id"],
        proposed_by=row["proposed_by"],
        runtime=row["runtime"],
        session_id=row["session_id"],
        type=row["type"],
        title=row["title"],
        content=row["content"],
        summary=row["summary"],
        rejected=loads_json(row["rejected"], []),
        tags=loads_json(row["tags"], []),
        status=row["status"],
        similar_to=loads_json(row["similar_to"], []),
        conflicts_with=loads_json(row["conflicts_with"], []),
        recommended_action=row["recommended_action"],
        created_at=row["created_at"],
        resolved_at=row["resolved_at"],
    )


def row_to_memory_occurrence(row: sqlite3.Row) -> MemoryOccurrenceRecord:
    return MemoryOccurrenceRecord(
        id=row["id"],
        memory_id=row["memory_id"],
        agent_id=row["agent_id"],
        runtime=row["runtime"],
        session_id=row["session_id"],
        observed_at=row["observed_at"],
        note=row["note"],
    )


def row_to_memory_cluster(row: sqlite3.Row) -> MemoryClusterRecord:
    return MemoryClusterRecord(
        cluster_id=row["cluster_id"],
        canonical_memory_id=row["canonical_memory_id"],
        summary=row["summary"],
        tags=loads_json(row["tags"], []),
        source_count=row["source_count"],
        quality_score=row["quality_score"],
        updated_at=row["updated_at"],
        metadata=loads_json(row["metadata"], {}),
    )


def row_to_audit_log(row: sqlite3.Row) -> AuditLogRecord:
    return AuditLogRecord(
        id=row["id"],
        actor=row["actor"],
        action=row["action"],
        resource_type=row["resource_type"],
        resource_id=row["resource_id"],
        request_id=row["request_id"],
        ip=row["ip"],
        metadata=loads_json(row["metadata"], {}),
        created_at=row["created_at"],
    )


class RelayCoreStorage:
    """Repository layer for core RelayCore persistence operations."""

    def __init__(
        self,
        db_path: Optional[PathLike] = None,
        connection: Optional[sqlite3.Connection] = None,
        auto_bootstrap: bool = True,
    ) -> None:
        self.db_path = resolve_database_path(db_path)
        self.connection = connection or connect_database(self.db_path)
        self._owns_connection = connection is None
        if auto_bootstrap:
            from .migrations import apply_migrations

            apply_migrations(self.connection)

    def close(self) -> None:
        if self._owns_connection:
            self.connection.close()

    def __enter__(self) -> "RelayCoreStorage":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def _fetch_one(self, sql: str, parameters: Sequence[Any], message: str) -> sqlite3.Row:
        row = self.connection.execute(sql, tuple(parameters)).fetchone()
        if row is None:
            raise NotFoundError(message)
        return row

    def _insert(self, table: str, values: Dict[str, Any]) -> None:
        columns = list(values.keys())
        placeholders = ", ".join("?" for _ in columns)
        sql = "INSERT INTO {} ({}) VALUES ({})".format(table, ", ".join(columns), placeholders)
        self.connection.execute(sql, [values[column] for column in columns])
        self.connection.commit()

    def _update(self, table: str, key_column: str, key_value: Any, values: Dict[str, Any]) -> None:
        if not values:
            return
        assignments = ", ".join("{} = ?".format(column) for column in values)
        sql = "UPDATE {} SET {} WHERE {} = ?".format(table, assignments, key_column)
        parameters = [values[column] for column in values] + [key_value]
        cursor = self.connection.execute(sql, parameters)
        if cursor.rowcount == 0:
            raise NotFoundError("{}={!r} not found".format(key_column, key_value))
        self.connection.commit()

    def create_session(
        self,
        session_id: str,
        name: str,
        goal: str,
        mode: str,
        created_by: str,
        status: str = "active",
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> SessionRecord:
        timestamp = created_at or utc_now()
        self._insert(
            "sessions",
            {
                "session_id": session_id,
                "name": name,
                "goal": goal,
                "mode": mode,
                "status": status,
                "created_by": created_by,
                "created_at": timestamp,
                "updated_at": updated_at or timestamp,
                "metadata": dumps_json(ensure_json_object("metadata", metadata)),
            },
        )
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> SessionRecord:
        row = self._fetch_one(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,),
            "session {!r} not found".format(session_id),
        )
        return row_to_session(row)

    def list_sessions(self, status: Optional[str] = None) -> List[SessionRecord]:
        sql = "SELECT * FROM sessions"
        parameters: List[Any] = []
        if status is not None:
            sql += " WHERE status = ?"
            parameters.append(status)
        sql += " ORDER BY updated_at DESC, created_at DESC"
        rows = self.connection.execute(sql, parameters).fetchall()
        return [row_to_session(row) for row in rows]

    def update_session(
        self,
        session_id: str,
        *,
        name: Optional[str] = None,
        goal: Optional[str] = None,
        mode: Optional[str] = None,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionRecord:
        current = self.get_session(session_id)
        values: Dict[str, Any] = {"updated_at": utc_now()}
        if name is not None:
            values["name"] = name
        if goal is not None:
            values["goal"] = goal
        if mode is not None:
            values["mode"] = mode
        if status is not None:
            values["status"] = status
        if metadata is not None:
            merged = dict(current.metadata)
            merged.update(ensure_json_object("metadata", metadata))
            values["metadata"] = dumps_json(merged)
        self._update("sessions", "session_id", session_id, values)
        return self.get_session(session_id)

    def delete_session(self, session_id: str) -> None:
        cursor = self.connection.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        if cursor.rowcount == 0:
            raise NotFoundError("session {!r} not found".format(session_id))
        self.connection.commit()

    def create_command(
        self,
        command_id: str,
        session_id: str,
        mode: str,
        command_type: str,
        payload: Dict[str, Any],
        created_by: str,
        target_agent: Optional[str] = None,
        target_runtime: Optional[str] = None,
        status: str = "pending",
        priority: int = 100,
        result: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        permission_level: str = "L1",
        created_at: Optional[str] = None,
    ) -> CommandRecord:
        if status not in COMMAND_STATUSES:
            raise ValidationError("unsupported command status {!r}".format(status))
        self._insert(
            "commands",
            {
                "command_id": command_id,
                "session_id": session_id,
                "target_agent": target_agent,
                "target_runtime": target_runtime,
                "mode": mode,
                "command_type": command_type,
                "payload": dumps_json(ensure_json_object("payload", payload)),
                "status": status,
                "priority": priority,
                "created_by": created_by,
                "created_at": created_at or utc_now(),
                "claimed_by": None,
                "claimed_at": None,
                "lease_expires_at": None,
                "completed_at": None,
                "result": dumps_json(ensure_json_object("result", result)),
                "idempotency_key": idempotency_key,
                "permission_level": permission_level,
            },
        )
        return self.get_command(command_id)

    def get_command(self, command_id: str) -> CommandRecord:
        row = self._fetch_one(
            "SELECT * FROM commands WHERE command_id = ?",
            (command_id,),
            "command {!r} not found".format(command_id),
        )
        return row_to_command(row)

    def list_commands(
        self,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        target_runtime: Optional[str] = None,
        target_agent: Optional[str] = None,
        limit: int = 50,
    ) -> List[CommandRecord]:
        clauses: List[str] = []
        parameters: List[Any] = []
        if session_id is not None:
            clauses.append("session_id = ?")
            parameters.append(session_id)
        if status is not None:
            clauses.append("status = ?")
            parameters.append(status)
        if target_runtime is not None:
            clauses.append("target_runtime = ?")
            parameters.append(target_runtime)
        if target_agent is not None:
            clauses.append("target_agent = ?")
            parameters.append(target_agent)
        sql = "SELECT * FROM commands"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY priority ASC, created_at ASC LIMIT ?"
        parameters.append(limit)
        rows = self.connection.execute(sql, parameters).fetchall()
        return [row_to_command(row) for row in rows]

    def update_command_status(
        self,
        command_id: str,
        new_status: str,
        *,
        claimed_by: Optional[str] = None,
        lease_expires_at: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        completed_at: Optional[str] = None,
    ) -> CommandRecord:
        command = self.get_command(command_id)
        if new_status not in COMMAND_STATUSES:
            raise ValidationError("unsupported command status {!r}".format(new_status))
        allowed = COMMAND_STATUS_TRANSITIONS[command.status]
        if new_status != command.status and new_status not in allowed:
            raise InvalidTransitionError(
                "cannot transition command {} from {} to {}".format(command_id, command.status, new_status)
            )

        values: Dict[str, Any] = {"status": new_status}
        now = utc_now()

        if new_status == "claimed":
            if not claimed_by:
                raise ValidationError("claimed_by is required when claiming a command")
            values["claimed_by"] = claimed_by
            values["claimed_at"] = now
            values["lease_expires_at"] = lease_expires_at
            values["completed_at"] = None
        elif new_status == "pending":
            values["claimed_by"] = None
            values["claimed_at"] = None
            values["lease_expires_at"] = None
            if result is not None:
                values["result"] = dumps_json(ensure_json_object("result", result))
        elif new_status == "completed":
            if result is None:
                raise ValidationError("result is required when completing a command")
            values["result"] = dumps_json(ensure_json_object("result", result))
            values["completed_at"] = completed_at or now
            values["lease_expires_at"] = None
        elif new_status == "failed":
            values["lease_expires_at"] = None
            if result is not None:
                values["result"] = dumps_json(ensure_json_object("result", result))
            if command.status == "claimed":
                values["completed_at"] = completed_at or now

        self._update("commands", "command_id", command_id, values)
        return self.get_command(command_id)

    def delete_command(self, command_id: str) -> None:
        cursor = self.connection.execute("DELETE FROM commands WHERE command_id = ?", (command_id,))
        if cursor.rowcount == 0:
            raise NotFoundError("command {!r} not found".format(command_id))
        self.connection.commit()

    def append_event(
        self,
        session_id: str,
        agent_id: str,
        event_type: str,
        content: Dict[str, Any],
        runtime: Optional[str] = None,
        mode: Optional[str] = None,
        command_id: Optional[str] = None,
        parent_seq: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
    ) -> AgentEventRecord:
        values = {
            "session_id": session_id,
            "agent_id": agent_id,
            "runtime": runtime,
            "mode": mode,
            "event_type": event_type,
            "content": dumps_json(ensure_json_object("content", content)),
            "command_id": command_id,
            "parent_seq": parent_seq,
            "metadata": dumps_json(ensure_json_object("metadata", metadata)),
            "created_at": created_at or utc_now(),
        }
        columns = list(values.keys())
        placeholders = ", ".join("?" for _ in columns)
        cursor = self.connection.execute(
            "INSERT INTO agent_events ({}) VALUES ({})".format(", ".join(columns), placeholders),
            [values[column] for column in columns],
        )
        self.connection.commit()
        return self.get_event(cursor.lastrowid)

    def get_event(self, seq: int) -> AgentEventRecord:
        row = self._fetch_one(
            "SELECT * FROM agent_events WHERE seq = ?",
            (seq,),
            "event {!r} not found".format(seq),
        )
        return row_to_agent_event(row)

    def list_events(
        self,
        session_id: str,
        after_seq: Optional[int] = None,
        limit: int = 100,
    ) -> List[AgentEventRecord]:
        sql = "SELECT * FROM agent_events WHERE session_id = ?"
        parameters: List[Any] = [session_id]
        if after_seq is not None:
            sql += " AND seq > ?"
            parameters.append(after_seq)
        sql += " ORDER BY seq ASC LIMIT ?"
        parameters.append(limit)
        rows = self.connection.execute(sql, parameters).fetchall()
        return [row_to_agent_event(row) for row in rows]

    def count_events(self, session_id: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM agent_events WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return int(row[0])

    def list_events_window(
        self,
        session_id: str,
        from_seq: int,
        limit: int = 10,
    ) -> List[AgentEventRecord]:
        rows = self.connection.execute(
            """
            SELECT * FROM agent_events
            WHERE session_id = ? AND seq >= ?
            ORDER BY seq ASC
            LIMIT ?
            """,
            (session_id, from_seq, limit),
        ).fetchall()
        return [row_to_agent_event(row) for row in rows]

    def upsert_agent_state(
        self,
        agent_id: str,
        runtime: str,
        *,
        session_id: Optional[str] = None,
        role: Optional[str] = None,
        status: str = "idle",
        last_seen_seq: int = 0,
        last_heartbeat: Optional[str] = None,
        current_task: Optional[str] = None,
        capabilities: Optional[List[Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentStateRecord:
        self.connection.execute(
            """
            INSERT INTO agent_states (
              agent_id, runtime, session_id, role, status,
              last_seen_seq, last_heartbeat, current_task, capabilities, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
              runtime = excluded.runtime,
              session_id = excluded.session_id,
              role = excluded.role,
              status = excluded.status,
              last_seen_seq = excluded.last_seen_seq,
              last_heartbeat = excluded.last_heartbeat,
              current_task = excluded.current_task,
              capabilities = excluded.capabilities,
              metadata = excluded.metadata
            """,
            (
                agent_id,
                runtime,
                session_id,
                role,
                status,
                last_seen_seq,
                last_heartbeat or utc_now(),
                current_task,
                dumps_json(ensure_json_list("capabilities", capabilities)),
                dumps_json(ensure_json_object("metadata", metadata)),
            ),
        )
        self.connection.commit()
        return self.get_agent_state(agent_id)

    def get_agent_state(self, agent_id: str) -> AgentStateRecord:
        row = self._fetch_one(
            "SELECT * FROM agent_states WHERE agent_id = ?",
            (agent_id,),
            "agent state {!r} not found".format(agent_id),
        )
        return row_to_agent_state(row)

    def list_agent_states(
        self,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[AgentStateRecord]:
        clauses: List[str] = []
        parameters: List[Any] = []
        if session_id is not None:
            clauses.append("session_id = ?")
            parameters.append(session_id)
        if status is not None:
            clauses.append("status = ?")
            parameters.append(status)
        sql = "SELECT * FROM agent_states"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY last_heartbeat DESC LIMIT ?"
        parameters.append(limit)
        rows = self.connection.execute(sql, parameters).fetchall()
        return [row_to_agent_state(row) for row in rows]

    def create_session_digest(
        self,
        digest_id: str,
        session_id: str,
        from_seq: int,
        to_seq: int,
        summary: str,
        decisions: Optional[List[Any]] = None,
        open_questions: Optional[List[Any]] = None,
        rejected_candidates: Optional[List[Any]] = None,
        created_at: Optional[str] = None,
    ) -> SessionDigestRecord:
        self._insert(
            "session_digests",
            {
                "digest_id": digest_id,
                "session_id": session_id,
                "from_seq": from_seq,
                "to_seq": to_seq,
                "summary": summary,
                "decisions": dumps_json(ensure_json_list("decisions", decisions)),
                "open_questions": dumps_json(ensure_json_list("open_questions", open_questions)),
                "rejected_candidates": dumps_json(ensure_json_list("rejected_candidates", rejected_candidates)),
                "created_at": created_at or utc_now(),
            },
        )
        return self.get_session_digest(digest_id)

    def get_session_digest(self, digest_id: str) -> SessionDigestRecord:
        row = self._fetch_one(
            "SELECT * FROM session_digests WHERE digest_id = ?",
            (digest_id,),
            "digest {!r} not found".format(digest_id),
        )
        return row_to_session_digest(row)

    def list_session_digests(self, session_id: str, limit: int = 20) -> List[SessionDigestRecord]:
        rows = self.connection.execute(
            """
            SELECT * FROM session_digests
            WHERE session_id = ?
            ORDER BY to_seq DESC, created_at DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
        return [row_to_session_digest(row) for row in rows]

    def get_latest_session_digest(self, session_id: str) -> Optional[SessionDigestRecord]:
        row = self.connection.execute(
            """
            SELECT * FROM session_digests
            WHERE session_id = ?
            ORDER BY to_seq DESC, created_at DESC
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return row_to_session_digest(row)

    def create_memory_candidate(
        self,
        candidate_id: str,
        proposed_by: str,
        type: str,
        title: str,
        content: str,
        runtime: Optional[str] = None,
        session_id: Optional[str] = None,
        summary: str = "",
        rejected: Optional[List[Any]] = None,
        tags: Optional[List[Any]] = None,
        status: str = "pending",
        similar_to: Optional[List[Any]] = None,
        conflicts_with: Optional[List[Any]] = None,
        recommended_action: str = "",
        created_at: Optional[str] = None,
        resolved_at: Optional[str] = None,
    ) -> MemoryCandidateRecord:
        if status not in MEMORY_CANDIDATE_STATUSES:
            raise ValidationError("unsupported memory candidate status {!r}".format(status))
        self._insert(
            "memory_candidates",
            {
                "candidate_id": candidate_id,
                "proposed_by": proposed_by,
                "runtime": runtime,
                "session_id": session_id,
                "type": type,
                "title": title,
                "content": content,
                "summary": summary,
                "rejected": dumps_json(ensure_json_list("rejected", rejected)),
                "tags": dumps_json(ensure_json_list("tags", tags)),
                "status": status,
                "similar_to": dumps_json(ensure_json_list("similar_to", similar_to)),
                "conflicts_with": dumps_json(ensure_json_list("conflicts_with", conflicts_with)),
                "recommended_action": recommended_action,
                "created_at": created_at or utc_now(),
                "resolved_at": resolved_at,
            },
        )
        return self.get_memory_candidate(candidate_id)

    def get_memory_candidate(self, candidate_id: str) -> MemoryCandidateRecord:
        row = self._fetch_one(
            "SELECT * FROM memory_candidates WHERE candidate_id = ?",
            (candidate_id,),
            "memory candidate {!r} not found".format(candidate_id),
        )
        return row_to_memory_candidate(row)

    def list_memory_candidates(
        self,
        status: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MemoryCandidateRecord]:
        clauses: List[str] = []
        parameters: List[Any] = []
        if status is not None:
            clauses.append("status = ?")
            parameters.append(status)
        if session_id is not None:
            clauses.append("session_id = ?")
            parameters.append(session_id)
        sql = "SELECT * FROM memory_candidates"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC LIMIT ?"
        parameters.append(limit)
        rows = self.connection.execute(sql, parameters).fetchall()
        return [row_to_memory_candidate(row) for row in rows]

    def update_memory_candidate(
        self,
        candidate_id: str,
        *,
        summary: Optional[str] = None,
        rejected: Optional[List[Any]] = None,
        tags: Optional[List[Any]] = None,
        status: Optional[str] = None,
        similar_to: Optional[List[Any]] = None,
        conflicts_with: Optional[List[Any]] = None,
        recommended_action: Optional[str] = None,
        resolved_at: Optional[str] = None,
    ) -> MemoryCandidateRecord:
        values: Dict[str, Any] = {}
        if summary is not None:
            values["summary"] = summary
        if rejected is not None:
            values["rejected"] = dumps_json(ensure_json_list("rejected", rejected))
        if tags is not None:
            values["tags"] = dumps_json(ensure_json_list("tags", tags))
        if status is not None:
            if status not in MEMORY_CANDIDATE_STATUSES:
                raise ValidationError("unsupported memory candidate status {!r}".format(status))
            values["status"] = status
        if similar_to is not None:
            values["similar_to"] = dumps_json(ensure_json_list("similar_to", similar_to))
        if conflicts_with is not None:
            values["conflicts_with"] = dumps_json(ensure_json_list("conflicts_with", conflicts_with))
        if recommended_action is not None:
            values["recommended_action"] = recommended_action
        if resolved_at is not None:
            values["resolved_at"] = resolved_at
        self._update("memory_candidates", "candidate_id", candidate_id, values)
        return self.get_memory_candidate(candidate_id)

    def resolve_memory_candidate(
        self,
        candidate_id: str,
        status: str,
        *,
        recommended_action: Optional[str] = None,
        resolved_at: Optional[str] = None,
    ) -> MemoryCandidateRecord:
        if status == "pending" or status not in MEMORY_CANDIDATE_STATUSES:
            raise ValidationError("memory candidate resolution status must be supported and non-pending")
        values: Dict[str, Any] = {
            "status": status,
            "resolved_at": resolved_at or utc_now(),
        }
        if recommended_action is not None:
            values["recommended_action"] = recommended_action
        self._update("memory_candidates", "candidate_id", candidate_id, values)
        return self.get_memory_candidate(candidate_id)

    def record_memory_occurrence(
        self,
        memory_id: str,
        agent_id: str,
        runtime: Optional[str] = None,
        session_id: Optional[str] = None,
        observed_at: Optional[str] = None,
        note: str = "",
    ) -> MemoryOccurrenceRecord:
        values = {
            "memory_id": memory_id,
            "agent_id": agent_id,
            "runtime": runtime,
            "session_id": session_id,
            "observed_at": observed_at or utc_now(),
            "note": note,
        }
        columns = list(values.keys())
        placeholders = ", ".join("?" for _ in columns)
        cursor = self.connection.execute(
            "INSERT INTO memory_occurrences ({}) VALUES ({})".format(", ".join(columns), placeholders),
            [values[column] for column in columns],
        )
        self.connection.commit()
        row = self._fetch_one(
            "SELECT * FROM memory_occurrences WHERE id = ?",
            (cursor.lastrowid,),
            "memory occurrence not found after insert",
        )
        return row_to_memory_occurrence(row)

    def list_memory_occurrences(self, memory_id: str, limit: int = 100) -> List[MemoryOccurrenceRecord]:
        rows = self.connection.execute(
            """
            SELECT * FROM memory_occurrences
            WHERE memory_id = ?
            ORDER BY observed_at DESC, id DESC
            LIMIT ?
            """,
            (memory_id, limit),
        ).fetchall()
        return [row_to_memory_occurrence(row) for row in rows]

    def upsert_memory_cluster(
        self,
        cluster_id: str,
        canonical_memory_id: str,
        summary: str,
        tags: Optional[List[Any]] = None,
        source_count: int = 1,
        quality_score: float = 0.5,
        updated_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryClusterRecord:
        self.connection.execute(
            """
            INSERT INTO memory_clusters (
              cluster_id, canonical_memory_id, summary, tags,
              source_count, quality_score, updated_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cluster_id) DO UPDATE SET
              canonical_memory_id = excluded.canonical_memory_id,
              summary = excluded.summary,
              tags = excluded.tags,
              source_count = excluded.source_count,
              quality_score = excluded.quality_score,
              updated_at = excluded.updated_at,
              metadata = excluded.metadata
            """,
            (
                cluster_id,
                canonical_memory_id,
                summary,
                dumps_json(ensure_json_list("tags", tags)),
                source_count,
                quality_score,
                updated_at or utc_now(),
                dumps_json(ensure_json_object("metadata", metadata)),
            ),
        )
        self.connection.commit()
        return self.get_memory_cluster(cluster_id)

    def get_memory_cluster(self, cluster_id: str) -> MemoryClusterRecord:
        row = self._fetch_one(
            "SELECT * FROM memory_clusters WHERE cluster_id = ?",
            (cluster_id,),
            "memory cluster {!r} not found".format(cluster_id),
        )
        return row_to_memory_cluster(row)

    def list_memory_clusters(self, limit: int = 100) -> List[MemoryClusterRecord]:
        rows = self.connection.execute(
            "SELECT * FROM memory_clusters ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [row_to_memory_cluster(row) for row in rows]

    def get_memory_cluster_by_canonical(self, canonical_memory_id: str) -> Optional[MemoryClusterRecord]:
        row = self.connection.execute(
            "SELECT * FROM memory_clusters WHERE canonical_memory_id = ? ORDER BY updated_at DESC LIMIT 1",
            (canonical_memory_id,),
        ).fetchone()
        if row is None:
            return None
        return row_to_memory_cluster(row)

    def append_audit_log(
        self,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        request_id: Optional[str] = None,
        ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
    ) -> AuditLogRecord:
        values = {
            "actor": actor,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "request_id": request_id,
            "ip": ip,
            "metadata": dumps_json(ensure_json_object("metadata", metadata)),
            "created_at": created_at or utc_now(),
        }
        columns = list(values.keys())
        placeholders = ", ".join("?" for _ in columns)
        cursor = self.connection.execute(
            "INSERT INTO audit_logs ({}) VALUES ({})".format(", ".join(columns), placeholders),
            [values[column] for column in columns],
        )
        self.connection.commit()
        row = self._fetch_one(
            "SELECT * FROM audit_logs WHERE id = ?",
            (cursor.lastrowid,),
            "audit log not found after insert",
        )
        return row_to_audit_log(row)

    def list_audit_logs(
        self,
        actor: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditLogRecord]:
        clauses: List[str] = []
        parameters: List[Any] = []
        if actor is not None:
            clauses.append("actor = ?")
            parameters.append(actor)
        if resource_type is not None:
            clauses.append("resource_type = ?")
            parameters.append(resource_type)
        if resource_id is not None:
            clauses.append("resource_id = ?")
            parameters.append(resource_id)
        sql = "SELECT * FROM audit_logs"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
        parameters.append(limit)
        rows = self.connection.execute(sql, parameters).fetchall()
        return [row_to_audit_log(row) for row in rows]

    def export_snapshot(self, *, redact: bool = True) -> Dict[str, Any]:
        table_names = [
            "sessions",
            "commands",
            "agent_events",
            "agent_states",
            "session_digests",
            "memory_candidates",
            "memory_occurrences",
            "memory_clusters",
            "artifacts",
            "audit_logs",
        ]
        snapshot: Dict[str, Any] = {"exported_at": utc_now(), "tables": {}}
        for table_name in table_names:
            rows = self.connection.execute("SELECT * FROM {}".format(table_name)).fetchall()
            values = [dict(row) for row in rows]
            snapshot["tables"][table_name] = redact_structure(values) if redact else values
        return snapshot

    def backup_database(self, target_path: PathLike) -> Path:
        resolved = resolve_database_path(target_path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self.connection.commit()
        destination = sqlite3.connect(str(resolved))
        try:
            self.connection.backup(destination)
            destination.commit()
        finally:
            destination.close()
        return resolved


__all__ = [
    "COMMAND_STATUSES",
    "COMMAND_STATUS_TRANSITIONS",
    "DEFAULT_DB_PATH",
    "RelayCoreStorage",
    "InvalidTransitionError",
    "MEMORY_CANDIDATE_STATUSES",
    "NotFoundError",
    "PRAGMA_STATEMENTS",
    "StorageError",
    "ValidationError",
    "bootstrap_database",
    "configure_connection",
    "connect_database",
    "resolve_database_path",
    "utc_now",
]
