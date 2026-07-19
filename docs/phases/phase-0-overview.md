# Phase 0 Overview

## Goal

Establish the execution scaffold for the project, map the current repository state, and prepare the repo for phase-by-phase implementation without changing business behavior.

## Input Files

- `AGENTS.md`
- `docs/ECHOMEMORY_CROSS_AGENT_BUILD_NO_OBSIDIAN.md`
- `docs/CODEX_EXECUTION_GUIDE_NO_OBSIDIAN.md`

## Expected Modified Files

- `AGENTS.md`
- `CLAUDE.md`
- `docs/phases/phase-0-overview.md`
- `docs/phases/phase-1-runtime-contract-and-adapters.md`
- `docs/phases/phase-2-schema-migrations.md`
- `docs/phases/phase-3-storage-layer.md`
- `docs/phases/phase-4-memory-quality.md`
- `docs/phases/phase-5-command-bus-api.md`
- `docs/phases/phase-6-event-log-and-sse.md`
- `docs/phases/phase-7-mcp-tools.md`
- `docs/phases/phase-8-html-mission-control.md`
- `docs/phases/phase-9-collaboration-modes.md`
- `docs/phases/phase-10-security-and-observability.md`
- `docs/phases/phase-11-tests-and-validation.md`

## External Reference Scope

- None required.
- This phase should rely only on the local build blueprint and execution guide.

## Detailed TODO

1. Read the build blueprint and execution guide.
2. Confirm what already exists in the repository.
3. Create `AGENTS.md` with compact runtime rules.
4. Create `CLAUDE.md` as a supplement that points back to `AGENTS.md`.
5. Create `docs/phases/` and split the work into phase-specific files.
6. Keep each phase file limited to the information needed for that phase.
7. Leave implementation for later phases.

## Disallowed

- Do not implement runtime code, storage, APIs, MCP tools, or UI in this phase.
- Do not copy the full blueprint into the phase files.
- Do not add Obsidian support or PKM-oriented workflows.
- Do not invent extra phases outside the approved sequence.

## Acceptance Criteria

- `AGENTS.md` exists and stays compact.
- `CLAUDE.md` exists and references `AGENTS.md`.
- `docs/phases/` contains phase files for phase 0 through phase 11.
- Each phase file includes goal, inputs, target files, external scope, TODO, constraints, acceptance, and tests.
- No business code is added in this phase.

## Recommended Test Commands

```bash
rg --files
rg -n "^## " AGENTS.md CLAUDE.md docs/phases/*.md
```
