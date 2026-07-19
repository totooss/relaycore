# RelayCore Roadmap

## Completion Snapshot

RelayCore has completed the MVP control-plane loop:

- shared sessions,
- structured command relay,
- event timeline and digests,
- MCP-style memory tools,
- Mission Control UI,
- baseline security controls,
- safe local memory migration.

## Next Priority

### 1. Release Hardening

- Add semantic versioning and release tags.
- Add a lightweight changelog discipline.
- Add startup smoke checks for required environment variables.
- Add CLI-level integration tests.

### 2. Deployment Ergonomics

- Add a small config reference for host, port, token, CORS, and backup paths.
- Add Docker packaging for local and server deployment.
- Add a reverse-proxy deployment example.

### 3. Observability Depth

- Expand metrics beyond counts into latency and error buckets.
- Add structured logs for operators.
- Add import/export audit summaries.

### 4. Migration Maturity

- Add per-entry preview and approval flow in Mission Control.
- Add richer source adapters for more Claude/Codex layouts.
- Add import dedupe preview and rollback snapshots.

### 5. Multi-Runtime Interop

- Add stronger runtime capability discovery.
- Add richer routing filters for agent pools.
- Add artifact handoff metadata between stages.

### 6. Production Safety

- Add stronger auth options for multi-user deployments.
- Add rate-limiting or request throttling.
- Add backup restore drills and recovery docs.

## Suggested Release Sequence

### v0.1.0

- Public GitHub release of the current MVP.

### v0.2.0

- Deployment packaging, Docker, and richer config docs.

### v0.3.0

- Migration preview UI and operator approval workflow.

### v0.4.0

- Production-grade observability and deployment hardening.
