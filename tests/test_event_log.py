from pathlib import Path
import sys
from threading import Thread
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from relaycore.command_bus import CommandBusService
from relaycore.event_log import EventLogService, format_sse
from relaycore.memory_quality import MemoryQualityService
from relaycore.server import create_app
from relaycore.storage import RelayCoreStorage


@pytest.fixture
def storage(tmp_path: Path) -> RelayCoreStorage:
    repository = RelayCoreStorage(tmp_path / "event-log.db")
    repository.create_session(
        session_id="session-1",
        name="Timeline Session",
        goal="Track runtime events",
        mode="assist",
        created_by="codex",
    )
    try:
        yield repository
    finally:
        repository.close()


@pytest.fixture
def event_log(storage: RelayCoreStorage) -> EventLogService:
    return EventLogService(storage)


@pytest.fixture
def command_bus(storage: RelayCoreStorage, event_log: EventLogService) -> CommandBusService:
    return CommandBusService(storage, event_log=event_log)


@pytest.fixture
def memory_quality(storage: RelayCoreStorage, event_log: EventLogService) -> MemoryQualityService:
    return MemoryQualityService(storage, event_log=event_log)


@pytest.fixture
def client(command_bus: CommandBusService, event_log: EventLogService, memory_quality: MemoryQualityService):
    app = create_app(command_bus=command_bus, event_log=event_log, memory_quality=memory_quality)
    app.testing = True
    return app.test_client()


def test_post_and_get_events_round_trip(client, storage: RelayCoreStorage) -> None:
    created = client.post(
        "/api/events",
        json={
            "session_id": "session-1",
            "agent_id": "codex",
            "event_type": "proposal",
            "content": {"summary": "first draft"},
            "metadata": {"source": "manual"},
        },
    )
    assert created.status_code == 201

    fetched = client.get("/api/events", query_string={"session_id": "session-1"})
    assert fetched.status_code == 200
    payload = fetched.get_json()
    assert payload["events"][0]["event_type"] == "proposal"
    assert payload["events"][0]["metadata"]["source"] == "manual"
    assert payload["digests"] == []
    assert storage.list_audit_logs(resource_type="agent_event")[0].action == "event_append"


def test_sse_stream_returns_event_format(client, event_log: EventLogService) -> None:
    event_log.append_event(
        session_id="session-1",
        agent_id="codex",
        event_type="proposal",
        content={"summary": "stream me"},
    )

    response = client.get("/api/events/stream", query_string={"session_id": "session-1"})
    body = response.data.decode("utf-8")

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert "event: event" in body
    assert '"event_type":"proposal"' in body


def test_command_lifecycle_writes_events(client) -> None:
    published = client.post(
        "/api/commands",
        json={
            "session_id": "session-1",
            "mode": "assist",
            "command_type": "review_patch",
            "payload": {"path": "app.py"},
            "created_by": "codex",
            "target_runtime": "claude",
            "permission_level": "L1",
            "idempotency_key": "event-command-1",
        },
    )
    command_id = published.get_json()["command"]["command_id"]

    client.post(
        "/api/commands/{}/claim".format(command_id),
        json={
            "claimed_by": "agent-claude",
            "requester_permission_level": "L1",
            "lease_seconds": 120,
        },
    )
    client.post(
        "/api/commands/{}/complete".format(command_id),
        json={
            "claimed_by": "agent-claude",
            "requester_permission_level": "L1",
            "result": {"status": "done"},
        },
    )

    events = client.get("/api/events", query_string={"session_id": "session-1"}).get_json()["events"]
    event_types = [event["event_type"] for event in events]
    assert "command_published" in event_types
    assert "command_claimed" in event_types
    assert "command_completed" in event_types


def test_memory_quality_writes_review_events(client, memory_quality: MemoryQualityService, storage: RelayCoreStorage) -> None:
    storage.create_memory_candidate(
        candidate_id="mem-active",
        proposed_by="codex",
        runtime="codex",
        session_id="session-1",
        type="decision",
        title="Primary Database",
        content="Use SQLite for the MVP control plane.",
        summary="Use SQLite for the MVP control plane.",
        tags=["storage"],
        status="active",
    )

    result = memory_quality.memory_propose(
        proposed_by="claude",
        type="decision",
        title="Primary Database",
        content="Use PostgreSQL for the MVP control plane.",
        session_id="session-1",
        runtime="claude",
        relation_hint="supersede",
        tags=["storage"],
    )

    assert result.action == "supersede"
    events = client.get("/api/events", query_string={"session_id": "session-1"}).get_json()["events"]
    review_events = [event for event in events if event["event_type"] == "memory_review_required"]
    assert review_events
    assert review_events[0]["content"]["conflicts_with"] == ["mem-active"]


def test_memory_conflict_resolution_writes_events(client, memory_quality: MemoryQualityService, storage: RelayCoreStorage) -> None:
    storage.create_memory_candidate(
        candidate_id="mem-active",
        proposed_by="codex",
        runtime="codex",
        session_id="session-1",
        type="decision",
        title="Primary Database",
        content="Use SQLite for the MVP control plane.",
        summary="Use SQLite for the MVP control plane.",
        tags=["storage"],
        status="active",
    )
    result = memory_quality.memory_propose(
        proposed_by="claude",
        type="decision",
        title="Primary Database",
        content="Use PostgreSQL for the MVP control plane.",
        session_id="session-1",
        runtime="claude",
        relation_hint="supersede",
        tags=["storage"],
        candidate_id="mem-conflict",
    )

    assert result.conflicts_with == ["mem-active"]

    resolved = client.post(
        "/api/memory-candidates/mem-conflict/resolve",
        json={"status": "superseded", "recommended_action": "supersede", "actor": "mission-control"},
    )
    assert resolved.status_code == 200
    assert resolved.get_json()["candidate"]["status"] == "superseded"

    events = client.get("/api/events", query_string={"session_id": "session-1"}).get_json()["events"]
    event_types = [event["event_type"] for event in events]
    assert "memory_conflict_resolved" in event_types


def test_digest_is_created_every_ten_events(event_log: EventLogService, storage: RelayCoreStorage) -> None:
    for index in range(10):
        event_log.append_event(
            session_id="session-1",
            agent_id="codex",
            event_type="tool_summary",
            content={"index": index},
        )

    digests = storage.list_session_digests("session-1")
    assert len(digests) == 1
    assert digests[0].from_seq == 1
    assert digests[0].to_seq == 10


def test_stream_events_stays_live_for_new_events(event_log: EventLogService) -> None:
    def publish_later() -> None:
        time.sleep(0.01)
        event_log.broker.publish(
            "session-1",
            format_sse(
                "event",
                {
                    "event": {
                        "seq": 999,
                        "agent_id": "codex",
                        "event_type": "followup",
                        "content": {"summary": "late event"},
                    }
                },
                event_id=999,
            ),
        )

    thread = Thread(target=publish_later)
    thread.start()
    try:
        body = b"".join(
            event_log.stream_events(
                "session-1",
                poll_timeout=0.05,
                max_live_messages=1,
                max_heartbeats=2,
            )
        ).decode("utf-8")
        assert "event: event" in body
        assert '"event_type":"followup"' in body
    finally:
        thread.join()
