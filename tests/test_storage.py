from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from relaycore.storage import RelayCoreStorage, InvalidTransitionError, NotFoundError, ValidationError


@pytest.fixture
def storage(tmp_path: Path) -> RelayCoreStorage:
    repository = RelayCoreStorage(tmp_path / "storage.db")
    try:
        yield repository
    finally:
        repository.close()


def create_session(repository: RelayCoreStorage, session_id: str = "session-1") -> None:
    repository.create_session(
        session_id=session_id,
        name="Mission Alpha",
        goal="Coordinate two agents",
        mode="assist",
        created_by="codex",
        metadata={"team": "runtime"},
    )


def test_session_crud_and_digest_reads(storage: RelayCoreStorage) -> None:
    create_session(storage)

    session = storage.get_session("session-1")
    assert session.metadata["team"] == "runtime"

    updated = storage.update_session("session-1", status="paused", metadata={"priority": "high"})
    assert updated.status == "paused"
    assert updated.metadata == {"team": "runtime", "priority": "high"}

    digest = storage.create_session_digest(
        digest_id="digest-1",
        session_id="session-1",
        from_seq=1,
        to_seq=5,
        summary="A compact summary",
        decisions=[{"id": "d1"}],
        open_questions=["What is next?"],
    )
    assert digest.decisions == [{"id": "d1"}]
    assert storage.list_session_digests("session-1")[0].digest_id == "digest-1"

    storage.delete_session("session-1")
    with pytest.raises(NotFoundError):
        storage.get_session("session-1")


def test_command_status_transitions_are_validated(storage: RelayCoreStorage) -> None:
    create_session(storage)
    command = storage.create_command(
        command_id="cmd-1",
        session_id="session-1",
        mode="assist",
        command_type="review_patch",
        payload={"path": "a.py"},
        created_by="claude",
        target_runtime="codex",
    )
    assert command.status == "pending"

    claimed = storage.update_command_status(
        "cmd-1",
        "claimed",
        claimed_by="agent-codex",
        lease_expires_at="2026-07-19T13:00:00+00:00",
    )
    assert claimed.status == "claimed"
    assert claimed.claimed_by == "agent-codex"

    completed = storage.update_command_status(
        "cmd-1",
        "completed",
        result={"status": "done"},
    )
    assert completed.status == "completed"
    assert completed.result["status"] == "done"

    with pytest.raises(InvalidTransitionError):
        storage.update_command_status("cmd-1", "claimed", claimed_by="agent-codex")

    with pytest.raises(ValidationError):
        storage.update_command_status("cmd-1", "completed")


def test_event_append_and_ordered_queries(storage: RelayCoreStorage) -> None:
    create_session(storage)

    first = storage.append_event(
        session_id="session-1",
        agent_id="codex",
        event_type="proposal",
        content={"summary": "initial idea"},
    )
    second = storage.append_event(
        session_id="session-1",
        agent_id="claude",
        event_type="critique",
        content={"summary": "counterpoint"},
        parent_seq=first.seq,
        metadata={"severity": "low"},
    )

    events = storage.list_events("session-1")
    assert [event.seq for event in events] == [first.seq, second.seq]
    assert storage.list_events("session-1", after_seq=first.seq)[0].seq == second.seq
    assert events[1].metadata["severity"] == "low"


def test_memory_candidate_occurrence_cluster_and_audit_flows(storage: RelayCoreStorage) -> None:
    create_session(storage)

    candidate = storage.create_memory_candidate(
        candidate_id="mem-1",
        proposed_by="codex",
        runtime="codex",
        session_id="session-1",
        type="decision",
        title="Use SQLite",
        content="SQLite is enough for the MVP.",
        tags=["storage"],
    )
    assert candidate.status == "pending"

    updated = storage.update_memory_candidate(
        "mem-1",
        summary="SQLite is sufficient for MVP persistence.",
        similar_to=["mem-0"],
        conflicts_with=["mem-x"],
        recommended_action="review",
    )
    assert updated.similar_to == ["mem-0"]

    resolved = storage.resolve_memory_candidate("mem-1", "active", recommended_action="accept")
    assert resolved.status == "active"
    assert resolved.recommended_action == "accept"
    assert resolved.resolved_at is not None

    occurrence = storage.record_memory_occurrence(
        memory_id="mem-1",
        agent_id="codex",
        runtime="codex",
        session_id="session-1",
        note="Observed in testing",
    )
    assert occurrence.memory_id == "mem-1"
    assert storage.list_memory_occurrences("mem-1")[0].note == "Observed in testing"

    cluster = storage.upsert_memory_cluster(
        cluster_id="cluster-1",
        canonical_memory_id="mem-1",
        summary="SQLite choices",
        tags=["storage"],
        source_count=2,
        quality_score=0.75,
        metadata={"owner": "codex"},
    )
    assert cluster.source_count == 2
    assert storage.list_memory_clusters()[0].cluster_id == "cluster-1"

    audit_log = storage.append_audit_log(
        actor="codex",
        action="memory_accept",
        resource_type="memory_candidate",
        resource_id="mem-1",
        metadata={"cluster": "cluster-1"},
    )
    assert audit_log.resource_id == "mem-1"
    assert storage.list_audit_logs(resource_type="memory_candidate")[0].metadata["cluster"] == "cluster-1"


def test_invalid_memory_candidate_status_is_rejected(storage: RelayCoreStorage) -> None:
    create_session(storage)

    with pytest.raises(ValidationError):
        storage.create_memory_candidate(
            candidate_id="mem-bad",
            proposed_by="codex",
            type="decision",
            title="Bad",
            content="Bad status",
            status="unknown",
        )
