# RelayCore

RelayCore is a lightweight cross-agent memory and command relay for Codex, Claude, and other local runtimes.

The repository keeps the internal Python package name `echomemory` for compatibility, while the public project name is now `RelayCore`.

## What It Does

- Stores shared session state in SQLite.
- Relays structured commands across runtimes.
- Maintains an append-only event timeline with digest generation.
- Exposes a compact MCP-style tool surface.
- Provides an operator-facing Mission Control web UI.
- Supports safe local memory migration from selected Claude and Codex sources.

## Project Status

RelayCore is at a strong MVP stage and is suitable for:

- local development,
- private team workflows,
- operator-supervised migrations,
- internal demos and pilot rollouts.

It is not yet a fully hardened production platform for large-scale unattended deployment. The main remaining work is around packaging polish, deployment ergonomics, observability depth, and broader source adapters.

## Current Completion Assessment

- Core product completeness: high
- Runtime safety baseline: solid
- Local migration utility: good with explicit guardrails
- Public release readiness: now suitable for GitHub publication
- Production hardening beyond MVP: still in progress

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python -m echomemory init-db
python -m echomemory serve --host 127.0.0.1 --port 8080
```

Then open:

- `http://127.0.0.1:8080/mission-control`

## Local Memory Migration

Preview importable memories without writing:

```bash
python scripts/migrate_local_memories.py --dry-run
```

Include summarized history and supported runtime-store summaries:

```bash
python scripts/migrate_local_memories.py --dry-run --include-history --include-runtime-store
```

Import into the local database:

```bash
python scripts/migrate_local_memories.py --session-id local-memory-migration
```

## CLI

RelayCore ships with a minimal CLI:

```bash
python -m echomemory init-db
python -m echomemory serve
python -m echomemory export
```

## Tests

```bash
pytest
```

Current local validation status on July 19, 2026: `46 passed`.

## Repository Layout

- `echomemory/`: core package
- `scripts/`: operator scripts, including local memory migration
- `tests/`: automated test suite
- `docs/`: execution notes, decisions, and roadmap

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md).

## License

MIT. See [LICENSE](LICENSE).
