from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from echomemory.command_bus import CommandBusService
from echomemory.event_log import EventLogService
from echomemory.runtime_adapters import CollaborationModeRegistry
from echomemory.server import create_app
from echomemory.storage import EchoMemoryStorage


def build_stack(tmp_path: Path):
    storage = EchoMemoryStorage(tmp_path / "collaboration.db")
    storage.create_session(
        session_id="session-1",
        name="Collaboration Session",
        goal="Validate mode templates",
        mode="assist",
        created_by="codex",
    )
    event_log = EventLogService(storage)
    command_bus = CommandBusService(storage, event_log=event_log)
    return storage, event_log, command_bus


def test_collaboration_mode_registry_contains_all_supported_modes() -> None:
    registry = CollaborationModeRegistry()
    names = [template.name for template in registry.list()]
    assert names == ["assist", "review", "adversarial", "debate", "pipeline"]
    adversarial = registry.get("adversarial")
    assert "challenger" in adversarial.participants
    assert adversarial.command_defaults["command_type"] == "challenge_plan"


def test_adversarial_mode_end_to_end_adds_template_and_events(tmp_path: Path) -> None:
    storage, event_log, command_bus = build_stack(tmp_path)
    try:
        command = command_bus.publish_command(
            session_id="session-1",
            mode="adversarial",
            command_type="challenge_plan",
            payload={"summary": "Stress-test the proposed database decision."},
            created_by="codex",
            target_runtime="claude",
            permission_level="L2",
            idempotency_key="adversarial-1",
        )

        assert command.mode == "adversarial"
        assert command.payload["collaboration"]["name"] == "adversarial"
        assert "challenger" in command.payload["collaboration"]["participants"]

        claimed = command_bus.claim_command(
            command.command_id,
            claimed_by="claude-reviewer",
            requester_permission_level="L2",
        )
        completed = command_bus.complete_command(
            command.command_id,
            claimed_by="claude-reviewer",
            requester_permission_level="L2",
            result={"resolution": "SQLite stays, but backup/export becomes mandatory."},
        )

        assert claimed.status == "claimed"
        assert completed.status == "completed"

        events = event_log.list_events("session-1")
        event_types = [event.event_type for event in events]
        assert "collaboration_mode_started" in event_types
        started = [event for event in events if event.event_type == "collaboration_mode_started"][0]
        assert started.content["collaboration_mode"] == "adversarial"
        assert "resolver" in started.content["participants"]
    finally:
        storage.close()


def test_mission_control_quick_publish_uses_structured_mode_defaults(tmp_path: Path) -> None:
    storage, event_log, command_bus = build_stack(tmp_path)
    app = create_app(storage=storage, command_bus=command_bus, event_log=event_log)
    app.testing = True
    client = app.test_client()
    try:
        response = client.post(
            "/mission-control/commands",
            data={
                "session_id": "session-1",
                "created_by": "mission-control",
                "mode": "pipeline",
                "target_runtime": "codex",
                "command_type": "pipeline_stage",
                "permission_level": "L1",
                "priority": "85",
                "payload": '{"summary":"Run ordered handoff","workflow":["stage_1","stage_2","stage_3"]}',
            },
        )

        assert response.status_code == 200
        commands = storage.list_commands(session_id="session-1")
        assert commands[0].mode == "pipeline"
        assert commands[0].payload["collaboration"]["name"] == "pipeline"
        assert commands[0].payload["participants"] == ["stage_1", "stage_2", "stage_3"]
    finally:
        storage.close()
