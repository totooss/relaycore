"""HTML Mission Control views for RelayCore."""

from html import escape
import json
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from .command_bus import CommandBusService
from .event_log import EventLogService
from .memory_quality import MemoryQualityService
from .runtime_adapters import CollaborationModeRegistry
from .storage import RelayCoreStorage
from .token_budget import redact_structure


def _esc(value: Any) -> str:
    return escape("" if value is None else str(value))


def _json_preview(value: Any) -> str:
    return _esc(json.dumps(redact_structure(value), ensure_ascii=True, sort_keys=True))


SUPPORTED_LANGS = frozenset(("en", "zh"))
UI_TEXT = {
    "en": {
        "mission_control": "Mission Control",
        "memory_viewer": "Memory Viewer",
        "lang_en": "English",
        "lang_zh": "中文",
        "eyebrow_dashboard": "RelayCore Mission Control",
        "dashboard_title": "Shared runtime memory, not a shell.",
        "dashboard_body": "Inspect sessions, structured commands, live events, candidate memories, and audit trails from one page. This console only publishes permission-scoped commands and session metadata. It never executes arbitrary shell instructions.",
        "sessions": "Sessions",
        "agent_states": "Agent States",
        "pending_commands": "Pending Commands",
        "recent_events": "Recent Events",
        "tracked_count": "{count} tracked",
        "session_detail": "Session Detail",
        "session_detail_lead": "Current focus, command traffic, and live timeline for the selected task.",
        "no_session_selected": "No session selected",
        "command_publisher": "Command Publisher",
        "command_publisher_lead": "Publish a structured command with explicit routing and permission scope.",
        "no_shell_execution": "No Shell Execution",
        "collaboration_modes": "Collaboration Modes",
        "collaboration_modes_lead": "Structured templates keep multi-agent coordination predictable and auditable.",
        "templates_count": "{count} templates",
        "live_count": "{count} live",
        "token_budget_monitor": "Token Budget Monitor",
        "est_count": "{count} est",
        "token_budget_lead": "A compact estimate to keep retrieval and operator summaries small enough for runtime use.",
        "memory_context": "Memory Context",
        "event_digest": "Event Digest",
        "command_payloads": "Command Payloads",
        "candidate_summaries": "Candidate Summaries",
        "token_note": "Approximation only. Full content stays hidden unless an explicit expansion handle is requested.",
        "memory_candidate_queue": "Memory Candidate Queue",
        "queued_count": "{count} queued",
        "conflict_resolution_panel": "Conflict Resolution Panel",
        "conflicts_count": "{count} conflicts",
        "resolve_conflict": "Resolve Conflict",
        "resolution_status": "Resolution Status",
        "resolution_action": "Resolution Action",
        "live_timeline": "Live Timeline",
        "sse_ready": "SSE Ready",
        "audit_log_viewer": "Audit Log Viewer",
        "recent_count": "{count} recent",
        "recent_digests": "Recent Digests",
        "compact_count": "{count} compact",
        "eyebrow_memory": "RelayCore Memory Viewer",
        "memory_title": "View stored memory in one place.",
        "memory_body": "Browse memory entries by session and status. This page is for inspection only, so you can directly review summaries, full content, tags, rejected options, and conflict markers.",
        "total_in_scope": "Total In Scope",
        "active": "Active",
        "pending": "Pending",
        "rejected": "Rejected",
        "status_filters": "Status Filters",
        "type_filters": "Type Filters",
        "search_memory": "Search Memory",
        "search_active": "active",
        "search_empty": "empty",
        "query": "Query",
        "query_placeholder": "Search title, summary, content, tags, rejected options",
        "apply_search": "Apply Search",
        "clear": "Clear",
        "current_scope": "Current Scope",
        "shown_count": "{count} shown",
        "scope_session": "session scope",
        "scope_status": "status scope",
        "scope_type": "type scope",
        "scope_search": "search scope",
        "all_sessions": "all sessions",
        "all_statuses": "all statuses",
        "all_types": "all types",
        "no_search": "no search",
        "memory_entries": "Memory Entries",
        "all_sessions_title": "All Sessions",
        "all_sessions_desc": "View every memory entry currently stored.",
        "all": "all",
        "entries_count": "{count} entries",
        "no_sessions_yet": "No sessions yet.",
        "seed_control_plane": "Use MCP tools or Phase 8 forms to seed the control plane.",
        "memory_after_session": "Memory entries will appear after a session is created.",
        "select_session_lead": "Select a session to inspect commands, events, candidates, and digests.",
        "session_id": "Session ID",
        "status": "Status",
        "mode": "Mode",
        "created_by": "Created By",
        "commands": "Commands",
        "events": "Events",
        "metadata": "Metadata",
        "compact": "Compact",
        "target_runtime": "Target Runtime",
        "target_agent": "Target Agent",
        "optional": "optional",
        "command_type": "Command Type",
        "permission_level": "Permission Level",
        "priority": "Priority",
        "idempotency_key": "Idempotency Key",
        "idempotency_placeholder": "optional-dedup-key",
        "structured_payload_json": "Structured Payload JSON",
        "publish_structured_command": "Publish Structured Command",
        "quick_publish": "Quick Publish {name}",
        "no_heartbeats": "No heartbeats yet.",
        "heartbeats_desc": "Agents will appear here after `agent_heartbeat` or `memory_begin_task`.",
        "last_heartbeat": "last heartbeat {value}",
        "no_candidates": "No candidates queued.",
        "candidates_desc": "Memory proposals and conflict reviews will appear here.",
        "review": "review",
        "no_memory_entries": "No memory entries found.",
        "try_another_filter": "Try another session or status filter.",
        "conflict": "conflict",
        "session": "Session",
        "proposed_by": "Proposed by",
        "runtime": "Runtime",
        "created": "Created",
        "full_content": "Full Content",
        "structured_metadata": "Structured Metadata",
        "global": "global",
        "unknown": "unknown",
        "no_summary": "(no summary)",
        "no_active_conflicts": "No active conflicts.",
        "conflict_review_empty": "Conflict review is empty for the selected session.",
        "conflict_count_label": "{count} conflict(s)",
        "recommended_action": "Recommended action: {value}",
        "no_timeline": "No timeline events yet.",
        "timeline_desc": "Event API, command changes, and memory actions will stream here.",
        "seq": "seq {value}",
        "no_audit_entries": "No audit entries yet.",
        "not_available": "n/a",
        "no_digests": "No digests yet.",
        "digests_desc": "Digests appear automatically every 10 events or via task commit.",
        "committed_session": "Committed session",
        "last_commit_at": "Last commit at {value}.",
        "uncommitted_session": "Uncommitted Session",
        "uncommitted_desc": "This session has not been sealed with `memory_commit_task` yet.",
        "published_command": "Published command {command_id} for session {session_id}.",
        "payload_json_error": "payload must be valid JSON: {message}",
        "payload_object_error": "payload must decode to a JSON object",
        "session_required_error": "session_id is required",
        "language": "Language",
    },
    "zh": {
        "mission_control": "控制台",
        "memory_viewer": "记忆浏览",
        "lang_en": "English",
        "lang_zh": "中文",
        "eyebrow_dashboard": "RelayCore 控制台",
        "dashboard_title": "共享运行时记忆，而不是 Shell。",
        "dashboard_body": "在一个页面里查看会话、结构化命令、实时事件、候选记忆和审计轨迹。这个控制台只发布有权限范围的结构化命令和会话元数据，不执行任意 Shell 指令。",
        "sessions": "会话",
        "agent_states": "代理状态",
        "pending_commands": "待处理命令",
        "recent_events": "最近事件",
        "tracked_count": "共 {count} 个",
        "session_detail": "会话详情",
        "session_detail_lead": "查看当前任务焦点、命令流转和实时事件时间线。",
        "no_session_selected": "未选择会话",
        "command_publisher": "命令发布",
        "command_publisher_lead": "以明确路由和权限范围发布结构化命令。",
        "no_shell_execution": "不执行 Shell",
        "collaboration_modes": "协作模式",
        "collaboration_modes_lead": "结构化模板让多代理协作更稳定、更可审计。",
        "templates_count": "共 {count} 个模板",
        "live_count": "{count} 个在线",
        "token_budget_monitor": "Token 预算监视",
        "est_count": "估算 {count}",
        "token_budget_lead": "用紧凑估算控制检索和操作摘要的体积，保证运行时可用。",
        "memory_context": "记忆上下文",
        "event_digest": "事件摘要",
        "command_payloads": "命令载荷",
        "candidate_summaries": "候选摘要",
        "token_note": "这里只是近似估算。除非明确展开，否则不会直接暴露完整内容。",
        "memory_candidate_queue": "记忆候选队列",
        "queued_count": "共 {count} 条",
        "conflict_resolution_panel": "冲突处理面板",
        "conflicts_count": "{count} 个冲突",
        "resolve_conflict": "解决冲突",
        "resolution_status": "处理状态",
        "resolution_action": "处理动作",
        "live_timeline": "实时时间线",
        "sse_ready": "支持 SSE",
        "audit_log_viewer": "审计日志",
        "recent_count": "最近 {count} 条",
        "recent_digests": "最近摘要",
        "compact_count": "共 {count} 条",
        "eyebrow_memory": "RelayCore 记忆浏览",
        "memory_title": "集中查看已存储记忆。",
        "memory_body": "按会话和状态浏览记忆条目。这个页面只用于查看，你可以直接审阅摘要、完整内容、标签、被拒选项和冲突标记。",
        "total_in_scope": "当前范围总数",
        "active": "活跃",
        "pending": "待处理",
        "rejected": "已拒绝",
        "status_filters": "状态筛选",
        "type_filters": "类型筛选",
        "search_memory": "搜索记忆",
        "search_active": "已启用",
        "search_empty": "未启用",
        "query": "查询词",
        "query_placeholder": "搜索标题、摘要、正文、标签、被拒选项",
        "apply_search": "应用搜索",
        "clear": "清除",
        "current_scope": "当前范围",
        "shown_count": "显示 {count} 条",
        "scope_session": "会话范围",
        "scope_status": "状态范围",
        "scope_type": "类型范围",
        "scope_search": "搜索范围",
        "all_sessions": "全部会话",
        "all_statuses": "全部状态",
        "all_types": "全部类型",
        "no_search": "未搜索",
        "memory_entries": "记忆条目",
        "all_sessions_title": "全部会话",
        "all_sessions_desc": "查看当前存储的全部记忆条目。",
        "all": "全部",
        "entries_count": "共 {count} 条",
        "no_sessions_yet": "还没有会话。",
        "seed_control_plane": "可以通过 MCP 工具或 Phase 8 表单初始化控制台数据。",
        "memory_after_session": "创建会话后，这里会显示记忆条目。",
        "select_session_lead": "选择一个会话，查看命令、事件、候选记忆和摘要。",
        "session_id": "会话 ID",
        "status": "状态",
        "mode": "模式",
        "created_by": "创建者",
        "commands": "命令",
        "events": "事件",
        "metadata": "元数据",
        "compact": "紧凑",
        "target_runtime": "目标运行时",
        "target_agent": "目标代理",
        "optional": "可选",
        "command_type": "命令类型",
        "permission_level": "权限等级",
        "priority": "优先级",
        "idempotency_key": "幂等键",
        "idempotency_placeholder": "可选去重键",
        "structured_payload_json": "结构化载荷 JSON",
        "publish_structured_command": "发布结构化命令",
        "quick_publish": "快速发布 {name}",
        "no_heartbeats": "还没有心跳。",
        "heartbeats_desc": "调用 `agent_heartbeat` 或 `memory_begin_task` 后，这里会出现代理状态。",
        "last_heartbeat": "最近心跳 {value}",
        "no_candidates": "还没有候选条目。",
        "candidates_desc": "记忆提案和冲突审查会显示在这里。",
        "review": "审查",
        "no_memory_entries": "没有找到记忆条目。",
        "try_another_filter": "可以换一个会话或状态筛选条件。",
        "conflict": "冲突",
        "session": "会话",
        "proposed_by": "提出者",
        "runtime": "运行时",
        "created": "创建时间",
        "full_content": "完整内容",
        "structured_metadata": "结构化元数据",
        "global": "全局",
        "unknown": "未知",
        "no_summary": "（无摘要）",
        "no_active_conflicts": "当前没有活动冲突。",
        "conflict_review_empty": "所选会话当前没有冲突审查项。",
        "conflict_count_label": "{count} 个冲突",
        "recommended_action": "建议动作：{value}",
        "no_timeline": "还没有时间线事件。",
        "timeline_desc": "事件 API、命令变化和记忆动作会流式显示在这里。",
        "seq": "序号 {value}",
        "no_audit_entries": "还没有审计记录。",
        "not_available": "无",
        "no_digests": "还没有摘要。",
        "digests_desc": "每 10 个事件或执行 task commit 时会自动生成摘要。",
        "committed_session": "已提交会话",
        "last_commit_at": "最近提交时间：{value}。",
        "uncommitted_session": "未提交会话",
        "uncommitted_desc": "这个会话还没有通过 `memory_commit_task` 封存。",
        "published_command": "已为会话 {session_id} 发布命令 {command_id}。",
        "payload_json_error": "payload 必须是合法 JSON：{message}",
        "payload_object_error": "payload 必须解析为 JSON 对象",
        "session_required_error": "必须提供 session_id",
        "language": "语言",
    },
}


