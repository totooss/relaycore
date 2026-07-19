# Phase 5 Command Bus API

## Goal

Expose REST endpoints for publishing, claiming, completing, failing, and recovering structured commands across multiple agent runtimes.

## Input Files

- `AGENTS.md`
- `docs/phases/phase-5-command-bus-api.md`
- `echomemory/storage.py`
- `echomemory/server.py`
- `echomemory/command_bus.py`

## Expected Modified Files

- `echomemory/server.py`
- `echomemory/command_bus.py`
- `tests/test_command_bus.py`

## External Reference Scope

- `mcp-memory-service` concepts for agent IDs, conversation IDs, and management APIs

Only extract API patterns that fit the current phase.

## Detailed TODO

1. Add `POST /api/commands`.
2. Add `GET /api/commands/pending`.
3. Add claim, complete, and fail endpoints.
4. Implement lease ownership and expiry recovery.
5. Enforce idempotency where needed.
6. Validate `permission_level` and target routing fields.
7. Emit audit entries for sensitive command operations.

## Disallowed

- Do not let commands execute shell actions directly.
- Do not add UI logic in this phase.
- Do not bypass permission checks for convenience.

## Acceptance Criteria

- Structured commands can be created and retrieved.
- Only one claimant can own a live lease at a time.
- Lease expiry returns commands to a recoverable state.
- Sensitive operations are audited.

## Recommended Test Commands

```bash
pytest tests/test_command_bus.py
pytest tests/test_storage.py
```
