# Phase 1 Runtime Contract And Adapters

## Goal

Add the short runtime contract and adapter-facing configuration examples so Codex and Claude can attach to the same EchoMemory workflow with minimal context overhead.

## Input Files

- `AGENTS.md`
- `CLAUDE.md`
- `docs/CODEX_EXECUTION_GUIDE_NO_OBSIDIAN.md`
- `docs/ECHOMEMORY_CROSS_AGENT_BUILD_NO_OBSIDIAN.md`

## Expected Modified Files

- `AGENTS.md`
- `CLAUDE.md`
- `.codex/config.toml`
- `.codex/hooks.json`
- `docs/claude-hooks.md`

## External Reference Scope

- `AgentMemory/.claude-plugin`
- `AgentMemory/.codex-plugin`
- `AgentMemory/packages/mcp`
- `AgentMemory/INSTALL_FOR_AGENTS.md`
- `AgentMemory/integrations`

Only extract adapter patterns. Do not copy implementations or read unrelated folders.

## Detailed TODO

1. Finalize the compact runtime contract for all agent runtimes.
2. Add Codex MCP configuration examples.
3. Add Codex hook examples only if the referenced hook commands exist or are clearly marked as examples.
4. Add Claude-facing setup notes that mirror the same contract.
5. Keep adapter behavior symmetric across Codex and Claude.
6. Document how to proceed when EchoMemory MCP is not yet available.

## Disallowed

- Do not implement MCP server logic in this phase.
- Do not add separate business rules for Codex and Claude.
- Do not add HTML command execution or UI features.
- Do not add Obsidian integration.

## Acceptance Criteria

- Runtime rules remain under the intended short-form size.
- Codex and Claude both have setup guidance tied to the same contract.
- `.codex/` examples are syntactically valid examples.
- The repository has a clear fallback path when MCP is unavailable.

## Recommended Test Commands

```bash
sed -n '1,220p' AGENTS.md
sed -n '1,220p' CLAUDE.md
python - <<'PY'
import json, pathlib
path = pathlib.Path(".codex/hooks.json")
if path.exists():
    json.load(path.open())
print("hooks.json ok or not created")
PY
```
