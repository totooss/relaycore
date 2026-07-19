# Claude Hooks For EchoMemory

## Purpose

This document mirrors the Codex adapter contract for Claude-oriented runtimes. It is intentionally lightweight and should stay aligned with [`AGENTS.md`](../AGENTS.md).

## Runtime Contract

Before work:

1. Call `memory_begin_task` if EchoMemory MCP is available.
2. Call `memory_context` with `max_tokens <= 1200`.
3. Read active decisions, rules, lessons, and relevant rejected options.

During work:

1. Append only important events with `agent_event_append`.
2. Poll commands with `command_poll` when the runtime is participating in a managed session.
3. Keep responses compact by default.
4. Do not drift from the confirmed phase or task boundary.

Before stop:

1. Call `memory_commit_task` if available.
2. Persist durable decisions and rejected options.
3. If EchoMemory MCP is unavailable, write durable design decisions into `docs/decisions/`.

## Claude Setup Pattern

Use the same EchoMemory MCP endpoint and tool semantics as Codex. The Claude-side adapter should:

- treat EchoMemory as the only durable memory backend
- use compact memory context by default
- preserve rejected options instead of dropping them
- keep command and event behavior symmetric with Codex

## Example Hook Intents

These are behavioral examples, not a second business logic path:

- on session start, join or resume the EchoMemory task session
- before stop, commit a compact task summary and any durable decisions
- while running in a managed session, poll for structured commands instead of inventing ad hoc control flows

## Fallback When MCP Is Unavailable

If the EchoMemory MCP server is not yet implemented or not reachable:

1. continue local implementation work without blocking
2. explicitly report that long-term memory could not be persisted through MCP
3. write durable design decisions into `docs/decisions/phase-X-<short-title>.md`

## Constraints

- Do not introduce Obsidian integration.
- Do not create Claude-only business behavior that diverges from Codex.
- Do not turn any HTML surface into a shell executor.
