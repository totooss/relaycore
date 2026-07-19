# Phase 2 Schema Migrations

## Goal

Create the SQLite migration layer for sessions, commands, events, digests, memory candidates, clusters, artifacts, and audit records.

## Input Files

- `AGENTS.md`
- `docs/phases/phase-2-schema-migrations.md`
- Any existing storage or server modules once they exist

## Expected Modified Files

- `echomemory/migrations.py`
- `echomemory/storage.py`
- `tests/test_migrations.py`

## External Reference Scope

- None required by default.
- If local source context is missing, only inspect the schema sections in the build blueprint.

## Detailed TODO

1. Add SQLite migration helpers and a consistent migration entrypoint.
2. Create tables for `sessions`, `commands`, `agent_events`, `agent_states`, and `session_digests`.
3. Create tables for `memory_candidates`, `memory_occurrences`, `memory_clusters`, `artifacts`, and `audit_logs`.
4. Enable `WAL`, `synchronous=NORMAL`, and `busy_timeout`.
5. Add indexes needed for common lookup paths.
6. Make migrations safe to rerun.

## Disallowed

- Do not implement full CRUD behavior beyond what is needed to support migrations.
- Do not swap SQLite for a heavier database.
- Do not add vector stores, graph databases, or external services.

## Acceptance Criteria

- A fresh database can be initialized from code.
- Re-running migrations is idempotent.
- The schema matches the phase blueprint closely enough to support later phases.
- Database pragmas are applied intentionally.

## Recommended Test Commands

```bash
pytest tests/test_migrations.py
python -m echomemory.migrations
```
