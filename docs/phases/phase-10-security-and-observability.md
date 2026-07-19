# Phase 10 Security And Observability

## Goal

Add baseline security controls and operational visibility so the system can be exposed safely to multiple agent runtimes and operator interfaces.

## Input Files

- `AGENTS.md`
- `docs/phases/phase-10-security-and-observability.md`
- `relaycore/server.py`
- `relaycore/mcp_server.py`
- `relaycore/storage.py`

## Expected Modified Files

- `relaycore/server.py`
- `relaycore/mcp_server.py`
- `relaycore/token_budget.py`
- `tests/test_security.py`

## External Reference Scope

- `mcp-memory-service` concepts for operational access boundaries

Do not import OAuth stacks or unrelated hosted systems unless the phase explicitly expands.

## Detailed TODO

1. Add CORS allowlist behavior.
2. Add SSE authentication or equivalent access control.
3. Expand audit coverage for commands, memory changes, and conflict actions.
4. Add secret redaction for logs and visible payloads.
5. Add token-budget estimation helpers.
6. Add a metrics endpoint or equivalent observability surface.
7. Add backup and export support suitable for SQLite-backed storage.

## Disallowed

- Do not expose unauthenticated live streams.
- Do not log secrets in raw form.
- Do not weaken permission boundaries for convenience.

## Acceptance Criteria

- Browser and MCP surfaces have baseline access protections.
- Sensitive operations are audited and secrets are redacted.
- Operators can inspect metrics and token-budget status.
- Backup or export workflows exist for stored data.

## Recommended Test Commands

```bash
pytest tests/test_security.py
pytest tests/test_web_ui.py
```
