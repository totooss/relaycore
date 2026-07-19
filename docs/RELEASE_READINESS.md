# RelayCore Release Information

Date: 2026-07-19

## Current Published Release

- Version: `v0.1.2`
- Release page: [RelayCore v0.1.2](https://github.com/totooss/relaycore/releases/tag/v0.1.2)
- Git tag: `v0.1.2`

## Repository Contents

- SQLite-backed shared memory and command store
- structured command lifecycle with permission levels
- append-only event timeline with digest generation
- MCP-style memory and coordination tools
- Mission Control web UI
- token, redaction, CORS, export, backup, and audit-related code paths
- local memory migration script for Claude/Codex layouts
- automated tests across core modules

## Validation Snapshot

- Command check: `python -m relaycore --help`
- Test command: `pytest`
- Result on 2026-07-19: `46 passed`

## Version History In Repository

- `docs/GITHUB_RELEASE_v0.1.0.md`
- `docs/GITHUB_RELEASE_v0.1.1.md`
- `docs/GITHUB_RELEASE_v0.1.2.md`

## Notes

- Historical release documents remain in the repository as documentation files.
- GitHub release entries can differ from documentation files if older releases are removed from the release page.
