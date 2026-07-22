from html import unescape
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
    storage.create_memory_candidate(
        candidate_id="candidate-decision-1",
        proposed_by="codex-agent",
        runtime="codex",
        session_id="session-1",
        type="decision",
        title="Primary Database",
        content="Use SQLite for the MVP.",
        summary="Use SQLite for the MVP.",
        tags=["storage"],
        status="active",
        trace_refs=[{"session_id": "session-1", "event_seq": 1, "source_location": "tests"}],
        memory_level="L3",
    )
    storage.upsert_memory_cluster(
        cluster_id="cluster-candidate-decision-1",
        canonical_memory_id="candidate-decision-1",
        summary="Primary database cluster",
        tags=["storage"],
        source_count=2,
        quality_score=0.91,
        metadata={"source": "test"},
    )
    storage.create_memory_candidate(
        candidate_id="candidate-merged-1",
        proposed_by="claude-agent",
        runtime="claude",
        session_id="session-1",
        type="decision",
        title="Primary Database",
        content="Use SQLite for the MVP.",
        summary="Duplicate of Primary Database.",
        tags=["storage"],
        status="merged",
        similar_to=["candidate-decision-1"],
        recommended_action="merge",
        memory_level="L1",
        decision_status="accepted",
    )
    storage.append_event(
        session_id="session-1",
        agent_id="codex-agent",
        event_type="decision_note",
        content={"summary": "Use SQLite for the MVP."},
    )
    storage.create_session_digest(
        digest_id="digest-ui-1",
        session_id="session-1",
        from_seq=1,
        to_seq=1,
        summary="Digest with task canvas",
        decisions=[{"candidate_id": "candidate-decision-1"}],
        trace_refs=[{"session_id": "session-1", "event_seq": 1, "source_location": "tests"}],
        task_canvas='graph TD\nA["decision_note #1"]',
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
        content="Use PostgreSQL for the MVP.",
        runtime="codex",
        session_id="session-1",
        tags=["storage"],
        candidate_id="candidate-conflict-1",
        relation_hint="supersede",
    )
    storage.create_memory_candidate(
        candidate_id="candidate-rule-1",
        proposed_by="claude-agent",
        type="rule",
        title="No Scope Drift",
        content="Do not drift from the current confirmed phase or task scope while executing.",
        runtime="claude",
        session_id="session-1",
        summary="Stay within the confirmed phase and task scope.",
        tags=["execution", "scope"],
        status="active",
        rejected=["Expanding into roadmap work mid-task"],
        recommended_action="keep",
    )
    storage.append_audit_log(
        actor="codex-agent",
        action="seed_ui",
        resource_type="session",
        resource_id="session-1",
        metadata={"source": "test"},
    )
    storage.create_rejected_knowledge(
        rejected_id="reject-ui-1",
        session_id="session-1",
        candidate_id="candidate-conflict-1",
        accepted_candidate_id="candidate-decision-1",
        decision_type="decision",
        reason="SQLite remains the accepted MVP store.",
        trace_refs=[{"session_id": "session-1", "event_seq": 1, "source_location": "tests"}],
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
        assert "Manual Dispatch" in body
        assert "Agents normally publish commands themselves." in body
        assert "How to use it" in body
        assert "Choose a dispatch template to prefill the command shape." in body
        assert "Dispatch Template" in body
        assert "Usually the agent runtime you want to reach" in body
        assert "Example payload" in body
        assert "Create Dispatch" in body
        assert "Collaboration Modes" not in body
        assert "Quick Publish adversarial" not in body
        assert "Memory Candidate Queue" in body
        assert "Mermaid Task Canvas" in body
        assert "Trace Inspector" in body
        assert "Rejected Knowledge" in body
        assert "Decision Ledger" in body
        assert "Memory Viewer" in body
        assert "Conflict Resolution Panel" in body
        assert "Resolve Conflict" in body
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


def test_memory_viewer_renders_memory_entries_and_filters(tmp_path: Path) -> None:
    client, storage = build_client(tmp_path)
    try:
        response = client.get("/mission-control/memories", query_string={"session_id": "session-1"})
        body = response.data.decode("utf-8")
        visible = unescape(body)

        assert response.status_code == 200
        assert response.mimetype == "text/html"
        assert "RelayCore Memory Viewer" in visible
        assert "How to Read This Page" in visible
        assert "Start with Deposited Memory" in visible
        assert "Deposited Memory" in visible
        assert "Review Queue" in visible
        assert "Merged / Duplicate Records" in visible
        assert "Dedup & Refinement" in visible
        assert "Exact duplicates collapse into merged records" in visible
        assert "Merged Duplicates" in visible
        assert "Primary Database" in visible
        assert "Current role" in visible
        assert "Canonical accepted memory that is ready to reuse." in visible
        assert "Merged into" in visible
        assert "cluster-candidate-decision-1" in visible
        assert "Use SQLite for the MVP." in visible
        assert "Status Filters" in visible
        assert "Type Filters" in visible
        assert "Search Memory" in visible
        assert "All Sessions" in visible
        assert "Full Content" in visible
        assert "Structured Metadata" in visible
    finally:
        storage.close()


def test_memory_viewer_defaults_to_all_sessions_scope(tmp_path: Path) -> None:
    client, storage = build_client(tmp_path)
    try:
        response = client.get("/mission-control/memories")
        body = response.data.decode("utf-8")
        visible = unescape(body)

        assert response.status_code == 200
        assert "All Sessions" in visible
        assert "View every memory entry currently stored." in visible
        assert "session_id=session-1" not in body.split("<form", 1)[1]
    finally:
        storage.close()


def test_memory_viewer_filters_by_type_and_query(tmp_path: Path) -> None:
    client, storage = build_client(tmp_path)
    try:
        response = client.get(
            "/mission-control/memories",
            query_string={"session_id": "session-1", "type": "rule", "q": "scope"},
        )
        body = response.data.decode("utf-8")

        assert response.status_code == 200
        assert "No Scope Drift" in body
        assert "Expanding into roadmap work mid-task" in body
        assert "Primary Database" not in body
    finally:
        storage.close()


def test_dashboard_supports_chinese_language_toggle(tmp_path: Path) -> None:
    client, storage = build_client(tmp_path)
    try:
        response = client.get("/mission-control", query_string={"session_id": "session-1", "lang": "zh"})
        body = response.data.decode("utf-8")

        assert response.status_code == 200
        assert 'lang="zh"' in body
        assert "RelayCore 控制台" in body
        assert "控制台" in body
        assert "记忆浏览" in body
        assert "人工介入" in body
        assert "使用方法" in body
        assert "先选一个调度模板" in body
        assert "分发模板" in body
        assert "载荷示例" in body
        assert "创建调度" in body
        assert "追溯检查器" in body
        assert 'name="lang" value="zh"' in body
    finally:
        storage.close()


def test_memory_viewer_supports_chinese_language_toggle(tmp_path: Path) -> None:
    client, storage = build_client(tmp_path)
    try:
        response = client.get(
            "/mission-control/memories",
            query_string={"session_id": "session-1", "lang": "zh"},
        )
        body = response.data.decode("utf-8")

        assert response.status_code == 200
        assert 'lang="zh"' in body
        assert "RelayCore 记忆浏览" in body
        assert "如何阅读此页" in body
        assert "先看已沉淀记忆" in body
        assert "已沉淀记忆" in body
        assert "去重与精炼" in body
        assert "状态筛选" in body
        assert "类型筛选" in body
        assert "搜索记忆" in body
        assert "完整内容" in body
    finally:
        storage.close()


def test_mission_control_can_resolve_memory_conflicts(tmp_path: Path) -> None:
    client, storage = build_client(tmp_path)
    try:
        response = client.post(
            "/mission-control/memory-candidates/resolve",
            data={
                "session_id": "session-1",
                "lang": "en",
                "candidate_id": "candidate-conflict-1",
                "created_by": "mission-control",
                "status": "superseded",
                "recommended_action": "supersede",
            },
        )
        body = response.data.decode("utf-8")

        assert response.status_code == 200
        assert "Resolved candidate candidate-conflict-1 as superseded." in body
        assert storage.get_memory_candidate("candidate-conflict-1").status == "superseded"
        assert storage.list_audit_logs(resource_type="memory_candidate")[0].action == "memory_candidate_resolve"
    finally:
        storage.close()
