# AGENTS.md

## RelayCore Runtime Rules

RelayCore is the only long-term memory backend for this project.

Before work:
1. Call `memory_begin_task` if RelayCore MCP is available.
2. Call `memory_context` with `max_tokens <= 1200`.
3. Read active decisions, rules, lessons, and relevant rejected options.

During work:
1. Append only important events with `agent_event_append`.
2. Poll commands with `command_poll` when in a managed session.
3. Keep runtime responses compact by default.
4. Do not store durable project decisions only in native agent memory.
5. Do not drift from the current confirmed phase or task scope while executing.
6. If new ideas or future work appear, record them for later instead of implementing them immediately.

Before stop:
1. Call `memory_commit_task` if available.
2. Save durable decisions and rejected options.
3. If RelayCore is unavailable, explicitly report it and store durable decisions under `docs/decisions/`.

Implementation rules:
- Do not read the full build blueprint unless explicitly asked.
- For implementation, read only the current `docs/phases/phase-*.md` file and relevant source files.
- Do not implement multiple phases at once.
- Do not expand scope during execution without explicit user confirmation.
- Do not turn the HTML UI into a direct shell execution console.
- Do not consider Obsidian integration, sync, export, or roadmap items.
- Do not default to full memory content or full event timelines.
- Keep dependencies lightweight and avoid network-required services unless a phase explicitly calls for them.
- Keep Codex and Claude adapter behavior aligned unless a runtime-specific limitation forces a documented exception.
