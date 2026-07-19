# Phase 6 Event Log And SSE

## Goal

Expose append-only event APIs and a live stream so multiple runtimes can observe the same session timeline without polling full history.

## Input Files

- `AGENTS.md`
- `docs/phases/phase-6-event-log-and-sse.md`
- `echomemory/server.py`
- `echomemory/event_log.py`
- `echomemory/storage.py`

## Expected Modified Files

- `echomemory/server.py`
- `echomemory/event_log.py`
- `echomemory/storage.py`
- `tests/test_event_log.py`

## External Reference Scope

- `mcp-memory-service` concepts for REST plus SSE event delivery

Do not adopt unrelated auth or embedding systems.

## Detailed TODO

1. Add `POST /api/events`.
2. Add `GET /api/events`.
3. Add `GET /api/events/stream` using SSE.
4. Ensure command state changes also write events.
5. Ensure memory writes and conflict actions also write events.
6. Generate periodic digests, such as every 10 events.
7. Keep default event reads compact and filterable by session.

## Disallowed

- Do not stream unrestricted private data to all clients.
- Do not return entire timelines by default when a digest or cursor view is enough.
- Do not replace append-only semantics with mutable logs.

## Acceptance Criteria

- Events can be appended and fetched by session.
- An SSE client can subscribe to live updates.
- Command and memory actions appear in the shared timeline.
- Digests are created on the defined cadence.

## Recommended Test Commands

```bash
pytest tests/test_event_log.py
pytest tests/test_command_bus.py
```
