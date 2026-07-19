from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from relaycore.memory_quality import MemoryQualityService
from relaycore.server import create_app
from relaycore.storage import RelayCoreStorage


def build_client(tmp_path: Path):
    storage = RelayCoreStorage(tmp_path / "web-ui.db")
    storage.create_session(
        session_id="session-1",
        name="Mission Board",
        goal="Inspect the control plane",
        mode="assist",
        created_by="codex",
    )
    storage.upsert_agent_state(
        agent_id="codex-agent",
        runtime="codex",
        session_id="session-1",
        status="active",
        capabilities=["memory", "commands"],
        metadata={"surface": "ui"},
    )
    quality = MemoryQualityService(storage)
    quality.memory_propose(
        proposed_by="codex-agent",
        type="decision",
        title="Primary Database",
        content="Use SQLite for the MVP.",
        runtime="codex",
        session_id="session-1",
        tags=["storage"],
    )
    storage.append_audit_log(
        actor="codex-agent",
        action="seed_ui",
        resource_type="session",
        resource_id="session-1",
        metadata={"source": "test"},
    )
    app = create_app(storage=storage, memory_quality=quality)
    app.testing = True
    return app.test_client(), storage


def test_mission_control_dashboard_renders_sections(tmp_path: Path) -> None:
    client, storage = build_client(tmp_path)
    try:
        response = client.get("/mission-control", query_string={"session_id": "session-1"})
        body = response.data.decode("utf-8")

        assert response.status_code == 200
        assert response.mimetype == "text/html"
        assert "RelayCore Mission Control" in body
        assert "Command Publisher" in body
        assert "Collaboration Modes" in body
        assert "Quick Publish adversarial" in body
        assert "Memory Candidate Queue" in body
        assert "Conflict Resolution Panel" in body
        assert "Token Budget Monitor" in body
        assert "Audit Log Viewer" in body
        assert "Uncommitted Session" in body
        assert "/api/events/stream?session_id=" in body
    finally:
        storage.close()


def test_mission_control_shows_commit_status_when_session_is_committed(tmp_path: Path) -> None:
    client, storage = build_client(tmp_path)
    try:
        storage.update_session("session-1", metadata={"last_commit_at": "2026-07-19T00:00:00+00:00"})
        response = client.get("/mission-control", query_string={"session_id": "session-1"})
        body = response.data.decode("utf-8")

        assert response.status_code == 200
        assert "Committed session" in body
        assert "Last commit at 2026-07-19T00:00:00+00:00." in body
        assert "Uncommitted Session" not in body
    finally:
        storage.close()


def test_mission_control_command_form_publishes_structured_command(tmp_path: Path) -> None:
    client, storage = build_client(tmp_path)
    try:
        response = client.post(
            "/mission-control/commands",
            data={
                "session_id": "session-1",
                "created_by": "mission-control",
                "mode": "assist",
                "target_runtime": "claude",
                "target_agent": "",
                "command_type": "review_patch",
                "permission_level": "L2",
                "priority": "80",
                "idempotency_key": "web-ui-1",
                "payload": '{"path":"app.py","summary":"Review latest command bus changes"}',
            },
        )
        body = response.data.decode("utf-8")

        assert response.status_code == 200
        assert "Published command" in body
        commands = storage.list_commands(session_id="session-1", target_runtime="claude")
        assert len(commands) == 1
        assert commands[0].permission_level == "L2"
        assert commands[0].payload["path"] == "app.py"
    finally:
        storage.close()


def test_mission_control_rejects_invalid_payload_json(tmp_path: Path) -> None:
    client, storage = build_client(tmp_path)
    try:
        response = client.post(
            "/mission-control/commands",
            data={
                "session_id": "session-1",
                "created_by": "mission-control",
                "mode": "assist",
                "target_runtime": "claude",
                "command_type": "review_patch",
                "permission_level": "L1",
                "priority": "100",
                "payload": '{"broken":',
            },
        )
        body = response.data.decode("utf-8")

        assert response.status_code == 400
        assert "payload must be valid JSON" in body
    finally:
        storage.close()
