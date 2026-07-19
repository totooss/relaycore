from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from relaycore.mcp_server import RelayCoreMCPServer
from relaycore.storage import RelayCoreStorage


@pytest.fixture
def server(tmp_path: Path) -> RelayCoreMCPServer:
    storage = RelayCoreStorage(tmp_path / "mcp-tools.db")
    instance = RelayCoreMCPServer(storage=storage)
    yield instance
    storage.close()


def test_tool_list_contains_required_mcp_surface(server: RelayCoreMCPServer) -> None:
    names = [tool.name for tool in server.list_tools()]
    assert "memory_begin_task" in names
    assert "memory_context" in names
    assert "memory_propose" in names
    assert "memory_add" in names
    assert "command_poll" in names
    assert "session_digest_get" in names
    assert "agent_heartbeat" in names


def test_memory_begin_context_and_commit_flow(server: RelayCoreMCPServer) -> None:
    begun = server.call_tool(
        "memory_begin_task",
        {
            "session_id": "session-1",
            "runtime": "codex",
            "agent_id": "codex-runner",
            "name": "Phase Session",
            "goal": "Coordinate memory",
        },
    )
    assert begun["session"]["session_id"] == "session-1"

    added = server.call_tool(
        "memory_add",
        {
            "session_id": "session-1",
            "runtime": "codex",
            "agent_id": "codex-runner",
            "type": "decision",
            "title": "Primary Store",
            "content": "Use SQLite as the shared control-plane store.",
            "tags": ["storage", "shared"],
        },
    )
    assert added["candidate"]["status"] == "active"

    context = server.call_tool(
        "memory_context",
        {
            "session_id": "session-1",
            "runtime": "claude",
            "agent_id": "claude-reviewer",
            "query": "shared store",
            "max_items": 3,
        },
    )
    assert context["items"]
    assert "why_relevant" in context["items"][0]
    assert "expand_handle" in context["items"][0]
    assert "content" not in context["items"][0]

    committed = server.call_tool(
        "memory_commit_task",
        {
            "session_id": "session-1",
            "runtime": "claude",
            "agent_id": "claude-reviewer",
            "summary": "Committed current task state.",
        },
    )
    assert committed["session_id"] == "session-1"


def test_memory_propose_preserves_conflicts_and_rejected_options(server: RelayCoreMCPServer) -> None:
    server.call_tool(
        "memory_begin_task",
        {"session_id": "session-2", "runtime": "codex", "agent_id": "codex-runner"},
    )
    server.call_tool(
        "memory_add",
        {
            "session_id": "session-2",
            "runtime": "codex",
            "agent_id": "codex-runner",
            "type": "decision",
            "title": "Primary Database",
            "content": "Use SQLite for the MVP.",
        },
    )
    result = server.call_tool(
        "memory_propose",
        {
            "session_id": "session-2",
            "runtime": "claude",
            "agent_id": "claude-reviewer",
            "type": "decision",
            "title": "Primary Database",
            "content": "Use PostgreSQL for the MVP.",
            "relation_hint": "supersede",
        },
    )
    assert result["action"] == "supersede"
    assert result["conflicts_with"]

    context = server.call_tool(
        "memory_context",
        {
            "session_id": "session-2",
            "runtime": "claude",
            "agent_id": "claude-reviewer",
        },
    )
    assert context["items"][0]["rejected_summary"]


