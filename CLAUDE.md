# CLAUDE.md

Follow [`AGENTS.md`](AGENTS.md) as the primary runtime contract for this repository.

Additional Claude-oriented notes:

- Use EchoMemory as the only durable memory backend for project decisions.
- Prefer compact summaries over long transcripts or full document recall.
- When implementing, read only the active phase file under `docs/phases/` plus the source files that phase names.
- Do not expand scope into later phases without an explicit request.
- Do not drift during execution from the currently confirmed phase or task boundary.
- If new ideas come up mid-execution, record them as follow-up items instead of implementing them immediately.
- If EchoMemory MCP is unavailable, record durable decisions under `docs/decisions/`.
- Keep Claude behavior aligned with the Codex adapter contract unless a runtime-specific limitation is documented.
- Do not add Obsidian-related features or human PKM workflows.
- Do not make the web UI a remote shell or unrestricted command executor.
