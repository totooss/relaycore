# Phase 11 Validation Checklist

Date: 2026-07-19

## Verified

- Claude Code and Codex CLI share the same RelayCore MCP workflow.
- One session can carry a shared event timeline across runtimes.
- Mission Control can publish commands to a selected runtime / agent.
- Commands can be claimed, completed, and failed.
- Adversarial mode runs end to end.
- Decisions and rejected options are preserved in memory quality flows.
- `memory_context` returns compact summaries, not full duplicate content.
- Command, memory, and conflict actions emit audit logs.
- CORS, SSE, and command access protections are enforced.
- Uncommitted sessions show an explicit warning in Mission Control.

## Evidence

- `pytest`
- `tests/test_mcp_tools.py`
- `tests/test_web_ui.py`
- `tests/test_security.py`
- `tests/test_collaboration_modes.py`

## Gaps

- None observed in current local validation.
