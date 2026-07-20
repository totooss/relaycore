"""Typed storage records used by the RelayCore repository layer."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


JsonDict = Dict[str, Any]
JsonList = List[Any]


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    name: str
    goal: str
    mode: str
    status: str
    created_by: str
    created_at: str
    updated_at: str
    metadata: JsonDict


@dataclass(frozen=True)
class CommandRecord:
    command_id: str
    session_id: str
    target_agent: Optional[str]
    target_runtime: Optional[str]
    mode: str
    command_type: str
    payload: JsonDict
    status: str
    priority: int
    created_by: str
    created_at: str
    claimed_by: Optional[str]
    claimed_at: Optional[str]
    lease_expires_at: Optional[str]
    completed_at: Optional[str]
    result: JsonDict
    idempotency_key: Optional[str]
    permission_level: str


@dataclass(frozen=True)
class AgentEventRecord:
    seq: int
    session_id: str
    agent_id: str
    runtime: Optional[str]
    mode: Optional[str]
    event_type: str
    content: JsonDict
    command_id: Optional[str]
    parent_seq: Optional[int]
    node_id: str
    trace_refs: JsonList
    artifact_refs: JsonList
    metadata: JsonDict
    created_at: str


@dataclass(frozen=True)
class AgentStateRecord:
    agent_id: str
    runtime: str
    session_id: Optional[str]
    role: Optional[str]
    status: str
    last_seen_seq: int
    last_heartbeat: Optional[str]
    current_task: Optional[str]
    capabilities: JsonList
    metadata: JsonDict


@dataclass(frozen=True)
class SessionDigestRecord:
    digest_id: str
    session_id: str
    from_seq: int
    to_seq: int
    summary: str
    decisions: JsonList
    open_questions: JsonList
    rejected_candidates: JsonList
    node_id: str
    trace_refs: JsonList
    artifact_refs: JsonList
    task_canvas: str
    created_at: str


@dataclass(frozen=True)
class MemoryCandidateRecord:
    candidate_id: str
    proposed_by: str
    runtime: Optional[str]
    session_id: Optional[str]
    type: str
    title: str
    content: str
    summary: str
    rejected: JsonList
    tags: JsonList
    status: str
    similar_to: JsonList
    conflicts_with: JsonList
    recommended_action: str
    node_id: str
    trace_refs: JsonList
    artifact_refs: JsonList
    memory_level: str
    decision_status: str
    created_at: str
    resolved_at: Optional[str]


@dataclass(frozen=True)
class MemoryOccurrenceRecord:
    id: int
    memory_id: str
    agent_id: str
    runtime: Optional[str]
    session_id: Optional[str]
    observed_at: str
    note: str


@dataclass(frozen=True)
class MemoryClusterRecord:
    cluster_id: str
    canonical_memory_id: str
    summary: str
    tags: JsonList
    source_count: int
    quality_score: float
    updated_at: str
    metadata: JsonDict


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    session_id: Optional[str]
    agent_id: Optional[str]
    kind: str
    path: str
    sha256: str
    size_bytes: int
    summary: str
    trace_refs: JsonList
    metadata: JsonDict
    created_at: str


@dataclass(frozen=True)
class RejectedKnowledgeRecord:
    rejected_id: str
    session_id: Optional[str]
    candidate_id: str
    accepted_candidate_id: Optional[str]
    decision_type: str
    reason: str
    trace_refs: JsonList
    artifact_refs: JsonList
    metadata: JsonDict
    created_at: str


@dataclass(frozen=True)
class AuditLogRecord:
    id: int
    actor: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    request_id: Optional[str]
    ip: Optional[str]
    metadata: JsonDict
    created_at: str
