# RelayCore Runtime Contract For Claude

Claude should use RelayCore as the durable memory backend for this repository.

## Hard Rules

- Native Claude memory is not the project memory system.
- Do not assume built-in memory will be available in future sessions.
- Do not treat prior chat recall as an acceptable substitute for RelayCore.
- Any project decision that should survive the current session must be written to RelayCore.

## Minimum Task Sequence

1. `memory_begin_task`
2. `memory_context`
3. work
4. `memory_add` or `memory_propose` for durable outcomes
5. `memory_commit_task`

## What Must Go To RelayCore

- accepted decisions
- rejected options and reasons
- reusable rules
- lessons learned
- task progress that another runtime may need
- artifact references that matter later

## What Does Not Need Durable Storage

- ephemeral chain-of-thought
- transient drafting text
- one-off exploration that does not affect future work
- formatting chatter that has no project value

## Retrieval Guidance

- Prefer `memory_context` with a bounded token budget.
- Prefer compact summaries over dumping full historical transcripts.
- Read active decisions, rules, lessons, and relevant rejected knowledge before making new decisions.

## Mission Control Boundary

- Treat Mission Control command publishing as a manual operator override path.
- Default to agent-driven command publication during normal runtime collaboration.
- Use the web UI command form only for fallback dispatch, debugging, or session seeding.

## If RelayCore Is Down

- Report the outage plainly.
- Avoid pretending native memory covers the gap.
- Keep fallback notes minimal.
- Backfill durable outcomes into RelayCore once the service is restored.
