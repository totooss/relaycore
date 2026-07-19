# 2026-07-19 RelayCore Full Internal Rename

## Decision

The project now uses `RelayCore` and `relaycore` as the only active product and package names across runtime code, tests, scripts, packaging, and public documentation.

## Why

- Mixed naming between `EchoMemory` and `RelayCore` created release risk and operator confusion.
- The user explicitly requested a zero-drift full rename with no compatibility-layer leftovers.
- A single package name improves install, import, CLI, environment variable, and observability consistency.

## Applied Scope

- Python package path: `relaycore/`
- Console entrypoint: `relaycore`
- Module entrypoint: `python -m relaycore`
- Environment variables: `RELAYCORE_*`
- Access header: `X-RelayCore-Access-Token`
- Metrics prefix: `relaycore_*`
- Default database filename: `relaycore.db`

## Exception

The only remaining `EchoMemory` references are explicit attribution links and notes pointing to the inspiration source `EastSword/EchoMemory`.

## Runtime Note

RelayCore MCP tools were not available as a live backend in this task, so this durable decision was recorded under `docs/decisions/` per project rules.
