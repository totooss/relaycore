# Phase 4 Memory Quality

## Goal

Implement the memory quality pipeline so proposed memories are normalized, deduplicated, conflict-checked, and clustered before they become durable long-term memory.

## Input Files

- `AGENTS.md`
- `docs/phases/phase-4-memory-quality.md`
- `relaycore/storage.py`
- `relaycore/memory_quality.py`

## Expected Modified Files

- `relaycore/memory_quality.py`
- `relaycore/storage.py`
- `tests/test_memory_quality.py`

## External Reference Scope

- Zep or Graphiti concepts for current-state versus historical-state handling
- Supermemory concepts for contradiction and forgetting semantics
- LangMem concepts for hot-path tools and background consolidation

Do not import their stacks, databases, or runtime frameworks.

## Detailed TODO

1. Normalize titles, content, tags, runtime labels, and metadata.
2. Add exact dedupe using content hashing.
3. Add near dedupe using lightweight similarity heuristics with FTS-backed candidates where possible.
4. Detect conflicts against active decisions and rules.
5. Implement `memory_propose`.
6. Support merge, correct, supersede, and candidate-only outcomes.
7. Assign quality and confidence signals.
8. Maintain cluster summaries and relation markers.

## Disallowed

- Do not auto-delete conflicting memories.
- Do not auto-overwrite high-risk decisions.
- Do not introduce embeddings services, graph databases, or heavyweight ML dependencies.

## Acceptance Criteria

- Exact duplicates are handled deterministically.
- Similar memories can be merged or flagged as candidates.
- Conflicts are preserved and inspectable.
- The default path favors compact summaries over full duplicated text.

## Recommended Test Commands

```bash
pytest tests/test_memory_quality.py
pytest tests/test_storage.py
```
