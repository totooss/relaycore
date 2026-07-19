from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from echomemory.command_bus import CommandBusService
from echomemory.server import create_app
from echomemory.storage import EchoMemoryStorage


@pytest.fixture
def storage(tmp_path: Path) -> EchoMemoryStorage:
    repository = EchoMemoryStorage(tmp_path / "command-bus.db")
    repository.create_session(
        session_id="session-1",
        name="Mission Control",
        goal="Coordinate commands",
        mode="assist",
        created_by="codex",
    )
    try:
        yield repository
    finally:
        repository.close()


@pytest.fixture
def service(storage: EchoMemoryStorage) -> CommandBusService:
    return CommandBusService(storage)


@pytest.fixture
def client(service: CommandBusService):
    app = create_app(command_bus=service)
    app.testing = True
    return app.test_client()


def publish_command(client, **overrides):
    payload = {
        "session_id": "session-1",
        "mode": "assist",
        "command_type": "review_patch",
        "payload": {"path": "app.py"},
        "created_by": "codex",
        "target_runtime": "claude",
        "permission_level": "L2",
        "idempotency_key": "publish-1",
    }
    payload.update(overrides)
    return client.post("/api/commands", json=payload)


def test_publish_command_and_idempotency(client, storage: EchoMemoryStorage) -> None:
    first = publish_command(client)
    second = publish_command(client)

    assert first.status_code == 201
    assert second.status_code == 200
    first_command = first.get_json()["command"]
    second_command = second.get_json()["command"]
    assert first_command["command_id"] == second_command["command_id"]

    audit_logs = storage.list_audit_logs(resource_type="command")
    assert audit_logs[0].action == "command_publish"


def test_pending_query_filters_by_permission_and_target(client) -> None:
    publish_command(client, idempotency_key="pending-1", target_runtime="claude", permission_level="L2")
    publish_command(client, idempotency_key="pending-2", target_runtime="claude", permission_level="L3")

    response = client.get(
        "/api/commands/pending",
        query_string={
            "target_runtime": "claude",
            "requester_permission_level": "L2",
        },
    )

    assert response.status_code == 200
    commands = response.get_json()["commands"]
    assert len(commands) == 1
    assert commands[0]["permission_level"] == "L2"


def test_claim_complete_and_fail_flow(client, storage: EchoMemoryStorage) -> None:
    published = publish_command(client, idempotency_key="claim-flow")
    command_id = published.get_json()["command"]["command_id"]

    claimed = client.post(
        "/api/commands/{}/claim".format(command_id),
        json={
            "claimed_by": "agent-claude",
            "requester_permission_level": "L2",
            "lease_seconds": 120,
        },
    )
    assert claimed.status_code == 200
    assert claimed.get_json()["command"]["status"] == "claimed"

    conflict = client.post(
        "/api/commands/{}/claim".format(command_id),
        json={
            "claimed_by": "agent-other",
            "requester_permission_level": "L2",
            "lease_seconds": 120,
        },
    )
    assert conflict.status_code == 409

    completed = client.post(
        "/api/commands/{}/complete".format(command_id),
        json={
            "claimed_by": "agent-claude",
            "requester_permission_level": "L2",
            "result": {"status": "done"},
        },
    )
    assert completed.status_code == 200
    assert completed.get_json()["command"]["status"] == "completed"

    failed_publish = publish_command(client, idempotency_key="fail-flow", target_agent="agent-codex")
    failed_id = failed_publish.get_json()["command"]["command_id"]
    client.post(
        "/api/commands/{}/claim".format(failed_id),
        json={
            "claimed_by": "agent-codex",
            "requester_permission_level": "L2",
            "lease_seconds": 120,
        },
    )
    failed = client.post(
        "/api/commands/{}/fail".format(failed_id),
        json={
            "claimed_by": "agent-codex",
            "requester_permission_level": "L2",
            "result": {"reason": "validation"},
        },
    )
    assert failed.status_code == 200
    assert failed.get_json()["command"]["status"] == "failed"

    actions = [log.action for log in storage.list_audit_logs(resource_type="command", limit=10)]
    assert "command_claim" in actions
    assert "command_complete" in actions
    assert "command_fail" in actions


def test_expired_lease_is_recovered(service: CommandBusService, storage: EchoMemoryStorage) -> None:
    command = storage.create_command(
        command_id="cmd-expired",
        session_id="session-1",
        target_runtime="claude",
        mode="assist",
        command_type="review_patch",
        payload={"path": "x.py"},
        created_by="codex",
        permission_level="L1",
    )
    storage.update_command_status(
        command.command_id,
        "claimed",
        claimed_by="agent-claude",
        lease_expires_at=(datetime.now(timezone.utc) - timedelta(minutes=5)).replace(microsecond=0).isoformat(),
    )

    recovered = service.list_pending_commands(
        requester_permission_level="L1",
        target_runtime="claude",
    )
    assert recovered[0].command_id == "cmd-expired"
    refreshed = storage.get_command("cmd-expired")
    assert refreshed.status == "pending"


def test_permission_and_routing_validation(client) -> None:
    forbidden = publish_command(client, idempotency_key="perm-1", permission_level="L3")
    command_id = forbidden.get_json()["command"]["command_id"]

    denied = client.post(
        "/api/commands/{}/claim".format(command_id),
        json={
            "claimed_by": "agent-claude",
            "requester_permission_level": "L2",
            "lease_seconds": 120,
        },
    )
    assert denied.status_code == 403

    invalid = client.post(
        "/api/commands",
        json={
            "session_id": "session-1",
            "mode": "assist",
            "command_type": "review_patch",
            "payload": {"path": "app.py"},
            "created_by": "codex",
            "permission_level": "L1",
        },
    )
    assert invalid.status_code == 400
