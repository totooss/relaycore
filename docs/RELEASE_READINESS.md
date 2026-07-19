# RelayCore Release Readiness

Date: 2026-07-19

## Overall Judgment

RelayCore is ready for a public GitHub MVP release.

It is not yet fully ready for unattended production deployment in a multi-user environment without additional hardening.

## Completion Assessment

- Core control-plane functionality: 90%
- Security baseline for local/internal deployment: 80%
- Operator tooling and migration support: 80%
- Packaging and public-release readiness: 85%
- Production hardening for broader deployment: 60%

## What Is Already Strong

- SQLite-backed shared memory and command store
- Structured command lifecycle with permission levels
- Shared event timeline with digest generation
- MCP-style memory and coordination tools
- Mission Control operator UI
- Baseline token protection, redaction, CORS, export, backup, and audit logging
- Safe local memory migration with dry-run and skip classification
- Automated tests across core modules

## Remaining Gaps Before Broader Production Use

- Stronger deployment docs and environment management
- More complete runtime-store and history import adapters
- Richer metrics and structured observability
- Explicit restore drills and operational runbooks
- Stronger auth model for multi-user internet-facing deployment

## Recommended Public Name

RelayCore

Reason:

- short,
- easier to remember than EchoMemory,
- better aligned with cross-runtime command and memory relay behavior,
- broad enough to grow beyond one memory subsystem.

## Release Recommendation

Publish now as:

- `v0.1.0`
- GitHub-first MVP release
- clearly described as a local/self-hosted beta
