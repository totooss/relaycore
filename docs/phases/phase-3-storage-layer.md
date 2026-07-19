# Phase 3 Storage Layer

## Goal

Build the storage abstraction over the new schema so sessions, commands, events, digests, and memory candidates can be created and queried consistently.

## Input Files

- `AGENTS.md`
- `docs/phases/phase-3-storage-layer.md`
- `relaycore/migrations.py`
- `relaycore/storage.py`

## Expected Modified Files

- `relaycore/storage.py`
- `relaycore/models.py`
- `tests/test_storage.py`

## External Reference Scope

- None required by default.
- If a local pattern is needed, only inspect lightweight SQLite repository patterns.

## Detailed TODO

1. Implement session CRUD.
2. Implement command CRUD plus status transitions.
3. Implement event append and event queries.
4. Implement digest write and read methods.
5. Implement candidate memory create, list, update, and resolve paths.
6. Implement occurrence and cluster persistence helpers.
7. Implement audit log writes and basic reads.

## Disallowed

- Do not expose HTTP or MCP endpoints yet.
- Do not add background workers unless the storage layer absolutely requires one.
- Do not make storage methods return verbose full-content responses by default.

## Acceptance Criteria

- Storage methods cover all core entities needed by later phases.
- Command status transitions are explicit and validated.
- Event writes are append-only.
- Tests cover happy paths and key invalid transitions.

## Recommended Test Commands

```bash
pytest tests/test_storage.py
pytest tests/test_migrations.py
```
