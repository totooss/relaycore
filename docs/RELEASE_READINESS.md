# RelayCore Release Information

Date: 2026-07-19

## Current Published Release

- Version: `v1.0`
- Release page: `to be created from docs/GITHUB_RELEASE_v1.0.md`
- Git tag: `v1.0`

## Repository Contents

- SQLite-backed shared memory and command store
- structured command lifecycle with permission levels
- append-only event timeline with digest generation
- MCP-style memory and coordination tools
- Mission Control web UI
- Mission Control memory viewer with conflict-resolution workflow
- token, redaction, CORS, export, backup, and audit-related code paths
- local memory migration scripts
- automated tests across core modules

## Validation Snapshot

- Command check: `python -m relaycore --help`
- Test command: `pytest`
- Result on 2026-07-19: `55 passed`

## Version History In Repository

- `CHANGELOG.md`
- `docs/GITHUB_RELEASE_v1.0.md`

## Notes

- This repository has been trimmed to public release content only.
- Release notes should be published from `docs/GITHUB_RELEASE_v1.0.md`.
