# RelayCore v1.0

RelayCore v1.0 is the first cleaned, publish-ready public release of the project.

## Highlights

- SQLite-backed shared memory and structured command relay
- append-only event timeline with digests and audit trails
- MCP-style memory and command tools
- Mission Control web UI
- memory viewer with filtering, search, and conflict resolution
- local history migration scripts

## What Changed In This Release

- finalized a public repository layout without private working files or local-only process documents
- added a Mission Control memory viewer page for direct inspection of stored memory
- added conflict resolution flows for memory candidates in both the web UI and REST API
- aligned package metadata and release assets to the `v1.0` line
- refreshed README, roadmap, and release notes for public GitHub publishing

## Included CLI

- `relaycore init-db`
- `relaycore serve`
- `relaycore export`
- `relaycore mcp-http`
- `python -m relaycore init-db`
- `python -m relaycore serve`
- `python -m relaycore export`
- `python -m relaycore mcp-http`

## Runtime Notes

- Core service: `Python 3.9+`
- MCP bridge: `Python 3.10+` with `pip install -e .[mcp]`

## Validation

- Local automated tests passed
- `pytest` status on 2026-07-19: `55 passed`

## Packaging

- source distribution
- universal wheel for the current Python package
