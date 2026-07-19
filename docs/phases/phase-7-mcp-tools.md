# Phase 7 MCP Tools

## Goal

Expose the core EchoMemory behavior through MCP tools so Codex, Claude, and other compatible agents can share one long-term memory and command workflow.

## Input Files

- `AGENTS.md`
- `docs/phases/phase-7-mcp-tools.md`
- `echomemory/mcp_server.py`
- `echomemory/server.py`
- `echomemory/storage.py`
- `echomemory/memory_quality.py`

## Expected Modified Files

- `echomemory/mcp_server.py`
- `echomemory/runtime_adapters.py`
- `tests/test_mcp_tools.py`

## External Reference Scope

- `AgentMemory/.claude-plugin`
- `AgentMemory/.codex-plugin`
- `AgentMemory/packages/mcp`
- OpenMemory or Mem0 tool taxonomies
- Cognee MCP patterns for remember, recall, and forget semantics
- Redis Agent Memory Server concepts for working memory versus long-term memory

Only extract tool shape and adapter ideas. Do not import external infrastructure.

## Detailed TODO

1. Add `memory_begin_task`.
2. Add `memory_context` with compact default responses.
3. Add `memory_propose` and `memory_add`.
4. Add `memory_commit_task`.
5. Add command polling and lifecycle tools.
6. Add `agent_event_append`.
7. Add `session_digest_get`.
8. Add `agent_heartbeat`.
9. Keep tool outputs small, structured, and explain why items are relevant.

## Disallowed

- Do not return full memory bodies unless explicitly requested.
- Do not add provider-specific tool forks that diverge in behavior.
- Do not depend on external vector stores or hosted services.

## Acceptance Criteria

- A single MCP server exposes the minimum shared toolset.
- Codex and Claude can use the same memory and command semantics.
- `memory_context` defaults to summaries, IDs, and relevance reasons.
- Rejected options remain preserved and visible.

## Recommended Test Commands

```bash
pytest tests/test_mcp_tools.py
pytest tests/test_memory_quality.py
```