def test_codex_and_claude_share_one_session_workflow(server: RelayCoreMCPServer) -> None:
    server.call_tool(
        "memory_begin_task",
        {
            "session_id": "shared-session",
            "runtime": "codex",
            "agent_id": "codex-runner",
            "name": "Shared Workflow",
            "goal": "Verify cross-runtime attach flow",
        },
    )
    server.call_tool(
        "memory_begin_task",
        {
            "session_id": "shared-session",
            "runtime": "claude",
            "agent_id": "claude-reviewer",
        },
    )
    server.call_tool(
        "memory_add",
        {
            "session_id": "shared-session",
            "runtime": "codex",
            "agent_id": "codex-runner",
            "type": "decision",
            "title": "Shared Store",
            "content": "Use SQLite as the shared RelayCore store.",
            "tags": ["storage"],
        },
    )
    server.call_tool(
        "agent_event_append",
        {
            "session_id": "shared-session",
            "runtime": "claude",
            "agent_id": "claude-reviewer",
            "event_type": "review_note",
            "content": {"summary": "Claude attached to the same task timeline."},
        },
    )

    context = server.call_tool(
        "memory_context",
        {
            "session_id": "shared-session",
            "runtime": "claude",
            "agent_id": "claude-reviewer",
            "query": "shared store",
        },
    )
    assert context["items"]
    assert context["items"][0]["title"] == "Shared Store"
    assert "content" not in context["items"][0]

    committed = server.call_tool(
        "memory_commit_task",
        {
            "session_id": "shared-session",
            "runtime": "claude",
            "agent_id": "claude-reviewer",
            "summary": "Shared workflow committed.",
        },
    )
    assert committed["session_id"] == "shared-session"

    events = server.storage.list_events("shared-session", limit=20)
    event_types = [event.event_type for event in events]
    assert "task_begin" in event_types
    assert "review_note" in event_types
    assert "task_commit" in event_types

    agent_states = server.storage.list_agent_states(session_id="shared-session", limit=10)
    agent_ids = {state.agent_id for state in agent_states}
    assert {"codex-runner", "claude-reviewer"} <= agent_ids
    assert server.storage.get_session("shared-session").metadata["last_commit_runtime"] == "claude"


def test_command_tools_and_digest_fetch_work_together(server: RelayCoreMCPServer) -> None:
    server.call_tool(
        "memory_begin_task",
        {"session_id": "session-3", "runtime": "codex", "agent_id": "codex-runner"},
    )
    published = server.command_bus.publish_command(
        session_id="session-3",
        mode="assist",
        command_type="review_patch",
        payload={"path": "app.py"},
        created_by="codex-runner",
        target_runtime="claude",
        permission_level="L1",
        idempotency_key="mcp-command-1",
    )
    polled = server.call_tool(
        "command_poll",
        {
            "runtime": "claude",
            "agent_id": "claude-reviewer",
            "session_id": "session-3",
            "requester_permission_level": "L1",
        },
    )
    assert polled["count"] == 1

    claimed = server.call_tool(
        "command_claim",
        {
            "command_id": published.command_id,
            "runtime": "claude",
            "claimed_by": "claude-reviewer",
            "requester_permission_level": "L1",
        },
    )
    assert claimed["command"]["status"] == "claimed"

    completed = server.call_tool(
        "command_complete",
        {
            "command_id": published.command_id,
            "runtime": "claude",
            "claimed_by": "claude-reviewer",
            "requester_permission_level": "L1",
            "result": {"status": "done"},
        },
    )
    assert completed["command"]["status"] == "completed"

    for index in range(8):
        server.call_tool(
            "agent_event_append",
            {
                "session_id": "session-3",
                "runtime": "codex",
                "agent_id": "codex-runner",
                "event_type": "tool_summary",
                "content": {"index": index},
            },
        )

    digests = server.call_tool(
        "session_digest_get",
        {"session_id": "session-3", "runtime": "codex"},
    )
    assert digests["digests"]


def test_agent_heartbeat_updates_shared_agent_state(server: RelayCoreMCPServer) -> None:
    heartbeat = server.call_tool(
        "agent_heartbeat",
        {
            "runtime": "claude",
            "agent_id": "claude-reviewer",
            "session_id": "session-4",
            "status": "busy",
            "role": "reviewer",
            "capabilities": ["review", "memory"],
            "metadata": {"source": "mcp"},
        },
    )
    assert heartbeat["agent_state"]["agent_id"] == "claude-reviewer"
    assert heartbeat["agent_state"]["status"] == "busy"
