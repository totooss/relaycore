# Phase 8 HTML Mission Control

## Goal

Build a lightweight HTML control plane for sessions, agent status, commands, live events, candidate memories, conflict resolution, token budget visibility, and audit inspection.

## Input Files

- `AGENTS.md`
- `docs/phases/phase-8-html-mission-control.md`
- `relaycore/web_ui.py`
- `relaycore/server.py`
- `relaycore/storage.py`

## Expected Modified Files

- `relaycore/web_ui.py`
- `relaycore/server.py`
- `tests/test_web_ui.py`

## External Reference Scope

- `mcp-memory-service` dashboard concepts for operational views

Only borrow management patterns. Do not introduce direct shell control.

## Detailed TODO

1. Show session list and session detail views.
2. Show current agent states and heartbeats.
3. Add a structured command publisher UI.
4. Show a live event timeline.
5. Show a memory candidate queue.
6. Show a conflict resolution panel.
7. Show a token budget monitor.
8. Show an audit log viewer.

## Disallowed

- Do not add remote shell execution.
- Do not add generic file browsing or arbitrary command-running features.
- Do not optimize for human PKM or Markdown note workflows.

## Acceptance Criteria

- Operators can inspect sessions, commands, and events from the browser.
- Commands created in the UI remain structured and permission-scoped.
- Candidate memory conflicts are visible for manual review.
- The UI reflects token-budget and audit information without dumping excessive raw data.

## Recommended Test Commands

```bash
pytest tests/test_web_ui.py
pytest tests/test_event_log.py
```
