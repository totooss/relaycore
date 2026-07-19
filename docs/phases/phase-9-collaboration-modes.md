# Phase 9 Collaboration Modes

## Goal

Define and implement shared collaboration modes so multiple agents can coordinate under predictable templates such as assist, review, adversarial, debate, and pipeline.

## Input Files

- `AGENTS.md`
- `docs/phases/phase-9-collaboration-modes.md`
- `relaycore/command_bus.py`
- `relaycore/runtime_adapters.py`
- `relaycore/web_ui.py`

## Expected Modified Files

- `relaycore/command_bus.py`
- `relaycore/runtime_adapters.py`
- `relaycore/web_ui.py`
- `tests/test_collaboration_modes.py`

## External Reference Scope

- None required by default.
- If local examples are needed, only inspect collaboration patterns that map cleanly to structured commands and events.

## Detailed TODO

1. Define mode templates for `assist`, `review`, `adversarial`, `debate`, and `pipeline`.
2. Represent mode templates in structured JSON or equivalent serializable config.
3. Ensure command publication can attach a collaboration mode.
4. Ensure event timelines clearly identify mode transitions and participants.
5. Add UI affordances for publishing mode templates quickly.
6. Validate at least one end-to-end multi-agent mode, with `adversarial` required by the blueprint.

## Disallowed

- Do not invent free-form orchestration that bypasses the command bus.
- Do not couple collaboration modes to a single runtime vendor.
- Do not add agent-private hidden state sharing.

## Acceptance Criteria

- Each collaboration mode has a documented structured template.
- Commands and events can carry mode metadata.
- At least one mode is validated end to end.
- The implementation remains compatible with multiple runtimes.

## Recommended Test Commands

```bash
pytest tests/test_collaboration_modes.py
pytest tests/test_command_bus.py
```
