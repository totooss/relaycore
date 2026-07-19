# RelayCore v0.1.0

RelayCore is a lightweight cross-agent memory and command relay for local AI runtimes such as Codex and Claude.

## Highlights

- SQLite-backed shared session and memory store
- Structured command relay with permission levels
- Append-only event timeline with digest generation
- MCP-style memory and coordination tools
- Mission Control web UI
- Safe local memory migration with dry-run and skip classification
- GitHub-ready packaging, CLI, and CI

## Included CLI

- `python -m relaycore init-db`
- `python -m relaycore serve`
- `python -m relaycore export`

## Validation

- Full automated test suite passing
- Local status on 2026-07-19: `46 passed`

## Notes

- Public project name: `RelayCore`
- Internal Python package name: `relaycore`