class MissionControlUI:
    """Render a lightweight operator-facing HTML control plane."""

    def __init__(
        self,
        storage: RelayCoreStorage,
        command_bus: CommandBusService,
        event_log: EventLogService,
        memory_quality: MemoryQualityService,
    ) -> None:
        self.storage = storage
        self.command_bus = command_bus
        self.event_log = event_log
        self.memory_quality = memory_quality
        self.collaboration_modes = CollaborationModeRegistry()

    def _normalize_lang(self, lang: Optional[str]) -> str:
        cleaned = (lang or "en").strip().lower()
        return cleaned if cleaned in SUPPORTED_LANGS else "en"

    def _t(self, lang: str, key: str, **values: Any) -> str:
        text = UI_TEXT[self._normalize_lang(lang)].get(key, UI_TEXT["en"].get(key, key))
        return text.format(**values)

    def _lang_link(self, path: str, lang: str, **params: Any) -> str:
        query = [("lang", lang)]
        for key, value in params.items():
            if value not in (None, ""):
                query.append((key, value))
        return "{}?{}".format(path, "&".join("{}={}".format(key, quote(str(value))) for key, value in query))

    def _display_status(self, lang: str, value: Optional[str]) -> str:
        labels = {
            "pending": {"en": "pending", "zh": "待处理"},
            "active": {"en": "active", "zh": "活跃"},
            "merged": {"en": "merged", "zh": "已合并"},
            "corrected": {"en": "corrected", "zh": "已修正"},
            "superseded": {"en": "superseded", "zh": "已替换"},
            "archived": {"en": "archived", "zh": "已归档"},
            "rejected": {"en": "rejected", "zh": "已拒绝"},
        }
        if not value:
            return self._t(lang, "all")
        return labels.get(value, {}).get(self._normalize_lang(lang), value)

    def _display_memory_type(self, lang: str, value: Optional[str]) -> str:
        labels = {
            "decision": {"en": "decision", "zh": "决策"},
            "rule": {"en": "rule", "zh": "规则"},
            "fact": {"en": "fact", "zh": "事实"},
            "note": {"en": "note", "zh": "笔记"},
            "all": {"en": "all", "zh": "全部"},
        }
        if not value:
            return self._t(lang, "all")
        return labels.get(value, {}).get(self._normalize_lang(lang), value)

    def render_dashboard(
        self,
        *,
        session_id: Optional[str] = None,
        flash: Optional[str] = None,
        error: Optional[str] = None,
        lang: Optional[str] = None,
    ) -> str:
        lang = self._normalize_lang(lang)
        sessions = self.storage.list_sessions()
        selected_session = self._resolve_session(session_id, sessions)
        selected_id = selected_session.session_id if selected_session else None

        commands = self.storage.list_commands(session_id=selected_id, limit=12) if selected_id else []
        events = self.event_log.list_events(selected_id, limit=18) if selected_id else []
        candidates = self.storage.list_memory_candidates(session_id=selected_id, limit=12) if selected_id else []
        digests = self.storage.list_session_digests(selected_id, limit=6) if selected_id else []
        agent_states = self.storage.list_agent_states(session_id=selected_id, limit=12) if selected_id else []
        audit_logs = self.storage.list_audit_logs(limit=12)
        conflicts = [candidate for candidate in candidates if candidate.status == "pending" and candidate.conflicts_with]
        token_snapshot = self._build_token_snapshot(selected_session, commands, events, candidates, digests)
        commit_warning = self._render_commit_warning(selected_session, lang)

        return """<!DOCTYPE html>
<html lang="{page_lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{document_title}</title>
  <style>
    :root {{
      --sand: #f5efe1;
      --ink: #1f1b17;
      --ember: #c5562b;
      --clay: #9c3d26;
      --moss: #365c47;
      --steel: #3d4953;
      --paper: rgba(255,255,255,0.84);
      --line: rgba(31,27,23,0.12);
      --shadow: 0 22px 60px rgba(34,22,16,0.14);
      --mono: "IBM Plex Mono", "SFMono-Regular", Menlo, monospace;
      --sans: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: var(--sans);
      background:
        radial-gradient(circle at top left, rgba(197,86,43,0.16), transparent 28%),
        radial-gradient(circle at top right, rgba(54,92,71,0.14), transparent 24%),
        linear-gradient(180deg, #fbf6eb 0%, #efe3cf 100%);
      min-height: 100vh;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image: linear-gradient(rgba(31,27,23,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(31,27,23,0.03) 1px, transparent 1px);
      background-size: 26px 26px;
      mask-image: linear-gradient(180deg, rgba(0,0,0,0.55), transparent 78%);
    }}
    .shell {{
      width: min(1380px, calc(100vw - 32px));
      margin: 24px auto 56px;
    }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }}
    .nav-links {{
      display: inline-flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .nav-links a {{
      text-decoration: none;
      color: var(--steel);
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(31,27,23,0.08);
      border-radius: 999px;
      padding: 9px 12px;
      font-size: 13px;
    }}
    .nav-links a.active {{
      color: white;
      background: linear-gradient(135deg, var(--ember), var(--clay));
      border-color: transparent;
    }}
    .lang-switch {{
      display: inline-flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .lang-switch a {{
      text-decoration: none;
      color: var(--steel);
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(31,27,23,0.08);
      border-radius: 999px;
      padding: 9px 12px;
      font-size: 13px;
    }}
    .lang-switch a.active {{
      color: white;
      background: linear-gradient(135deg, var(--moss), var(--steel));
      border-color: transparent;
    }}
    .hero {{
      position: relative;
      overflow: hidden;
      background: linear-gradient(135deg, rgba(245,239,225,0.92), rgba(255,248,236,0.82));
      border: 1px solid rgba(31,27,23,0.08);
      border-radius: 28px;
      box-shadow: var(--shadow);
      padding: 28px 28px 24px;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      inset: auto -80px -80px auto;
      width: 220px;
      height: 220px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(197,86,43,0.22), transparent 68%);
    }}
    .eyebrow {{
      display: inline-flex;
      gap: 8px;
      align-items: center;
      font-family: var(--mono);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      color: var(--clay);
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(197,86,43,0.08);
    }}
    h1 {{
      margin: 14px 0 10px;
      font-size: clamp(2rem, 4vw, 3.5rem);
      line-height: 0.96;
      letter-spacing: -0.04em;
    }}
    .hero p {{
      max-width: 72ch;
      margin: 0;
      color: rgba(31,27,23,0.8);
      font-size: 1.02rem;
      line-height: 1.55;
    }}
    .metrics {{
      margin-top: 22px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
    }}
    .metric {{
      background: rgba(255,255,255,0.66);
      border: 1px solid rgba(31,27,23,0.08);
      border-radius: 18px;
      padding: 14px 16px;
      backdrop-filter: blur(6px);
    }}
    .metric strong {{
      display: block;
      font-size: 1.45rem;
      margin-top: 4px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 290px 1fr;
      gap: 18px;
      margin-top: 18px;
    }}
    .sidebar, .panel {{
      background: var(--paper);
      border: 1px solid rgba(31,27,23,0.08);
      border-radius: 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }}
    .sidebar {{
      padding: 18px;
      align-self: start;
      position: sticky;
      top: 18px;
    }}
    .content {{
      display: grid;
      gap: 18px;
    }}
    .panel {{
      padding: 20px;
    }}
    .panel h2 {{
      margin: 0 0 6px;
      font-size: 1.2rem;
      letter-spacing: -0.02em;
    }}
    .panel p.lead {{
      margin: 0 0 16px;
      color: rgba(31,27,23,0.68);
    }}
    .session-list {{
      display: grid;
      gap: 10px;
      margin-top: 16px;
    }}
    .session-card {{
      display: block;
      text-decoration: none;
      color: inherit;
      border-radius: 18px;
      padding: 14px;
      border: 1px solid rgba(31,27,23,0.08);
      background: rgba(255,255,255,0.74);
      transition: transform 140ms ease, border-color 140ms ease, background 140ms ease;
    }}
    .session-card:hover {{
      transform: translateY(-1px);
      border-color: rgba(197,86,43,0.35);
      background: rgba(255,252,247,0.92);
    }}
    .session-card.active {{
      border-color: rgba(197,86,43,0.5);
      background: linear-gradient(135deg, rgba(197,86,43,0.14), rgba(255,255,255,0.86));
    }}
    .session-card small, .muted {{
      color: rgba(31,27,23,0.6);
    }}
    .stack {{
      display: grid;
      gap: 14px;
    }}
    .two-up {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }}
    .three-up {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-family: var(--mono);
      background: rgba(54,92,71,0.1);
      color: var(--moss);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .badge.warn {{
      background: rgba(197,86,43,0.12);
      color: var(--clay);
    }}
    .list {{
      display: grid;
      gap: 12px;
    }}
    .list-item {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,0.58);
    }}
    .list-item pre {{
      margin: 10px 0 0;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
      color: #3b332c;
    }}
    .timeline {{
      display: grid;
      gap: 12px;
    }}
    .timeline-item {{
      position: relative;
      padding: 14px 14px 14px 18px;
      border-left: 4px solid rgba(54,92,71,0.24);
      border-radius: 0 18px 18px 0;
      background: rgba(255,255,255,0.56);
    }}
    .timeline-item.live {{
      animation: pulse 1.4s ease;
    }}
    @keyframes pulse {{
      0% {{ transform: translateX(4px); background: rgba(197,86,43,0.16); }}
      100% {{ transform: translateX(0); background: rgba(255,255,255,0.56); }}
    }}
    .kvs {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px 18px;
      margin-top: 10px;
    }}
    .kvs div {{
      padding: 10px 12px;
      border-radius: 14px;
      background: rgba(255,255,255,0.62);
      border: 1px solid var(--line);
    }}
    form {{
      display: grid;
      gap: 12px;
    }}
    label {{
      display: grid;
      gap: 6px;
      font-size: 14px;
      color: rgba(31,27,23,0.76);
    }}
    input, textarea, select, button {{
      font: inherit;
    }}
    input, textarea, select {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid rgba(31,27,23,0.14);
      padding: 11px 12px;
      background: rgba(255,255,255,0.9);
      color: var(--ink);
    }}
    textarea {{
      min-height: 112px;
      resize: vertical;
      font-family: var(--mono);
      font-size: 13px;
    }}
    button {{
      border: 0;
      cursor: pointer;
      border-radius: 16px;
      padding: 12px 16px;
      background: linear-gradient(135deg, var(--ember), var(--clay));
      color: white;
      box-shadow: 0 10px 24px rgba(156,61,38,0.25);
      font-weight: 600;
    }}
    .flash {{
      margin-top: 14px;
      padding: 12px 14px;
      border-radius: 16px;
      font-size: 14px;
    }}
    .flash.ok {{
      background: rgba(54,92,71,0.12);
      color: var(--moss);
      border: 1px solid rgba(54,92,71,0.16);
    }}
    .flash.error {{
      background: rgba(197,86,43,0.14);
      color: var(--clay);
      border: 1px solid rgba(197,86,43,0.18);
    }}
    .section-title {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
    }}
    .token-bar {{
      position: relative;
      overflow: hidden;
      height: 12px;
      border-radius: 999px;
      background: rgba(31,27,23,0.08);
      margin-top: 10px;
    }}
    .token-bar span {{
      display: block;
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--moss), var(--ember));
      width: {token_percent}%;
    }}
    code {{
      font-family: var(--mono);
      font-size: 12px;
    }}
    @media (max-width: 1080px) {{
      .grid {{
        grid-template-columns: 1fr;
      }}
      .sidebar {{
        position: static;
      }}
      .two-up, .three-up {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="topbar">
      <div class="nav-links">
        <a class="active" href="{dashboard_link}">{nav_mission}</a>
        <a href="{memory_link}">{nav_memory}</a>
      </div>
      <div class="lang-switch">
        <a class="{lang_en_active}" href="{lang_en_link}">{lang_en_label}</a>
        <a class="{lang_zh_active}" href="{lang_zh_link}">{lang_zh_label}</a>
      </div>
    </div>
    <section class="hero">
      <span class="eyebrow">{eyebrow_dashboard}</span>
      <h1>{dashboard_title}</h1>
      <p>{dashboard_body}</p>
      <div class="metrics">
        <div class="metric"><small>{metric_sessions}</small><strong>{session_count}</strong></div>
        <div class="metric"><small>{metric_agent_states}</small><strong>{agent_count}</strong></div>
        <div class="metric"><small>{metric_pending_commands}</small><strong>{pending_count}</strong></div>
        <div class="metric"><small>{metric_recent_events}</small><strong>{event_count}</strong></div>
      </div>
      {flash_html}
      {error_html}
    </section>
    <div class="grid">
      <aside class="sidebar">
        <div class="section-title"><h2>{sessions_label}</h2><span class="badge">{session_tracked_label}</span></div>
        <div class="session-list">
          {session_cards}
        </div>
      </aside>
      <main class="content">
        <section class="panel">
          <div class="section-title">
            <div>
              <h2>{session_detail_label}</h2>
              <p class="lead">{session_detail_lead}</p>
            </div>
            <span class="badge">{selected_label}</span>
          </div>
          {commit_warning}
          {session_detail}
        </section>
        <section class="panel">
          <div class="section-title">
            <div>
              <h2>{command_publisher_label}</h2>
              <p class="lead">{command_publisher_lead}</p>
            </div>
            <span class="badge warn">{no_shell_execution}</span>
          </div>
          {command_form}
        </section>
        <section class="panel">
          <div class="section-title">
            <div>
              <h2>{collaboration_modes_label}</h2>
              <p class="lead">{collaboration_modes_lead}</p>
            </div>
            <span class="badge">{mode_templates_label}</span>
          </div>
          <div class="list">{mode_cards}</div>
        </section>
        <div class="two-up">
          <section class="panel">
            <div class="section-title"><h2>{agent_states_label}</h2><span class="badge">{agent_live_label}</span></div>
            <div class="list">{agent_state_items}</div>
          </section>
          <section class="panel">
            <div class="section-title"><h2>{token_budget_label}</h2><span class="badge">{token_estimate_label}</span></div>
            <p class="lead">{token_budget_lead}</p>
            <div class="kvs">
              <div><small>{memory_context_label}</small><strong>{memory_tokens}</strong></div>
              <div><small>{event_digest_label}</small><strong>{digest_tokens}</strong></div>
              <div><small>{command_payloads_label}</small><strong>{command_tokens}</strong></div>
              <div><small>{candidate_summaries_label}</small><strong>{candidate_tokens}</strong></div>
            </div>
            <div class="token-bar"><span></span></div>
            <p class="muted">{token_note}</p>
          </section>
        </div>
        <div class="two-up">
          <section class="panel">
            <div class="section-title"><h2>{memory_candidate_queue_label}</h2><span class="badge">{candidate_queue_label}</span></div>
            <div class="list">{candidate_items}</div>
          </section>
          <section class="panel">
            <div class="section-title"><h2>{conflict_resolution_label}</h2><span class="badge warn">{conflict_count_label}</span></div>
            <div class="list">{conflict_items}</div>
          </section>
        </div>
        <div class="two-up">
          <section class="panel">
            <div class="section-title"><h2>{live_timeline_label}</h2><span class="badge">{sse_ready_label}</span></div>
            <div id="timeline" class="timeline">{timeline_items}</div>
          </section>
          <section class="panel">
            <div class="section-title"><h2>{audit_log_label}</h2><span class="badge">{audit_recent_label}</span></div>
            <div class="list">{audit_items}</div>
          </section>
        </div>
        <section class="panel">
          <div class="section-title"><h2>{recent_digests_label}</h2><span class="badge">{digest_compact_label}</span></div>
          <div class="list">{digest_items}</div>
        </section>
      </main>
    </div>
  </div>
  <script>
    (function() {{
      var sessionId = {selected_session_json};
      if (!sessionId) return;
      var timeline = document.getElementById("timeline");
      if (!timeline || !window.EventSource) return;
      var source = new EventSource("/api/events/stream?session_id=" + encodeURIComponent(sessionId) + "&limit=5");
      source.addEventListener("event", function(evt) {{
        try {{
          var payload = JSON.parse(evt.data);
          var item = document.createElement("article");
          item.className = "timeline-item live";
          item.innerHTML =
            "<strong>" + payload.event.event_type + "</strong>" +
            "<div class='muted'>" + payload.event.agent_id + " · seq " + payload.event.seq + "</div>" +
            "<pre>" + JSON.stringify(payload.event.content, null, 2) + "</pre>";
          timeline.insertBefore(item, timeline.firstChild);
        }} catch (error) {{
          console.warn("Event parse failed", error);
        }}
      }});
    }})();
  </script>
</body>
        </html>""".format(
            page_lang=_esc(lang),
            document_title=_esc(self._t(lang, "eyebrow_dashboard")),
            dashboard_link=self._lang_link("/mission-control", lang, session_id=selected_id),
            memory_link=self._lang_link("/mission-control/memories", lang, session_id=selected_id),
            nav_mission=_esc(self._t(lang, "mission_control")),
            nav_memory=_esc(self._t(lang, "memory_viewer")),
            lang_en_active="active" if lang == "en" else "",
            lang_zh_active="active" if lang == "zh" else "",
            lang_en_link=self._lang_link("/mission-control", "en", session_id=selected_id),
            lang_zh_link=self._lang_link("/mission-control", "zh", session_id=selected_id),
            lang_en_label=_esc(self._t(lang, "lang_en")),
            lang_zh_label=_esc(self._t(lang, "lang_zh")),
            eyebrow_dashboard=_esc(self._t(lang, "eyebrow_dashboard")),
            dashboard_title=_esc(self._t(lang, "dashboard_title")),
            dashboard_body=_esc(self._t(lang, "dashboard_body")),
            metric_sessions=_esc(self._t(lang, "sessions")),
            metric_agent_states=_esc(self._t(lang, "agent_states")),
            metric_pending_commands=_esc(self._t(lang, "pending_commands")),
            metric_recent_events=_esc(self._t(lang, "recent_events")),
            sessions_label=_esc(self._t(lang, "sessions")),
            session_tracked_label=_esc(self._t(lang, "tracked_count", count=len(sessions))),
            session_detail_label=_esc(self._t(lang, "session_detail")),
            session_detail_lead=_esc(self._t(lang, "session_detail_lead")),
            command_publisher_label=_esc(self._t(lang, "command_publisher")),
            command_publisher_lead=_esc(self._t(lang, "command_publisher_lead")),
            no_shell_execution=_esc(self._t(lang, "no_shell_execution")),
            collaboration_modes_label=_esc(self._t(lang, "collaboration_modes")),
            collaboration_modes_lead=_esc(self._t(lang, "collaboration_modes_lead")),
            mode_templates_label=_esc(self._t(lang, "templates_count", count=len(self.collaboration_modes.list()))),
            agent_states_label=_esc(self._t(lang, "agent_states")),
            agent_live_label=_esc(self._t(lang, "live_count", count=len(agent_states))),
            token_budget_label=_esc(self._t(lang, "token_budget_monitor")),
            token_estimate_label=_esc(self._t(lang, "est_count", count=token_snapshot["total"])),
            token_budget_lead=_esc(self._t(lang, "token_budget_lead")),
            memory_context_label=_esc(self._t(lang, "memory_context")),
            event_digest_label=_esc(self._t(lang, "event_digest")),
            command_payloads_label=_esc(self._t(lang, "command_payloads")),
            candidate_summaries_label=_esc(self._t(lang, "candidate_summaries")),
            token_note=_esc(self._t(lang, "token_note")),
            memory_candidate_queue_label=_esc(self._t(lang, "memory_candidate_queue")),
            candidate_queue_label=_esc(self._t(lang, "queued_count", count=len(candidates))),
            conflict_resolution_label=_esc(self._t(lang, "conflict_resolution_panel")),
            conflict_count_label=_esc(self._t(lang, "conflicts_count", count=len(conflicts))),
            live_timeline_label=_esc(self._t(lang, "live_timeline")),
            sse_ready_label=_esc(self._t(lang, "sse_ready")),
            audit_log_label=_esc(self._t(lang, "audit_log_viewer")),
            audit_recent_label=_esc(self._t(lang, "recent_count", count=len(audit_logs))),
            recent_digests_label=_esc(self._t(lang, "recent_digests")),
            digest_compact_label=_esc(self._t(lang, "compact_count", count=len(digests))),
            token_percent=min(100, token_snapshot["percent"]),
            session_count=len(sessions),
            agent_count=len(agent_states),
            pending_count=len([command for command in commands if command.status == "pending"]),
            event_count=len(events),
            flash_html=self._flash_html(flash, ok=True),
            error_html=self._flash_html(error, ok=False),
            session_cards=self._render_session_cards(sessions, selected_id, lang),
            selected_label=_esc(selected_id or self._t(lang, "no_session_selected")),
            commit_warning=commit_warning,
            session_detail=self._render_session_detail(selected_session, commands, events, lang),
            command_form=self._render_command_form(selected_id, lang),
            mode_cards=self._render_mode_cards(selected_id, lang),
            agent_state_count=len(agent_states),
            agent_state_items=self._render_agent_states(agent_states, lang),
            token_estimate=_esc(token_snapshot["total"]),
            memory_tokens=_esc(token_snapshot["memory_tokens"]),
            digest_tokens=_esc(token_snapshot["digest_tokens"]),
            command_tokens=_esc(token_snapshot["command_tokens"]),
            candidate_tokens=_esc(token_snapshot["candidate_tokens"]),
            candidate_count=len(candidates),
            candidate_items=self._render_candidates(candidates, lang),
            conflict_count=len(conflicts),
            conflict_items=self._render_conflicts(conflicts, selected_id, lang),
            timeline_items=self._render_timeline(events, lang),
            audit_count=len(audit_logs),
            audit_items=self._render_audit_logs(audit_logs, lang),
            digest_count=len(digests),
            digest_items=self._render_digests(digests, lang),
            selected_session_json=json.dumps(selected_id),
        )

    def handle_command_form(self, form: Dict[str, Any], *, lang: Optional[str] = None) -> str:
        lang = self._normalize_lang(lang)
        payload_text = form.get("payload", "{}")
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise ValueError(self._t(lang, "payload_json_error", message=exc.msg))
        if not isinstance(payload, dict):
            raise ValueError(self._t(lang, "payload_object_error"))

        session_id = str(form.get("session_id", "")).strip()
        if not session_id:
            raise ValueError(self._t(lang, "session_required_error"))

        command = self.command_bus.publish_command(
            session_id=session_id,
            mode=str(form.get("mode", "assist")).strip() or "assist",
            command_type=str(form.get("command_type", "")).strip(),
            payload=payload,
            created_by=str(form.get("created_by", "mission-control")).strip() or "mission-control",
            target_agent=self._nullable(form.get("target_agent")),
            target_runtime=self._nullable(form.get("target_runtime")),
            priority=int(form.get("priority", 100)),
            permission_level=str(form.get("permission_level", "L1")).strip() or "L1",
            idempotency_key=self._nullable(form.get("idempotency_key")),
        )
        return self._t(lang, "published_command", command_id=command.command_id, session_id=session_id)

    def handle_conflict_form(self, form: Dict[str, Any], *, lang: Optional[str] = None) -> str:
        lang = self._normalize_lang(lang)
        candidate_id = str(form.get("candidate_id", "")).strip()
        if not candidate_id:
            raise ValueError("candidate_id is required")
        status = str(form.get("status", "")).strip() or "active"
        actor = str(form.get("created_by", "mission-control")).strip() or "mission-control"
        candidate = self.memory_quality.resolve_candidate(
            candidate_id,
            status=status,
            actor=actor,
            runtime=self._nullable(form.get("runtime")),
            mode=self._nullable(form.get("mode")),
            recommended_action=self._nullable(form.get("recommended_action")),
            metadata={"source": "mission-control", "session_id": self._nullable(form.get("session_id"))},
        )
        return "Resolved candidate {} as {}.".format(candidate.candidate_id, candidate.status)

    def render_memory_page(
        self,
        *,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        memory_type: Optional[str] = None,
        query: Optional[str] = None,
        lang: Optional[str] = None,
    ) -> str:
        lang = self._normalize_lang(lang)
        sessions = self.storage.list_sessions()
        selected_session = self._resolve_session(session_id, sessions)
        selected_id = selected_session.session_id if selected_session else None
        allowed_statuses = {
            "pending",
            "active",
            "merged",
            "corrected",
            "superseded",
            "archived",
            "rejected",
        }
        selected_status = status if status in allowed_statuses else None
        normalized_query = " ".join((query or "").split())
        all_candidates = (
            self.storage.list_memory_candidates(session_id=selected_id, limit=200)
            if selected_id is not None
            else self.storage.list_memory_candidates(limit=200)
        )
        available_types = self._memory_types(all_candidates)
        selected_type = memory_type if memory_type in available_types else None
        candidates = self._filter_memory_candidates(
            all_candidates,
            status=selected_status,
            memory_type=selected_type,
            query=normalized_query,
        )
        session_scope = self._filter_memory_candidates(
            all_candidates,
            memory_type=selected_type,
            query=normalized_query,
        )
        counts = self._memory_status_counts(session_scope)
        type_counts = self._memory_type_counts(
            self._filter_memory_candidates(
                all_candidates,
                status=selected_status,
                query=normalized_query,
            )
        )

        return """<!DOCTYPE html>
<html lang="{page_lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{document_title}</title>
  <style>
    :root {{
      --sand: #f5efe1;
      --ink: #1f1b17;
      --ember: #c5562b;
      --clay: #9c3d26;
      --moss: #365c47;
      --steel: #3d4953;
      --paper: rgba(255,255,255,0.84);
      --line: rgba(31,27,23,0.12);
      --shadow: 0 22px 60px rgba(34,22,16,0.14);
      --mono: "IBM Plex Mono", "SFMono-Regular", Menlo, monospace;
      --sans: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: var(--sans);
      background:
        radial-gradient(circle at top left, rgba(197,86,43,0.16), transparent 28%),
        radial-gradient(circle at top right, rgba(54,92,71,0.14), transparent 24%),
        linear-gradient(180deg, #fbf6eb 0%, #efe3cf 100%);
      min-height: 100vh;
    }}
    .shell {{
      width: min(1380px, calc(100vw - 32px));
      margin: 24px auto 56px;
    }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }}
    .nav-links {{
      display: inline-flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .nav-links a {{
      text-decoration: none;
      color: var(--steel);
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(31,27,23,0.08);
      border-radius: 999px;
      padding: 9px 12px;
      font-size: 13px;
    }}
    .nav-links a.active {{
      color: white;
      background: linear-gradient(135deg, var(--ember), var(--clay));
      border-color: transparent;
    }}
    .lang-switch {{
      display: inline-flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .lang-switch a {{
      text-decoration: none;
      color: var(--steel);
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(31,27,23,0.08);
      border-radius: 999px;
      padding: 9px 12px;
      font-size: 13px;
    }}
    .lang-switch a.active {{
      color: white;
      background: linear-gradient(135deg, var(--moss), var(--steel));
      border-color: transparent;
    }}
    .hero, .sidebar, .panel {{
      background: var(--paper);
      border: 1px solid rgba(31,27,23,0.08);
      border-radius: 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }}
    .hero {{
      padding: 24px 26px;
      margin-bottom: 18px;
    }}
    .eyebrow {{
      display: inline-flex;
      gap: 8px;
      align-items: center;
      font-family: var(--mono);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      color: var(--clay);
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(197,86,43,0.08);
    }}
    h1 {{
      margin: 14px 0 10px;
      font-size: clamp(2rem, 4vw, 3.2rem);
      line-height: 0.98;
      letter-spacing: -0.04em;
    }}
    .lead {{
      margin: 0;
      color: rgba(31,27,23,0.76);
      line-height: 1.55;
    }}
    .metrics {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
    }}
    .metric {{
      background: rgba(255,255,255,0.66);
      border: 1px solid rgba(31,27,23,0.08);
      border-radius: 18px;
      padding: 14px 16px;
    }}
    .metric strong {{
      display: block;
      font-size: 1.4rem;
      margin-top: 4px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 290px 1fr;
      gap: 18px;
    }}
    .sidebar, .panel {{
      padding: 18px;
    }}
    .sidebar {{
      align-self: start;
      position: sticky;
      top: 18px;
    }}
    .session-list, .memory-list {{
      display: grid;
      gap: 10px;
      margin-top: 14px;
    }}
    .session-card, .filter-link {{
      display: block;
      text-decoration: none;
      color: inherit;
      border-radius: 16px;
      padding: 12px 14px;
      border: 1px solid rgba(31,27,23,0.08);
      background: rgba(255,255,255,0.72);
    }}
    .session-card.active, .filter-link.active {{
      border-color: rgba(197,86,43,0.5);
      background: linear-gradient(135deg, rgba(197,86,43,0.14), rgba(255,255,255,0.86));
    }}
    .memory-list {{
      margin-top: 0;
    }}
    .toolbar {{
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.85fr);
      gap: 16px;
      margin-bottom: 18px;
    }}
    .search-panel, .scope-panel {{
      border: 1px solid rgba(31,27,23,0.08);
      border-radius: 18px;
      background: rgba(255,255,255,0.72);
      padding: 14px;
    }}
    .search-form {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      align-items: end;
    }}
    .field {{
      display: grid;
      gap: 6px;
      font-size: 13px;
      color: rgba(31,27,23,0.74);
    }}
    .field input {{
      width: 100%;
      border: 1px solid rgba(31,27,23,0.14);
      border-radius: 12px;
      padding: 11px 12px;
      background: rgba(255,255,255,0.95);
      color: var(--ink);
      font: inherit;
    }}
    .search-actions {{
      display: inline-flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .search-actions button, .search-actions a {{
      border: 0;
      text-decoration: none;
      border-radius: 999px;
      padding: 11px 14px;
      font: inherit;
      cursor: pointer;
    }}
    .search-actions button {{
      color: white;
      background: linear-gradient(135deg, var(--ember), var(--clay));
    }}
    .search-actions a {{
      color: var(--steel);
      background: rgba(31,27,23,0.06);
    }}
    .scope-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 10px;
      margin-top: 10px;
    }}
    .scope-chip {{
      display: block;
      text-decoration: none;
      color: inherit;
      border-radius: 14px;
      padding: 10px 12px;
      border: 1px solid rgba(31,27,23,0.08);
      background: rgba(255,255,255,0.8);
    }}
    .scope-chip.active {{
      border-color: rgba(54,92,71,0.4);
      background: linear-gradient(135deg, rgba(54,92,71,0.12), rgba(255,255,255,0.9));
    }}
    .memory-card {{
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 16px;
      background: rgba(255,255,255,0.64);
    }}
    .memory-card pre {{
      margin: 10px 0 0;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
      color: #3b332c;
    }}
    .row {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
      margin-bottom: 10px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-family: var(--mono);
      background: rgba(54,92,71,0.1);
      color: var(--moss);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .badge.warn {{
      background: rgba(197,86,43,0.12);
      color: var(--clay);
    }}
    .muted {{
      color: rgba(31,27,23,0.62);
    }}
    .section-title {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
      margin-bottom: 14px;
    }}
    details {{
      margin-top: 10px;
    }}
    summary {{
      cursor: pointer;
      font-family: var(--mono);
      font-size: 12px;
      color: var(--steel);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    @media (max-width: 1080px) {{
      .grid {{
        grid-template-columns: 1fr;
      }}
      .sidebar {{
        position: static;
      }}
      .toolbar {{
        grid-template-columns: 1fr;
      }}
      .search-form {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="topbar">
      <div class="nav-links">
        <a href="{dashboard_link}">{nav_mission}</a>
        <a class="active" href="{memory_link}">{nav_memory}</a>
      </div>
      <div class="lang-switch">
        <a class="{lang_en_active}" href="{lang_en_link}">{lang_en_label}</a>
        <a class="{lang_zh_active}" href="{lang_zh_link}">{lang_zh_label}</a>
      </div>
    </div>
    <section class="hero">
      <span class="eyebrow">{eyebrow_memory}</span>
      <h1>{memory_title}</h1>
      <p class="lead">{memory_body}</p>
      <div class="metrics">
        <div class="metric"><small>{total_in_scope}</small><strong>{total_count}</strong></div>
        <div class="metric"><small>{active_label}</small><strong>{active_count}</strong></div>
        <div class="metric"><small>{pending_label}</small><strong>{pending_count}</strong></div>
        <div class="metric"><small>{rejected_label}</small><strong>{rejected_count}</strong></div>
      </div>
    </section>
    <div class="grid">
      <aside class="sidebar">
        <div class="section-title"><h2>{sessions_label}</h2><span class="badge">{session_tracked_label}</span></div>
        <div class="session-list">{session_cards}</div>
        <div class="section-title" style="margin-top:18px;"><h2>{status_filters_label}</h2><span class="badge">{current_status}</span></div>
        <div class="session-list">{filter_links}</div>
        <div class="section-title" style="margin-top:18px;"><h2>{type_filters_label}</h2><span class="badge">{current_type}</span></div>
        <div class="session-list">{type_links}</div>
      </aside>
      <main class="panel">
        <div class="toolbar">
          <section class="search-panel">
            <div class="section-title"><h2>{search_memory_label}</h2><span class="badge">{search_state}</span></div>
            <form class="search-form" method="get" action="/mission-control/memories">
              <input type="hidden" name="lang" value="{page_lang}">
              <input type="hidden" name="session_id" value="{selected_session_id}">
              <input type="hidden" name="status" value="{selected_status_value}">
              <input type="hidden" name="type" value="{selected_type_value}">
              <label class="field">{query_label}
                <input name="q" value="{query_value}" placeholder="{query_placeholder}">
              </label>
              <div class="search-actions">
                <button type="submit">{apply_search_label}</button>
                <a href="{clear_link}">{clear_label}</a>
              </div>
            </form>
          </section>
          <section class="scope-panel">
            <div class="section-title"><h2>{current_scope_label}</h2><span class="badge">{memory_count_label}</span></div>
            <div class="scope-grid">
              <a class="scope-chip active" href="{session_link}"><strong>{scope_session}</strong><div class="muted">{scope_session_label}</div></a>
              <a class="scope-chip active" href="{status_link}"><strong>{scope_status}</strong><div class="muted">{scope_status_label}</div></a>
              <a class="scope-chip active" href="{type_link}"><strong>{scope_type}</strong><div class="muted">{scope_type_label}</div></a>
              <a class="scope-chip active" href="{search_link}"><strong>{scope_query}</strong><div class="muted">{scope_search_label}</div></a>
            </div>
          </section>
        </div>
        <div class="section-title"><h2>{memory_entries_label}</h2><span class="badge">{memory_count_label}</span></div>
        <div class="memory-list">{memory_items}</div>
      </main>
    </div>
  </div>
</body>
</html>""".format(
            page_lang=_esc(lang),
            document_title=_esc(self._t(lang, "eyebrow_memory")),
            dashboard_link=self._lang_link("/mission-control", lang, session_id=selected_id),
            memory_link=self._lang_link("/mission-control/memories", lang, session_id=selected_id, status=selected_status, type=selected_type, q=normalized_query),
            nav_mission=_esc(self._t(lang, "mission_control")),
            nav_memory=_esc(self._t(lang, "memory_viewer")),
            lang_en_active="active" if lang == "en" else "",
            lang_zh_active="active" if lang == "zh" else "",
            lang_en_link=self._lang_link("/mission-control/memories", "en", session_id=selected_id, status=selected_status, type=selected_type, q=normalized_query),
            lang_zh_link=self._lang_link("/mission-control/memories", "zh", session_id=selected_id, status=selected_status, type=selected_type, q=normalized_query),
            lang_en_label=_esc(self._t(lang, "lang_en")),
            lang_zh_label=_esc(self._t(lang, "lang_zh")),
            eyebrow_memory=_esc(self._t(lang, "eyebrow_memory")),
            memory_title=_esc(self._t(lang, "memory_title")),
            memory_body=_esc(self._t(lang, "memory_body")),
            total_in_scope=_esc(self._t(lang, "total_in_scope")),
            active_label=_esc(self._t(lang, "active")),
            pending_label=_esc(self._t(lang, "pending")),
            rejected_label=_esc(self._t(lang, "rejected")),
            total_count=len(session_scope),
            active_count=counts.get("active", 0),
            pending_count=counts.get("pending", 0),
            rejected_count=counts.get("rejected", 0),
            session_count=len(sessions),
            sessions_label=_esc(self._t(lang, "sessions")),
            session_tracked_label=_esc(self._t(lang, "tracked_count", count=len(sessions))),
            session_cards=self._render_memory_session_cards(sessions, selected_id, selected_status, selected_type, normalized_query, lang),
            status_filters_label=_esc(self._t(lang, "status_filters")),
            current_status=_esc(self._display_status(lang, selected_status)),
            filter_links=self._render_memory_filter_links(selected_id, selected_status, selected_type, normalized_query, counts, lang),
            type_filters_label=_esc(self._t(lang, "type_filters")),
            current_type=_esc(self._display_memory_type(lang, selected_type)),
            type_links=self._render_memory_type_links(selected_id, selected_status, selected_type, normalized_query, type_counts, lang),
            search_memory_label=_esc(self._t(lang, "search_memory")),
            search_state=_esc(self._t(lang, "search_active" if normalized_query else "search_empty")),
            selected_session_id=_esc(selected_id or ""),
            selected_status_value=_esc(selected_status or ""),
            selected_type_value=_esc(selected_type or ""),
            query_label=_esc(self._t(lang, "query")),
            query_value=_esc(normalized_query),
            query_placeholder=_esc(self._t(lang, "query_placeholder")),
            apply_search_label=_esc(self._t(lang, "apply_search")),
            clear_label=_esc(self._t(lang, "clear")),
            clear_link=self._memory_link(selected_id, selected_status, selected_type, None, lang),
            current_scope_label=_esc(self._t(lang, "current_scope")),
            session_link=self._memory_link(selected_id, selected_status, selected_type, normalized_query, lang),
            status_link=self._memory_link(selected_id, selected_status, selected_type, normalized_query, lang),
            type_link=self._memory_link(selected_id, selected_status, selected_type, normalized_query, lang),
            search_link=self._memory_link(selected_id, selected_status, selected_type, normalized_query, lang),
            scope_session=_esc(selected_id or self._t(lang, "all_sessions")),
            scope_status=_esc(self._display_status(lang, selected_status) if selected_status else self._t(lang, "all_statuses")),
            scope_type=_esc(self._display_memory_type(lang, selected_type) if selected_type else self._t(lang, "all_types")),
            scope_query=_esc(normalized_query or self._t(lang, "no_search")),
            scope_session_label=_esc(self._t(lang, "scope_session")),
            scope_status_label=_esc(self._t(lang, "scope_status")),
            scope_type_label=_esc(self._t(lang, "scope_type")),
            scope_search_label=_esc(self._t(lang, "scope_search")),
            memory_entries_label=_esc(self._t(lang, "memory_entries")),
            memory_count_label=_esc(self._t(lang, "shown_count", count=len(candidates))),
            memory_count=len(candidates),
            memory_items=self._render_memory_items(candidates, lang),
        )

    def _resolve_session(self, session_id: Optional[str], sessions: List[Any]):
        if session_id:
            for session in sessions:
                if session.session_id == session_id:
                    return session
        return sessions[0] if sessions else None

    def _render_session_cards(self, sessions: List[Any], selected_id: Optional[str], lang: str) -> str:
        if not sessions:
            return "<div class='list-item'><strong>{}</strong><div class='muted'>{}</div></div>".format(
                _esc(self._t(lang, "no_sessions_yet")),
                _esc(self._t(lang, "seed_control_plane")),
            )
        cards = []
        for session in sessions:
            classes = "session-card active" if session.session_id == selected_id else "session-card"
            cards.append(
                "<a class='{classes}' href='{href}'>"
                "<strong>{name}</strong><br><small>{sid}</small>"
                "<div class='muted'>{goal}</div>"
                "<div class='badge'>{mode}</div>"
                "</a>".format(
                    classes=classes,
                    href=self._lang_link("/mission-control", lang, session_id=session.session_id),
                    sid=quote(session.session_id),
                    name=_esc(session.name),
                    goal=_esc(session.goal),
                    mode=_esc(session.mode),
                )
            )
        return "".join(cards)

    def _render_memory_session_cards(
        self,
        sessions: List[Any],
        selected_id: Optional[str],
        status: Optional[str],
        memory_type: Optional[str],
        query: Optional[str],
        lang: str,
    ) -> str:
        if not sessions:
            return "<div class='memory-card'><strong>{}</strong><div class='muted'>{}</div></div>".format(
                _esc(self._t(lang, "no_sessions_yet")),
                _esc(self._t(lang, "memory_after_session")),
            )
        cards = []
        cards.append(
            "<a class='{classes}' href='{href}'>"
            "<strong>{title}</strong><div class='muted'>{desc}</div></a>".format(
                classes="session-card active" if selected_id is None else "session-card",
                href=self._memory_link(None, status, memory_type, query, lang),
                title=_esc(self._t(lang, "all_sessions_title")),
                desc=_esc(self._t(lang, "all_sessions_desc")),
            )
        )
        for session in sessions:
            classes = "session-card active" if session.session_id == selected_id else "session-card"
            cards.append(
                "<a class='{classes}' href='{href}'>"
                "<strong>{name}</strong><br><small>{sid}</small>"
                "<div class='muted'>{goal}</div>"
                "</a>".format(
                    classes=classes,
                    sid=quote(session.session_id),
                    name=_esc(session.name),
                    goal=_esc(session.goal),
                    href=self._memory_link(session.session_id, status, memory_type, query, lang),
                )
            )
        return "".join(cards)

    def _render_memory_filter_links(
        self,
        selected_id: Optional[str],
        status: Optional[str],
        memory_type: Optional[str],
        query: Optional[str],
        counts: Dict[str, int],
        lang: str,
    ) -> str:
        statuses = [("all", None), ("active", "active"), ("pending", "pending"), ("rejected", "rejected"), ("merged", "merged")]
        links = []
        for label, value in statuses:
            count = sum(counts.values()) if value is None else counts.get(value, 0)
            classes = "filter-link active" if (status == value or (status is None and value is None)) else "filter-link"
            links.append(
                "<a class='{classes}' href='{href}'><strong>{label}</strong><div class='muted'>{count}</div></a>".format(
                    classes=classes,
                    href=self._memory_link(selected_id, value, memory_type, query, lang),
                    label=_esc(self._display_status(lang, value)),
                    count=_esc(self._t(lang, "entries_count", count=count)),
                )
            )
        return "".join(links)

    def _render_memory_type_links(
        self,
        selected_id: Optional[str],
        status: Optional[str],
        selected_type: Optional[str],
        query: Optional[str],
        counts: Dict[str, int],
        lang: str,
    ) -> str:
        links = []
        links.append(
            "<a class='{classes}' href='{href}'><strong>{label}</strong><div class='muted'>{count}</div></a>".format(
                classes="filter-link active" if selected_type is None else "filter-link",
                href=self._memory_link(selected_id, status, None, query, lang),
                label=_esc(self._t(lang, "all")),
                count=_esc(self._t(lang, "entries_count", count=sum(counts.values()))),
            )
        )
        for memory_type in sorted(counts):
            classes = "filter-link active" if memory_type == selected_type else "filter-link"
            links.append(
                "<a class='{classes}' href='{href}'><strong>{label}</strong><div class='muted'>{count}</div></a>".format(
                    classes=classes,
                    href=self._memory_link(selected_id, status, memory_type, query, lang),
                    label=_esc(self._display_memory_type(lang, memory_type)),
                    count=_esc(self._t(lang, "entries_count", count=counts[memory_type])),
                )
            )
        return "".join(links)

    def _render_session_detail(self, session, commands: List[Any], events: List[Any], lang: str) -> str:
        if session is None:
            return "<p class='lead'>{}</p>".format(_esc(self._t(lang, "select_session_lead")))
        return """
        <div class="kvs">
          <div><small>{session_id_label}</small><strong>{sid}</strong></div>
          <div><small>{status_label}</small><strong>{status}</strong></div>
          <div><small>{mode_label}</small><strong>{mode}</strong></div>
          <div><small>{created_by_label}</small><strong>{created_by}</strong></div>
        </div>
        <p class="lead">{goal}</p>
        <div class="three-up">
          <div class="list-item"><small>{commands_label}</small><strong>{command_count}</strong><pre>{command_preview}</pre></div>
          <div class="list-item"><small>{events_label}</small><strong>{event_count}</strong><pre>{event_preview}</pre></div>
          <div class="list-item"><small>{metadata_label}</small><strong>{compact_label}</strong><pre>{metadata}</pre></div>
        </div>
        """.format(
            session_id_label=_esc(self._t(lang, "session_id")),
            status_label=_esc(self._t(lang, "status")),
            mode_label=_esc(self._t(lang, "mode")),
            created_by_label=_esc(self._t(lang, "created_by")),
            sid=_esc(session.session_id),
            status=_esc(self._display_status(lang, session.status)),
            mode=_esc(session.mode),
            created_by=_esc(session.created_by),
            goal=_esc(session.goal),
            commands_label=_esc(self._t(lang, "commands")),
            command_count=len(commands),
            events_label=_esc(self._t(lang, "events")),
            event_count=len(events),
            metadata_label=_esc(self._t(lang, "metadata")),
            compact_label=_esc(self._t(lang, "compact")),
            command_preview=_json_preview([command.command_type for command in commands[:5]]),
            event_preview=_json_preview([event.event_type for event in events[:5]]),
            metadata=_json_preview(session.metadata),
        )

    def _render_command_form(self, selected_id: Optional[str], lang: str) -> str:
        options = "".join(
            "<option value='{name}'>{name}</option>".format(name=_esc(template.name))
            for template in self.collaboration_modes.list()
        )
        return """
        <form method="post" action="/mission-control/commands">
          <input type="hidden" name="lang" value="{lang}">
          <div class="two-up">
            <label>{session_id_label}<input name="session_id" value="{session_id}" required></label>
            <label>{created_by_label}<input name="created_by" value="mission-control" required></label>
          </div>
          <div class="three-up">
            <label>{mode_label}<select name="mode">{options}</select></label>
            <label>{target_runtime_label}<input name="target_runtime" value="codex"></label>
            <label>{target_agent_label}<input name="target_agent" placeholder="{optional_label}"></label>
          </div>
          <div class="three-up">
            <label>{command_type_label}<input name="command_type" value="review_patch" required></label>
            <label>{permission_level_label}
              <select name="permission_level">
                <option value="L1">L1</option>
                <option value="L2">L2</option>
                <option value="L3">L3</option>
              </select>
            </label>
            <label>{priority_label}<input name="priority" type="number" value="100" min="1"></label>
          </div>
          <label>{idempotency_label}<input name="idempotency_key" placeholder="{idempotency_placeholder}"></label>
          <label>{payload_label}<textarea name="payload">{{"summary":"Review current task state","paths":["app.py"]}}</textarea></label>
          <button type="submit">{publish_label}</button>
        </form>
        """.format(
            lang=_esc(lang),
            session_id_label=_esc(self._t(lang, "session_id")),
            created_by_label=_esc(self._t(lang, "created_by")),
            mode_label=_esc(self._t(lang, "mode")),
            target_runtime_label=_esc(self._t(lang, "target_runtime")),
            target_agent_label=_esc(self._t(lang, "target_agent")),
            optional_label=_esc(self._t(lang, "optional")),
            command_type_label=_esc(self._t(lang, "command_type")),
            permission_level_label=_esc(self._t(lang, "permission_level")),
            priority_label=_esc(self._t(lang, "priority")),
            idempotency_label=_esc(self._t(lang, "idempotency_key")),
            idempotency_placeholder=_esc(self._t(lang, "idempotency_placeholder")),
            payload_label=_esc(self._t(lang, "structured_payload_json")),
            publish_label=_esc(self._t(lang, "publish_structured_command")),
            session_id=_esc(selected_id or ""),
            options=options,
        )

    def _render_mode_cards(self, selected_id: Optional[str], lang: str) -> str:
        cards = []
        for template in self.collaboration_modes.list():
            defaults = template.command_defaults
            payload = json.dumps(
                {
                    "summary": template.summary,
                    "workflow": template.workflow,
                    "expected_outputs": template.output_expectations,
                },
                ensure_ascii=True,
            )
            cards.append(
                """
                <article class="list-item">
                  <strong>{name}</strong> <span class="badge">{participants}</span>
                  <div class="muted">{summary}</div>
                  <pre>{workflow}</pre>
                  <form method="post" action="/mission-control/commands">
                    <input type="hidden" name="lang" value="{lang}">
                    <input type="hidden" name="session_id" value="{session_id}">
                    <input type="hidden" name="created_by" value="mission-control">
                    <input type="hidden" name="mode" value="{name}">
                    <input type="hidden" name="target_runtime" value="codex">
                    <input type="hidden" name="command_type" value="{command_type}">
                    <input type="hidden" name="permission_level" value="{permission_level}">
                    <input type="hidden" name="priority" value="{priority}">
                    <input type="hidden" name="payload" value='{payload}'>
                    <button type="submit">{quick_publish}</button>
                  </form>
                </article>
                """.format(
                    lang=_esc(lang),
                    name=_esc(template.name),
                    participants=_esc(", ".join(template.participants)),
                    summary=_esc(template.description),
                    workflow=_json_preview(template.workflow),
                    session_id=_esc(selected_id or ""),
                    command_type=_esc(defaults["command_type"]),
                    permission_level=_esc(defaults["permission_level"]),
                    priority=_esc(defaults["priority"]),
                    payload=_esc(payload),
                    quick_publish=_esc(self._t(lang, "quick_publish", name=template.name)),
                )
            )
        return "".join(cards)

    def _render_agent_states(self, agent_states: List[Any], lang: str) -> str:
        if not agent_states:
            return "<div class='list-item'><strong>{}</strong><div class='muted'>{}</div></div>".format(
                _esc(self._t(lang, "no_heartbeats")),
                _esc(self._t(lang, "heartbeats_desc")),
            )
        return "".join(
            "<article class='list-item'><strong>{agent}</strong> <span class='badge'>{runtime}</span>"
            "<div class='muted'>{status} · {heartbeat_label}</div>"
            "<pre>{metadata}</pre></article>".format(
                agent=_esc(state.agent_id),
                runtime=_esc(state.runtime),
                status=_esc(state.status),
                heartbeat_label=_esc(self._t(lang, "last_heartbeat", value=state.last_heartbeat)),
                metadata=_json_preview({"capabilities": state.capabilities, "metadata": state.metadata}),
            )
            for state in agent_states
        )

    def _render_candidates(self, candidates: List[Any], lang: str) -> str:
        if not candidates:
            return "<div class='list-item'><strong>{}</strong><div class='muted'>{}</div></div>".format(
                _esc(self._t(lang, "no_candidates")),
                _esc(self._t(lang, "candidates_desc")),
            )
        return "".join(
            "<article class='list-item'><strong>{title}</strong> <span class='badge'>{status}</span>"
            "<div class='muted'>{memory_type} · {recommended}</div>"
            "<pre>{summary}</pre></article>".format(
                title=_esc(candidate.title),
                status=_esc(self._display_status(lang, candidate.status)),
                memory_type=_esc(self._display_memory_type(lang, candidate.type)),
                recommended=_esc(candidate.recommended_action or self._t(lang, "review")),
                summary=_esc(candidate.summary or candidate.content[:180]),
            )
            for candidate in candidates
        )

    def _render_memory_items(self, candidates: List[Any], lang: str) -> str:
        if not candidates:
            return "<div class='memory-card'><strong>{}</strong><div class='muted'>{}</div></div>".format(
                _esc(self._t(lang, "no_memory_entries")),
                _esc(self._t(lang, "try_another_filter")),
            )
        items = []
        for candidate in candidates:
            badges = [
                "<span class='badge'>{}</span>".format(_esc(self._display_status(lang, candidate.status))),
                "<span class='badge'>{}</span>".format(_esc(self._display_memory_type(lang, candidate.type))),
            ]
            if candidate.conflicts_with:
                badges.append("<span class='badge warn'>{}</span>".format(_esc(self._t(lang, "conflict"))))
            if candidate.rejected:
                badges.append("<span class='badge warn'>{}</span>".format(_esc(self._t(lang, "rejected"))))
            items.append(
                """
                <article class="memory-card">
                  <div class="row">
                    <strong>{title}</strong>
                    {badges}
                  </div>
                  <div class="muted">{session_label}: {session_id} · {proposed_by_label}: {proposed_by} · {runtime_label}: {runtime} · {created_label}: {created_at}</div>
                  <pre>{summary}</pre>
                  <details>
                    <summary>{full_content_label}</summary>
                    <pre>{content}</pre>
                  </details>
                  <details>
                    <summary>{structured_metadata_label}</summary>
                    <pre>{meta}</pre>
                  </details>
                </article>
                """.format(
                    title=_esc(candidate.title),
                    badges=" ".join(badges),
                    session_label=_esc(self._t(lang, "session")),
                    session_id=_esc(candidate.session_id or self._t(lang, "global")),
                    proposed_by_label=_esc(self._t(lang, "proposed_by")),
                    proposed_by=_esc(candidate.proposed_by),
                    runtime_label=_esc(self._t(lang, "runtime")),
                    runtime=_esc(candidate.runtime or self._t(lang, "unknown")),
                    created_label=_esc(self._t(lang, "created")),
                    created_at=_esc(candidate.created_at),
                    summary=_esc(candidate.summary or self._t(lang, "no_summary")),
                    full_content_label=_esc(self._t(lang, "full_content")),
                    content=_esc(candidate.content),
                    structured_metadata_label=_esc(self._t(lang, "structured_metadata")),
                    meta=_json_preview(
                        {
                            "tags": candidate.tags,
                            "rejected": candidate.rejected,
                            "similar_to": candidate.similar_to,
                            "conflicts_with": candidate.conflicts_with,
                            "recommended_action": candidate.recommended_action,
                            "resolved_at": candidate.resolved_at,
                        }
                    ),
                )
            )
        return "".join(items)

    def _filter_memory_candidates(
        self,
        candidates: List[Any],
        *,
        status: Optional[str] = None,
        memory_type: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[Any]:
        filtered = candidates
        if status is not None:
            filtered = [candidate for candidate in filtered if candidate.status == status]
        if memory_type is not None:
            filtered = [candidate for candidate in filtered if candidate.type == memory_type]
        if query:
            needle = query.lower()
            filtered = [
                candidate
                for candidate in filtered
                if needle in " ".join(
                    [
                        candidate.title,
                        candidate.summary,
                        candidate.content,
                        " ".join(str(tag) for tag in candidate.tags),
                        " ".join(str(item) for item in candidate.rejected),
                    ]
                ).lower()
            ]
        return filtered

    def _memory_types(self, candidates: List[Any]) -> List[str]:
        return sorted({candidate.type for candidate in candidates if candidate.type})

    def _memory_type_counts(self, candidates: List[Any]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for candidate in candidates:
            counts[candidate.type] = counts.get(candidate.type, 0) + 1
        return counts

    def _memory_link(
        self,
        session_id: Optional[str],
        status: Optional[str],
        memory_type: Optional[str],
        query: Optional[str],
        lang: str,
    ) -> str:
        return self._lang_link(
            "/mission-control/memories",
            lang,
            session_id=session_id,
            status=status,
            type=memory_type,
            q=query,
        )

    def _render_conflicts(self, conflicts: List[Any], selected_id: Optional[str], lang: str) -> str:
        if not conflicts:
            return "<div class='list-item'><strong>{}</strong><div class='muted'>{}</div></div>".format(
                _esc(self._t(lang, "no_active_conflicts")),
                _esc(self._t(lang, "conflict_review_empty")),
            )
        return "".join(
            "<article class='list-item'><strong>{title}</strong> <span class='badge warn'>{count}</span>"
            "<div class='muted'>{recommended}</div>"
            "<pre>{conflicts}</pre>"
            "<form method='post' action='/mission-control/memory-candidates/resolve'>"
            "<input type='hidden' name='lang' value='{lang}'>"
            "<input type='hidden' name='session_id' value='{session_id}'>"
            "<input type='hidden' name='candidate_id' value='{candidate_id}'>"
            "<input type='hidden' name='created_by' value='mission-control'>"
            "<label>{status_label}<select name='status'>{status_options}</select></label>"
            "<label>{action_label}<input name='recommended_action' value='{recommended_action}'></label>"
            "<button type='submit'>{resolve_label}</button>"
            "</form></article>".format(
                title=_esc(candidate.title),
                count=_esc(self._t(lang, "conflict_count_label", count=len(candidate.conflicts_with))),
                recommended=_esc(self._t(lang, "recommended_action", value=candidate.recommended_action or self._t(lang, "review"))),
                conflicts=_json_preview(candidate.conflicts_with),
                lang=_esc(lang),
                session_id=_esc(selected_id or candidate.session_id or ""),
                candidate_id=_esc(candidate.candidate_id),
                status_label=_esc(self._t(lang, "resolution_status")),
                action_label=_esc(self._t(lang, "resolution_action")),
                resolve_label=_esc(self._t(lang, "resolve_conflict")),
                recommended_action=_esc(candidate.recommended_action or ""),
                status_options="".join(
                    "<option value='{value}'{selected}>{label}</option>".format(
                        value=_esc(value),
                        selected=" selected" if value == "active" else "",
                        label=_esc(self._display_status(lang, value)),
                    )
                    for value in ("active", "corrected", "superseded", "rejected", "archived")
                ),
            )
            for candidate in conflicts
        )

    def _render_timeline(self, events: List[Any], lang: str) -> str:
        if not events:
            return "<div class='timeline-item'><strong>{}</strong><div class='muted'>{}</div></div>".format(
                _esc(self._t(lang, "no_timeline")),
                _esc(self._t(lang, "timeline_desc")),
            )
        items = []
        for event in reversed(events):
            event_content = dict(event.content)
            if "participants" in event_content:
                event_content["participants"] = event_content["participants"]
            items.append(
                "<article class='timeline-item'><strong>{event_type}</strong>"
                "<div class='muted'>{agent} · {seq_label}</div>"
                "<pre>{content}</pre></article>".format(
                    event_type=_esc(event.event_type),
                    agent=_esc(event.agent_id),
                    seq_label=_esc(self._t(lang, "seq", value=event.seq)),
                    content=_json_preview(event_content),
                )
            )
        return "".join(items)

    def _render_audit_logs(self, audit_logs: List[Any], lang: str) -> str:
        if not audit_logs:
            return "<div class='list-item'><strong>{}</strong></div>".format(_esc(self._t(lang, "no_audit_entries")))
        return "".join(
            "<article class='list-item'><strong>{action}</strong> <span class='badge'>{actor}</span>"
            "<div class='muted'>{resource_type} · {resource_id}</div>"
            "<pre>{metadata}</pre></article>".format(
                action=_esc(log.action),
                actor=_esc(log.actor),
                resource_type=_esc(log.resource_type),
                resource_id=_esc(log.resource_id or self._t(lang, "not_available")),
                metadata=_json_preview(log.metadata),
            )
            for log in audit_logs
        )

    def _render_digests(self, digests: List[Any], lang: str) -> str:
        if not digests:
            return "<div class='list-item'><strong>{}</strong><div class='muted'>{}</div></div>".format(
                _esc(self._t(lang, "no_digests")),
                _esc(self._t(lang, "digests_desc")),
            )
        return "".join(
            "<article class='list-item'><strong>{summary}</strong>"
            "<div class='muted'>{seq_label}</div>"
            "<pre>{details}</pre></article>".format(
                summary=_esc(digest.summary),
                seq_label=_esc(self._t(lang, "seq", value="{}-{}".format(digest.from_seq, digest.to_seq))),
                details=_json_preview(
                    {
                        "decisions": digest.decisions,
                        "open_questions": digest.open_questions,
                        "rejected_candidates": digest.rejected_candidates,
                    }
                ),
            )
            for digest in digests
        )

    def _render_commit_warning(self, session, lang: str) -> str:
        if session is None:
            return ""
        if session.metadata.get("last_commit_at"):
            return "<div class='list-item'><strong>{title}</strong><div class='muted'>{value}</div></div>".format(
                title=_esc(self._t(lang, "committed_session")),
                value=_esc(self._t(lang, "last_commit_at", value=session.metadata.get("last_commit_at"))),
            )
        return "<div class='list-item'><strong class='warn-text'>{}</strong><div class='muted'>{}</div></div>".format(
            _esc(self._t(lang, "uncommitted_session")),
            _esc(self._t(lang, "uncommitted_desc")),
        )

    def _build_token_snapshot(self, session, commands: List[Any], events: List[Any], candidates: List[Any], digests: List[Any]) -> Dict[str, int]:
        memory_tokens = sum(len((candidate.summary or candidate.content).split()) for candidate in candidates[:5])
        digest_tokens = sum(len(digest.summary.split()) for digest in digests[:5])
        command_tokens = sum(len(json.dumps(command.payload).split()) for command in commands[:5])
        candidate_tokens = sum(len((candidate.summary or "").split()) for candidate in candidates[:8])
        total = memory_tokens + digest_tokens + command_tokens + candidate_tokens
        return {
            "memory_tokens": memory_tokens,
            "digest_tokens": digest_tokens,
            "command_tokens": command_tokens,
            "candidate_tokens": candidate_tokens,
            "total": total,
            "percent": min(100, int((total / 1200) * 100)) if total else 4,
        }

    def _memory_status_counts(self, candidates: List[Any]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for candidate in candidates:
            counts[candidate.status] = counts.get(candidate.status, 0) + 1
        return counts

    def _flash_html(self, message: Optional[str], *, ok: bool) -> str:
        if not message:
            return ""
        return "<div class='flash {klass}'>{message}</div>".format(
            klass="ok" if ok else "error",
            message=_esc(message),
        )

    def _nullable(self, value: Any) -> Optional[str]:
        cleaned = str(value).strip() if value is not None else ""
        return cleaned or None
