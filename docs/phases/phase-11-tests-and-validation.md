# Phase 11 Tests And Validation

## Goal

Validate the full MVP with focused automated tests and lightweight integration checks across storage, memory quality, commands, events, MCP tools, adapters, and UI surfaces.

## Input Files

- `AGENTS.md`
- `docs/phases/phase-11-tests-and-validation.md`
- All implemented runtime modules
- All existing tests

## Expected Modified Files

- `tests/test_migrations.py`
- `tests/test_storage.py`
- `tests/test_memory_quality.py`
- `tests/test_command_bus.py`
- `tests/test_event_log.py`
- `tests/test_mcp_tools.py`
- `tests/test_web_ui.py`
- `tests/test_security.py`
- `tests/test_collaboration_modes.py`

## External Reference Scope

- None required.
- Validation should focus on the local implementation and the MVP acceptance list from the blueprint.

## Detailed TODO

1. Verify storage and migrations.
2. Verify command bus behavior and lease recovery.
3. Verify event appends, SSE, and digest generation.
4. Verify memory quality flows and rejected-option preservation.
5. Verify MCP tools and adapter smoke paths for Codex and Claude.
6. Verify HTML API behavior and security boundaries.
7. Verify at least one collaboration mode end to end.
8. Compare the implementation against the blueprint MVP acceptance criteria.

## Disallowed

- Do not claim completion without runnable verification or a clear explanation of gaps.
- Do not add broad unrelated end-to-end infrastructure just for testing optics.
- Do not silently skip security-sensitive checks.

## Acceptance Criteria

- Automated tests cover the major storage, API, MCP, and UI surfaces.
- Smoke tests verify Codex and Claude can attach to one shared EchoMemory workflow.
- The MVP acceptance checklist can be reviewed against actual implemented behavior.
- Any remaining gaps are explicitly documented.

## Recommended Test Commands

```bash
pytest
pytest tests/test_mcp_tools.py tests/test_web_ui.py
```
