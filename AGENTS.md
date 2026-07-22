# RelayCore Project Instructions

This project uses RelayCore as the only durable project memory layer.

## Memory Policy

- Treat native model memory as optional, unstable, and non-authoritative.
- Do not rely on ChatGPT, Codex, Claude, or any other runtime's built-in memory for project continuity.
- Do not store durable project decisions only in native agent memory.
- Durable memory for this project means any reusable decision, rule, lesson, rejected option, artifact reference, or workflow state that should survive the current session.
- If durable memory is not written to RelayCore, treat it as not stored.

## Required Workflow

1. At task start, call `memory_begin_task`.
2. Before doing substantial work, call `memory_context`.
3. When a durable fact, decision, rule, or lesson appears, write it with `memory_add` or `memory_propose`.
4. When a decision supersedes or rejects another option, preserve the rejected path and reason through RelayCore memory flows.
5. Before ending the task, call `memory_commit_task`.

## Required RelayCore Endpoints

- MCP: `http://127.0.0.1:9090/mcp`
- Mission Control: `http://127.0.0.1:8080/mission-control`
- Memory Viewer: `http://127.0.0.1:8080/mission-control/memories`

## Task Rules

- Use RelayCore as the source of truth for cross-session and cross-runtime memory.
- Prefer compact retrieval through `memory_context` rather than replaying full chat history.
- Record only important events with `agent_event_append`.
- Use `trace_refs` and `artifact_refs` whenever durable memory should point back to evidence.
- Promote memory to canonical form only when evidence exists.
- Keep project-scoped memory inside RelayCore, not repo-local scratch notes, unless RelayCore is unavailable.
- Treat Mission Control command publishing as a manual operator override path, not the default collaboration path.
- Default to agent-driven command publication during normal runtime collaboration.
- Use the web UI command form only for fallback dispatch, debugging, or session seeding.

## Fallback Rule

- If RelayCore MCP is unavailable, say so explicitly.
- In fallback mode, keep temporary notes local only until RelayCore is restored.
- After RelayCore is available again, backfill durable decisions into RelayCore before considering the task complete.

## Non-Goals

- Do not treat the Mission Control UI as a shell.
- Do not use RelayCore as a personal PKM or general note dump.
- Do not bypass RelayCore for convenience when the information should persist for the project.
