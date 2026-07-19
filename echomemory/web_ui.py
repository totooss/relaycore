"""HTML Mission Control views for EchoMemory."""

from html import escape
import json
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from .command_bus import CommandBusService
from .event_log import EventLogService
from .runtime_adapters import CollaborationModeRegistry
from .storage import EchoMemoryStorage
from .token_budget import redact_structure


def _esc(value: Any) -> str:
    return escape("" if value is None else str(value))


def _json_preview(value: Any) -> str:
    return _esc(json.dumps(redact_structure(value), ensure_ascii=True, sort_keys=True))


class MissionControlUI:
    """Render a lightweight operator-facing HTML control plane."""

    def __init__(
        self,
        storage: EchoMemoryStorage,
        command_bus: CommandBusService,
        event_log: EventLogService,
    ) -> None:
        self.storage = storage
        self.command_bus = command_bus
        self.event_log = event_log
        self.collaboration_modes = CollaborationModeRegistry()

    def render_dashboard(
        self,
        *,
        session_id: Optional[str] = None,
        flash: Optional[str] = None,
        error: Optional[str] = None,
    ) -> str:
        sessions = self.storage.list_sessions()
        selected_session = self._resolve_session(session_id, sessions)
        selected_id = selected_session.session_id if selected_session else None

        commands = self.storage.list_commands(session_id=selected_id, limit=12) if selected_id else []
        events = self.event_log.list_events(selected_id, limit=18) if selected_id else []
        candidates = self.storage.list_memory_candidates(session_id=selected_id, limit=12) if selected_id else []
        digests = self.storage.list_session_digests(selected_id, limit=6) if selected_id else []
        agent_states = self.storage.list_agent_states(session_id=selected_id, limit=12) if selected_id else []
        audit_logs = self.storage.list_audit_logs(limit=12)
        conflicts = [candidate for candidate in candidates if candidate.conflicts_with]
        token_snapshot = self._build_token_snapshot(selected_session, commands, events, candidates, digests)
        commit_warning = self._render_commit_warning(selected_session)

        return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EchoMemory Mission Control</title>
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
    <section class="hero">
      <span class="eyebrow">EchoMemory Mission Control</span>
      <h1>Shared runtime memory, not a shell.</h1>
      <p>Inspect sessions, structured commands, live events, candidate memories, and audit trails from one page. This console only publishes permission-scoped commands and session metadata. It never executes arbitrary shell instructions.</p>
      <div class="metrics">
        <div class="metric"><small>Sessions</small><strong>{session_count}</strong></div>
        <div class="metric"><small>Agent States</small><strong>{agent_count}</strong></div>
        <div class="metric"><small>Pending Commands</small><strong>{pending_count}</strong></div>
        <div class="metric"><small>Recent Events</small><strong>{event_count}</strong></div>
      </div>
      {flash_html}
      {error_html}
    </section>
    <div class="grid">
      <aside class="sidebar">
        <div class="section-title"><h2>Sessions</h2><span class="badge">{session_count} tracked</span></div>
        <div class="session-list">
          {session_cards}
        </div>
      </aside>
      <main class="content">
        <section class="panel">
          <div class="section-title">
            <div>
              <h2>Session Detail</h2>
              <p class="lead">Current focus, command traffic, and live timeline for the selected task.</p>
            </div>
            <span class="badge">{selected_label}</span>
          </div>
          {commit_warning}
          {session_detail}
        </section>
        <section class="panel">
          <div class="section-title">
            <div>
              <h2>Command Publisher</h2>
              <p class="lead">Publish a structured command with explicit routing and permission scope.</p>
            </div>
            <span class="badge warn">No Shell Execution</span>
          </div>
          {command_form}
        </section>
        <section class="panel">
          <div class="section-title">
            <div>
              <h2>Collaboration Modes</h2>
              <p class="lead">Structured templates keep multi-agent coordination predictable and auditable.</p>
            </div>
            <span class="badge">{mode_count} templates</span>
          </div>
          <div class="list">{mode_cards}</div>
        </section>
        <div class="two-up">
          <section class="panel">
            <div class="section-title"><h2>Agent States</h2><span class="badge">{agent_state_count} live</span></div>
            <div class="list">{agent_state_items}</div>
          </section>
          <section class="panel">
            <div class="section-title"><h2>Token Budget Monitor</h2><span class="badge">{token_estimate} est</span></div>
            <p class="lead">A compact estimate to keep retrieval and operator summaries small enough for runtime use.</p>
            <div class="kvs">
              <div><small>Memory Context</small><strong>{memory_tokens}</strong></div>
              <div><small>Event Digest</small><strong>{digest_tokens}</strong></div>
              <div><small>Command Payloads</small><strong>{command_tokens}</strong></div>
              <div><small>Candidate Summaries</small><strong>{candidate_tokens}</strong></div>
            </div>
            <div class="token-bar"><span></span></div>
            <p class="muted">Approximation only. Full content stays hidden unless an explicit expansion handle is requested.</p>
          </section>
        </div>
        <div class="two-up">
          <section class="panel">
            <div class="section-title"><h2>Memory Candidate Queue</h2><span class="badge">{candidate_count} queued</span></div>
            <div class="list">{candidate_items}</div>
          </section>
          <section class="panel">
            <div class="section-title"><h2>Conflict Resolution Panel</h2><span class="badge warn">{conflict_count} conflicts</span></div>
            <div class="list">{conflict_items}</div>
          </section>
        </div>
        <div class="two-up">
          <section class="panel">
            <div class="section-title"><h2>Live Timeline</h2><span class="badge">SSE Ready</span></div>
            <div id="timeline" class="timeline">{timeline_items}</div>
          </section>
          <section class="panel">
            <div class="section-title"><h2>Audit Log Viewer</h2><span class="badge">{audit_count} recent</span></div>
            <div class="list">{audit_items}</div>
          </section>
        </div>
        <section class="panel">
          <div class="section-title"><h2>Recent Digests</h2><span class="badge">{digest_count} compact</span></div>
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
            token_percent=min(100, token_snapshot["percent"]),
            session_count=len(sessions),
            agent_count=len(agent_states),
            pending_count=len([command for command in commands if command.status == "pending"]),
            event_count=len(events),
            flash_html=self._flash_html(flash, ok=True),
            error_html=self._flash_html(error, ok=False),
            session_cards=self._render_session_cards(sessions, selected_id),
            selected_label=_esc(selected_id or "No session selected"),
            commit_warning=commit_warning,
            session_detail=self._render_session_detail(selected_session, commands, events),
            command_form=self._render_command_form(selected_id),
            mode_count=len(self.collaboration_modes.list()),
            mode_cards=self._render_mode_cards(selected_id),
            agent_state_count=len(agent_states),
            agent_state_items=self._render_agent_states(agent_states),
            token_estimate=_esc(token_snapshot["total"]),
            memory_tokens=_esc(token_snapshot["memory_tokens"]),
            digest_tokens=_esc(token_snapshot["digest_tokens"]),
            command_tokens=_esc(token_snapshot["command_tokens"]),
            candidate_tokens=_esc(token_snapshot["candidate_tokens"]),
            candidate_count=len(candidates),
            candidate_items=self._render_candidates(candidates),
            conflict_count=len(conflicts),
            conflict_items=self._render_conflicts(conflicts),
            timeline_items=self._render_timeline(events),
            audit_count=len(audit_logs),
            audit_items=self._render_audit_logs(audit_logs),
            digest_count=len(digests),
            digest_items=self._render_digests(digests),
            selected_session_json=json.dumps(selected_id),
        )

    def handle_command_form(self, form: Dict[str, Any]) -> str:
        payload_text = form.get("payload", "{}")
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise ValueError("payload must be valid JSON: {}".format(exc.msg))
        if not isinstance(payload, dict):
            raise ValueError("payload must decode to a JSON object")

        session_id = str(form.get("session_id", "")).strip()
        if not session_id:
            raise ValueError("session_id is required")

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
        return "Published command {} for session {}.".format(command.command_id, session_id)

    def _resolve_session(self, session_id: Optional[str], sessions: List[Any]):
        if session_id:
            for session in sessions:
                if session.session_id == session_id:
                    return session
        return sessions[0] if sessions else None

    def _render_session_cards(self, sessions: List[Any], selected_id: Optional[str]) -> str:
        if not sessions:
            return "<div class='list-item'><strong>No sessions yet.</strong><div class='muted'>Use MCP tools or Phase 8 forms to seed the control plane.</div></div>"
        cards = []
        for session in sessions:
            classes = "session-card active" if session.session_id == selected_id else "session-card"
            cards.append(
                "<a class='{classes}' href='/mission-control?session_id={sid}'>"
                "<strong>{name}</strong><br><small>{sid}</small>"
                "<div class='muted'>{goal}</div>"
                "<div class='badge'>{mode}</div>"
                "</a>".format(
                    classes=classes,
                    sid=quote(session.session_id),
                    name=_esc(session.name),
                    goal=_esc(session.goal),
                    mode=_esc(session.mode),
                )
            )
        return "".join(cards)

    def _render_session_detail(self, session, commands: List[Any], events: List[Any]) -> str:
        if session is None:
            return "<p class='lead'>Select a session to inspect commands, events, candidates, and digests.</p>"
        return """
        <div class="kvs">
          <div><small>Session ID</small><strong>{sid}</strong></div>
          <div><small>Status</small><strong>{status}</strong></div>
          <div><small>Mode</small><strong>{mode}</strong></div>
          <div><small>Created By</small><strong>{created_by}</strong></div>
        </div>
        <p class="lead">{goal}</p>
        <div class="three-up">
          <div class="list-item"><small>Commands</small><strong>{command_count}</strong><pre>{command_preview}</pre></div>
          <div class="list-item"><small>Events</small><strong>{event_count}</strong><pre>{event_preview}</pre></div>
          <div class="list-item"><small>Metadata</small><strong>Compact</strong><pre>{metadata}</pre></div>
        </div>
        """.format(
            sid=_esc(session.session_id),
            status=_esc(session.status),
            mode=_esc(session.mode),
            created_by=_esc(session.created_by),
            goal=_esc(session.goal),
            command_count=len(commands),
            event_count=len(events),
            command_preview=_json_preview([command.command_type for command in commands[:5]]),
            event_preview=_json_preview([event.event_type for event in events[:5]]),
            metadata=_json_preview(session.metadata),
        )

    def _render_command_form(self, selected_id: Optional[str]) -> str:
        options = "".join(
            "<option value='{name}'>{name}</option>".format(name=_esc(template.name))
            for template in self.collaboration_modes.list()
        )
        return """
        <form method="post" action="/mission-control/commands">
          <div class="two-up">
            <label>Session ID<input name="session_id" value="{session_id}" required></label>
            <label>Created By<input name="created_by" value="mission-control" required></label>
          </div>
          <div class="three-up">
            <label>Mode<select name="mode">{options}</select></label>
            <label>Target Runtime<input name="target_runtime" value="codex"></label>
            <label>Target Agent<input name="target_agent" placeholder="optional"></label>
          </div>
          <div class="three-up">
            <label>Command Type<input name="command_type" value="review_patch" required></label>
            <label>Permission Level
              <select name="permission_level">
                <option value="L1">L1</option>
                <option value="L2">L2</option>
                <option value="L3">L3</option>
              </select>
            </label>
            <label>Priority<input name="priority" type="number" value="100" min="1"></label>
          </div>
          <label>Idempotency Key<input name="idempotency_key" placeholder="optional-dedup-key"></label>
          <label>Structured Payload JSON<textarea name="payload">{{"summary":"Review current task state","paths":["app.py"]}}</textarea></label>
          <button type="submit">Publish Structured Command</button>
        </form>
        """.format(session_id=_esc(selected_id or ""), options=options)

    def _render_mode_cards(self, selected_id: Optional[str]) -> str:
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
                    <input type="hidden" name="session_id" value="{session_id}">
                    <input type="hidden" name="created_by" value="mission-control">
                    <input type="hidden" name="mode" value="{name}">
                    <input type="hidden" name="target_runtime" value="codex">
                    <input type="hidden" name="command_type" value="{command_type}">
                    <input type="hidden" name="permission_level" value="{permission_level}">
                    <input type="hidden" name="priority" value="{priority}">
                    <input type="hidden" name="payload" value='{payload}'>
                    <button type="submit">Quick Publish {name}</button>
                  </form>
                </article>
                """.format(
                    name=_esc(template.name),
                    participants=_esc(", ".join(template.participants)),
                    summary=_esc(template.description),
                    workflow=_json_preview(template.workflow),
                    session_id=_esc(selected_id or ""),
                    command_type=_esc(defaults["command_type"]),
                    permission_level=_esc(defaults["permission_level"]),
                    priority=_esc(defaults["priority"]),
                    payload=_esc(payload),
                )
            )
        return "".join(cards)

    def _render_agent_states(self, agent_states: List[Any]) -> str:
        if not agent_states:
            return "<div class='list-item'><strong>No heartbeats yet.</strong><div class='muted'>Agents will appear here after `agent_heartbeat` or `memory_begin_task`.</div></div>"
        return "".join(
            "<article class='list-item'><strong>{agent}</strong> <span class='badge'>{runtime}</span>"
            "<div class='muted'>{status} · last heartbeat {heartbeat}</div>"
            "<pre>{metadata}</pre></article>".format(
                agent=_esc(state.agent_id),
                runtime=_esc(state.runtime),
                status=_esc(state.status),
                heartbeat=_esc(state.last_heartbeat),
                metadata=_json_preview({"capabilities": state.capabilities, "metadata": state.metadata}),
            )
            for state in agent_states
        )

    def _render_candidates(self, candidates: List[Any]) -> str:
        if not candidates:
            return "<div class='list-item'><strong>No candidates queued.</strong><div class='muted'>Memory proposals and conflict reviews will appear here.</div></div>"
        return "".join(
            "<article class='list-item'><strong>{title}</strong> <span class='badge'>{status}</span>"
            "<div class='muted'>{memory_type} · {recommended}</div>"
            "<pre>{summary}</pre></article>".format(
                title=_esc(candidate.title),
                status=_esc(candidate.status),
                memory_type=_esc(candidate.type),
                recommended=_esc(candidate.recommended_action or "review"),
                summary=_esc(candidate.summary or candidate.content[:180]),
            )
            for candidate in candidates
        )

    def _render_conflicts(self, conflicts: List[Any]) -> str:
        if not conflicts:
            return "<div class='list-item'><strong>No active conflicts.</strong><div class='muted'>Conflict review is empty for the selected session.</div></div>"
        return "".join(
            "<article class='list-item'><strong>{title}</strong> <span class='badge warn'>{count} conflict(s)</span>"
            "<div class='muted'>Recommended action: {recommended}</div>"
            "<pre>{conflicts}</pre></article>".format(
                title=_esc(candidate.title),
                count=len(candidate.conflicts_with),
                recommended=_esc(candidate.recommended_action or "review"),
                conflicts=_json_preview(candidate.conflicts_with),
            )
            for candidate in conflicts
        )

    def _render_timeline(self, events: List[Any]) -> str:
        if not events:
            return "<div class='timeline-item'><strong>No timeline events yet.</strong><div class='muted'>Event API, command changes, and memory actions will stream here.</div></div>"
        items = []
        for event in reversed(events):
            event_content = dict(event.content)
            if "participants" in event_content:
                event_content["participants"] = event_content["participants"]
            items.append(
                "<article class='timeline-item'><strong>{event_type}</strong>"
                "<div class='muted'>{agent} · seq {seq}</div>"
                "<pre>{content}</pre></article>".format(
                    event_type=_esc(event.event_type),
                    agent=_esc(event.agent_id),
                    seq=event.seq,
                    content=_json_preview(event_content),
                )
            )
        return "".join(items)

    def _render_audit_logs(self, audit_logs: List[Any]) -> str:
        if not audit_logs:
            return "<div class='list-item'><strong>No audit entries yet.</strong></div>"
        return "".join(
            "<article class='list-item'><strong>{action}</strong> <span class='badge'>{actor}</span>"
            "<div class='muted'>{resource_type} · {resource_id}</div>"
            "<pre>{metadata}</pre></article>".format(
                action=_esc(log.action),
                actor=_esc(log.actor),
                resource_type=_esc(log.resource_type),
                resource_id=_esc(log.resource_id or "n/a"),
                metadata=_json_preview(log.metadata),
            )
            for log in audit_logs
        )

    def _render_digests(self, digests: List[Any]) -> str:
        if not digests:
            return "<div class='list-item'><strong>No digests yet.</strong><div class='muted'>Digests appear automatically every 10 events or via task commit.</div></div>"
        return "".join(
            "<article class='list-item'><strong>{summary}</strong>"
            "<div class='muted'>seq {from_seq}-{to_seq}</div>"
            "<pre>{details}</pre></article>".format(
                summary=_esc(digest.summary),
                from_seq=digest.from_seq,
                to_seq=digest.to_seq,
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

    def _render_commit_warning(self, session) -> str:
        if session is None:
            return ""
        if session.metadata.get("last_commit_at"):
            return "<div class='list-item'><strong>Committed session</strong><div class='muted'>Last commit at {value}.</div></div>".format(
                value=_esc(session.metadata.get("last_commit_at")),
            )
        return "<div class='list-item'><strong class='warn-text'>Uncommitted Session</strong><div class='muted'>This session has not been sealed with `memory_commit_task` yet.</div></div>"

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
