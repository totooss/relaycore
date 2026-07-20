# RelayCore v1.1.0

RelayCore v1.1.0 upgrades the public release line from shared state infrastructure to a first usable shared intelligence workflow.

## Highlights

- traceable digests with `node_id`, `trace_refs`, and `artifact_refs`
- Mermaid task canvas generation for digest windows
- memory levels with L3 canonical promotion rules
- rejected knowledge tracking and decision ledger foundations
- Mission Control panels for Trace Inspector, Rejected Knowledge, and Decision Ledger
- new REST and MCP read surfaces for trace and evidence lookup

## What Changed In This Release

- extended the storage schema for traceable events, structured digests, richer memory candidates, artifacts, and rejected knowledge
- upgraded event compaction from flat summaries to structured digest payloads with evidence links and task canvas output
- expanded memory quality flows to support evidence-aware proposals, canonical promotion, and rejected knowledge recording
- added REST and MCP interfaces to inspect digest traces, memory evidence, and rejected decision history
- upgraded Mission Control from a status dashboard into a knowledge control plane with trace and governance panels
- refreshed README positioning from `Shared State` toward `Shared Intelligence`

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

- local automated tests passed
- `pytest` status on July 20, 2026: `61 passed`

## Packaging

- source distribution
- universal wheel for the current Python package
