"""Command bus service logic for EchoMemory."""

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

from .models import CommandRecord
from .runtime_adapters import CollaborationModeRegistry
from .storage import EchoMemoryStorage, row_to_command, utc_now

if TYPE_CHECKING:
    from .event_log import EventLogService

PERMISSION_RANKS = {"L1": 1, "L2": 2, "L3": 3}
DEFAULT_LEASE_SECONDS = 300
MAX_LIST_LIMIT = 200


class CommandBusError(Exception):
    """Base class for command bus failures."""


class BadRequestError(CommandBusError):
    """Raised when a request payload is invalid."""


class PermissionDeniedError(CommandBusError):
    """Raised when a caller does not have enough permission."""


class ConflictError(CommandBusError):
    """Raised when a command cannot be modified due to current state."""


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def serialize_command(command: CommandRecord) -> Dict[str, Any]:
    return asdict(command)


class CommandBusService:
    """Validate and coordinate command lifecycle operations."""

    def __init__(
        self,
        storage: EchoMemoryStorage,
        event_log: Optional["EventLogService"] = None,
        collaboration_modes: Optional[CollaborationModeRegistry] = None,
    ) -> None:
        self.storage = storage
        self.event_log = event_log
        self.collaboration_modes = collaboration_modes or CollaborationModeRegistry()

    def publish_command(
        self,
        *,
        session_id: str,
        mode: str,
        command_type: str,
        payload: Dict[str, Any],
        created_by: str,
        target_agent: Optional[str] = None,
        target_runtime: Optional[str] = None,
        priority: int = 100,
        permission_level: str = "L1",
        idempotency_key: Optional[str] = None,
    ) -> CommandRecord:
        self._validate_permission_level(permission_level)
        self._validate_target_routing(target_agent, target_runtime)
        self._ensure_non_empty("session_id", session_id)
        self._ensure_non_empty("mode", mode)
        self._ensure_non_empty("command_type", command_type)
        self._ensure_non_empty("created_by", created_by)
        if not isinstance(payload, dict):
            raise BadRequestError("payload must be an object")

        if idempotency_key:
            existing = self._find_command_by_idempotency_key(idempotency_key)
            if existing is not None:
                return existing

        template = self.collaboration_modes.get(mode)
        enriched_payload = dict(payload)
        enriched_payload.setdefault("collaboration", template.to_payload())
        enriched_payload.setdefault("participants", template.participants)

        command = self.storage.create_command(
            command_id=self._generate_command_id(),
            session_id=session_id,
            target_agent=target_agent,
            target_runtime=target_runtime,
            mode=template.name,
            command_type=command_type,
            payload=enriched_payload,
            created_by=created_by,
            priority=priority,
            idempotency_key=idempotency_key,
            permission_level=permission_level,
        )
        self.storage.append_audit_log(
            actor=created_by,
            action="command_publish",
            resource_type="command",
            resource_id=command.command_id,
            metadata={
                "session_id": session_id,
                "target_agent": target_agent,
                "target_runtime": target_runtime,
                "permission_level": permission_level,
            },
        )
        self._append_command_event(
            command,
            event_type="command_published",
            actor=created_by,
            content={
                "command_id": command.command_id,
                "command_type": command.command_type,
                "status": command.status,
                "target_agent": command.target_agent,
                "target_runtime": command.target_runtime,
                "permission_level": command.permission_level,
                "collaboration_mode": template.name,
                "participants": template.participants,
            },
        )
        self._append_command_event(
            command,
            event_type="collaboration_mode_started",
            actor=created_by,
            content={
                "command_id": command.command_id,
                "collaboration_mode": template.name,
                "participants": template.participants,
                "workflow": template.workflow,
            },
        )
        return command

    def find_command_by_idempotency_key(self, idempotency_key: str) -> Optional[CommandRecord]:
        """Return the existing command for an idempotency key, if present."""
        return self._find_command_by_idempotency_key(idempotency_key)

    def list_pending_commands(
        self,
        *,
        requester_permission_level: str,
        session_id: Optional[str] = None,
        target_runtime: Optional[str] = None,
        target_agent: Optional[str] = None,
        limit: int = 50,
        now: Optional[datetime] = None,
    ) -> List[CommandRecord]:
        self._validate_permission_level(requester_permission_level)
        self.recover_expired_claims(now=now)
        bounded_limit = max(1, min(limit, MAX_LIST_LIMIT))
        commands = self.storage.list_commands(
            session_id=session_id,
            status="pending",
            target_runtime=target_runtime,
            target_agent=target_agent,
            limit=bounded_limit,
        )
        return [
            command
            for command in commands
            if self._has_permission(requester_permission_level, command.permission_level)
        ]

    def claim_command(
        self,
        command_id: str,
        *,
        claimed_by: str,
        requester_permission_level: str,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
        now: Optional[datetime] = None,
    ) -> CommandRecord:
        self._validate_permission_level(requester_permission_level)
        self._ensure_non_empty("claimed_by", claimed_by)
        if lease_seconds <= 0:
            raise BadRequestError("lease_seconds must be positive")

        command = self._get_command_after_recovery(command_id, now=now)
        self._enforce_permission(requester_permission_level, command.permission_level)

        if command.status != "pending":
            raise ConflictError("command is not available for claiming")

        lease_expires_at = format_timestamp((now or self._now()).astimezone(timezone.utc) + timedelta(seconds=lease_seconds))
        claimed = self.storage.update_command_status(
            command_id,
            "claimed",
            claimed_by=claimed_by,
            lease_expires_at=lease_expires_at,
        )
        self.storage.append_audit_log(
            actor=claimed_by,
            action="command_claim",
            resource_type="command",
            resource_id=command_id,
            metadata={"lease_expires_at": lease_expires_at},
        )
        self._append_command_event(
            claimed,
            event_type="command_claimed",
            actor=claimed_by,
            content={
                "command_id": claimed.command_id,
                "status": claimed.status,
                "lease_expires_at": lease_expires_at,
            },
        )
        return claimed

    def complete_command(
        self,
        command_id: str,
        *,
        claimed_by: str,
        result: Dict[str, Any],
        requester_permission_level: str,
        now: Optional[datetime] = None,
    ) -> CommandRecord:
        self._validate_permission_level(requester_permission_level)
        self._ensure_non_empty("claimed_by", claimed_by)
        if not isinstance(result, dict):
            raise BadRequestError("result must be an object")

        command = self._get_command_after_recovery(command_id, now=now)
        self._enforce_permission(requester_permission_level, command.permission_level)
        self._ensure_claim_owner(command, claimed_by)

        completed = self.storage.update_command_status(
            command_id,
            "completed",
            result=result,
            completed_at=format_timestamp(now or self._now()),
        )
        self.storage.append_audit_log(
            actor=claimed_by,
            action="command_complete",
            resource_type="command",
            resource_id=command_id,
            metadata={"result_keys": sorted(result.keys())},
        )
        self._append_command_event(
            completed,
            event_type="command_completed",
            actor=claimed_by,
            content={
                "command_id": completed.command_id,
                "status": completed.status,
                "result": result,
            },
        )
        return completed

    def fail_command(
        self,
        command_id: str,
        *,
        claimed_by: str,
        result: Optional[Dict[str, Any]],
        requester_permission_level: str,
        now: Optional[datetime] = None,
    ) -> CommandRecord:
        self._validate_permission_level(requester_permission_level)
        self._ensure_non_empty("claimed_by", claimed_by)
        if result is not None and not isinstance(result, dict):
            raise BadRequestError("result must be an object")

        command = self._get_command_after_recovery(command_id, now=now)
        self._enforce_permission(requester_permission_level, command.permission_level)
        self._ensure_claim_owner(command, claimed_by)

        failed = self.storage.update_command_status(
            command_id,
            "failed",
            result=result or {"status": "failed"},
            completed_at=format_timestamp(now or self._now()),
        )
        self.storage.append_audit_log(
            actor=claimed_by,
            action="command_fail",
            resource_type="command",
            resource_id=command_id,
            metadata={"result_keys": sorted((result or {"status": "failed"}).keys())},
        )
        self._append_command_event(
            failed,
            event_type="command_failed",
            actor=claimed_by,
            content={
                "command_id": failed.command_id,
                "status": failed.status,
                "result": result or {"status": "failed"},
            },
        )
        return failed

    def recover_expired_claims(self, *, now: Optional[datetime] = None) -> int:
        current_time = now or self._now()
        recovered = 0
        claimed_commands = self.storage.list_commands(status="claimed", limit=MAX_LIST_LIMIT)
        for command in claimed_commands:
            if not command.lease_expires_at:
                continue
            if parse_timestamp(command.lease_expires_at) <= current_time.astimezone(timezone.utc):
                self.storage.update_command_status(
                    command.command_id,
                    "pending",
                    result={"recovered_from": command.claimed_by or "unknown"},
                )
                self.storage.append_audit_log(
                    actor="system",
                    action="command_lease_recover",
                    resource_type="command",
                    resource_id=command.command_id,
                    metadata={"expired_claimed_by": command.claimed_by},
                )
                refreshed = self.storage.get_command(command.command_id)
                self._append_command_event(
                    refreshed,
                    event_type="command_recovered",
                    actor="system",
                    content={
                        "command_id": refreshed.command_id,
                        "status": refreshed.status,
                        "expired_claimed_by": command.claimed_by,
                    },
                )
                recovered += 1
        return recovered

    def _append_command_event(
        self,
        command: CommandRecord,
        *,
        event_type: str,
        actor: str,
        content: Dict[str, Any],
    ) -> None:
        if self.event_log is None:
            return
        self.event_log.append_event(
            session_id=command.session_id,
            agent_id=actor,
            runtime=command.target_runtime,
            mode=command.mode,
            event_type=event_type,
            content=content,
            command_id=command.command_id,
            metadata={"source": "command_bus"},
        )

    def _find_command_by_idempotency_key(self, idempotency_key: str) -> Optional[CommandRecord]:
        row = self.storage.connection.execute(
            "SELECT * FROM commands WHERE idempotency_key = ? LIMIT 1",
            (idempotency_key,),
        ).fetchone()
        if row is None:
            return None
        return row_to_command(row)

    def _get_command_after_recovery(self, command_id: str, *, now: Optional[datetime] = None) -> CommandRecord:
        command = self.storage.get_command(command_id)
        if command.status == "claimed" and command.lease_expires_at:
            expires_at = parse_timestamp(command.lease_expires_at)
            current_time = (now or self._now()).astimezone(timezone.utc)
            if expires_at <= current_time:
                self.recover_expired_claims(now=current_time)
                command = self.storage.get_command(command_id)
        return command

    def _validate_target_routing(self, target_agent: Optional[str], target_runtime: Optional[str]) -> None:
        if not (target_agent or target_runtime):
            raise BadRequestError("target_agent or target_runtime is required")
        if target_agent is not None and not str(target_agent).strip():
            raise BadRequestError("target_agent cannot be blank")
        if target_runtime is not None and not str(target_runtime).strip():
            raise BadRequestError("target_runtime cannot be blank")

    def _validate_permission_level(self, permission_level: str) -> None:
        if permission_level not in PERMISSION_RANKS:
            raise BadRequestError("permission_level must be one of L1, L2, or L3")

    def _has_permission(self, requester_permission_level: str, command_permission_level: str) -> bool:
        return PERMISSION_RANKS[requester_permission_level] >= PERMISSION_RANKS[command_permission_level]

    def _enforce_permission(self, requester_permission_level: str, command_permission_level: str) -> None:
        if not self._has_permission(requester_permission_level, command_permission_level):
            raise PermissionDeniedError("requester does not have permission for this command")

    def _ensure_claim_owner(self, command: CommandRecord, claimed_by: str) -> None:
        if command.status != "claimed":
            raise ConflictError("command must be claimed before completion or failure")
        if command.claimed_by != claimed_by:
            raise ConflictError("command is claimed by another agent")

    def _ensure_non_empty(self, field_name: str, value: str) -> None:
        if not str(value).strip():
            raise BadRequestError("{} is required".format(field_name))

    def _generate_command_id(self) -> str:
        return "cmd-{}".format(uuid4().hex[:12])

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)
