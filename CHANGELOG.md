# Changelog

## 1.0.0 - 2026-07-19

### Added

- Mission Control memory viewer with filtering, search, and bilingual UI support
- memory candidate conflict resolution from the web UI and REST API
- more stable SSE test coverage for live event streaming

### Changed

- repository contents were cleaned for public release packaging
- README, roadmap, and release notes were rewritten for a publish-ready GitHub presentation
- package metadata and versioning were aligned to the `1.0.0` public release

### Validation

- `pytest`: `55 passed`

## 0.1.3 - 2026-07-19

### Added

- streamable HTTP MCP bridge for Codex / Claude-style runtimes
- `relaycore mcp-http` CLI entrypoint
- explicit optional dependency path for MCP support on Python 3.10+

### Changed

- README now documents a verified local Codex deployment path
- package metadata no longer exposes the previous personal author name

### Validation

- `pytest`: `48 passed`

## 0.1.2 - 2026-07-19

### Changed

- unified the internal Python package name to `relaycore`
- renamed runtime code, tests, scripts, env vars, metrics, and headers to `RelayCore`
- removed obsolete compatibility wording from public docs

### Notes

- inspiration attribution remains `EastSword/EchoMemory`

## 0.1.1 - 2026-07-19

### Added

- Chinese-first public README
- public comparison table and architecture diagram
- explicit inspiration note for `EastSword/EchoMemory`
- refreshed public release packaging and naming cleanup

### Notes

- Public project name: `RelayCore`
- Internal Python package name: `relaycore`

## 0.1.0 - 2026-07-19

### Added

- SQLite-backed shared memory and command relay
- Event timeline with digest generation
- MCP-style tool surface
- Mission Control operator UI
- Baseline security controls
- Safe local memory migration
- CLI entrypoints and GitHub CI

### Notes

- Public project name: RelayCore
- Internal Python package name: `relaycore`
