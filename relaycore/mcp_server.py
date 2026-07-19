"""Lightweight MCP-style tool registry for RelayCore."""

from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from .command_bus import CommandBusService, serialize_command
from .event_log import EventLogService, serialize_digest, serialize_event
from .memory_quality import MemoryQualityService, combined_similarity, summarize_content
from .runtime_adapters import RuntimeAdapterRegistry
from .storage import RelayCoreStorage, utc_now
from .token_budget import estimate_tokens, redact_structure


def compact_rejected_summary(candidate) -> List[str]:
    rejected = list(candidate.rejected or [])
    conflicts = list(candidate.conflicts_with or [])
    return [str(item) for item in (rejected + conflicts)[:3]]


@dataclass(frozen=True)
class MCPToolDefinition:
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPToolError(Exception):
    """Raised when an MCP-style tool invocation fails validation."""


class RelayCoreMCPServer:
    """Expose RelayCore capabilities through a compact MCP-style tool registry."""

    def __init__(
        self,
        storage: Optional[RelayCoreStorage] = None,
        *,
        command_bus: Optional[CommandBusService] = None,
        event_log: Optional[EventLogService] = None,
        memory_quality: Optional[MemoryQualityService] = None,
        adapters: Optional[RuntimeAdapterRegistry] = None,
    ) -> None:
        self.storage = storage or RelayCoreStorage()
        self.event_log = event_log or EventLogService(self.storage)
        self.command_bus = command_bus or CommandBusService(self.storage, event_log=self.event_log)
        if self.command_bus.event_log is None:
            self.command_bus.event_log = self.event_log
        self.memory_quality = memory_quality or MemoryQualityService(self.storage, event_log=self.event_log)
        if self.memory_quality.event_log is None:
            self.memory_quality.event_log = self.event_log
        self.adapters = adapters or RuntimeAdapterRegistry()
        self._tools = {
            "memory_begin_task": self.memory_begin_task,
            "memory_context": self.memory_context,
            "memory_propose": self.memory_propose,
            "memory_add": self.memory_add,
            "memory_commit_task": self.memory_commit_task,
            "command_poll": self.command_poll,
            "command_claim": self.command_claim,
            "command_complete": self.command_complete,
            "command_fail": self.command_fail,
            "agent_event_append": self.agent_event_append,
            "session_digest_get": self.session_digest_get,
            "agent_heartbeat": self.agent_heartbeat,
        }

    def list_tools(self) -> List[MCPToolDefinition]:
        return [
            MCPToolDefinition(
                name="memory_begin_task",
                description="Create or resume a session and register the calling runtime.",
                input_schema={"type": "object", "required": ["session_id", "runtime"]},
            ),
            MCPToolDefinition(
                name="memory_context",
                description="Return compact relevant memory summaries for a session or query.",
                input_schema={"type": "object", "required": ["session_id", "runtime"]},
            ),
            MCPToolDefinition(
                name="memory_propose",
                description="Normalize and score a proposed memory before durable promotion.",
                input_schema={"type": "object", "required": ["session_id", "runtime", "type", "title", "content"]},
            ),
            MCPToolDefinition(
                name="memory_add",
                description="Persist an explicit active memory entry with compact summaries.",
                input_schema={"type": "object", "required": ["session_id", "runtime", "type", "title", "content"]},
            ),
            MCPToolDefinition(
                name="memory_commit_task",
                description="Commit a task summary and create a digest for uncommitted events.",
                input_schema={"type": "object", "required": ["session_id", "runtime"]},
            ),
            MCPToolDefinition(
                name="command_poll",
                description="Poll compact pending commands for a runtime or agent.",
                input_schema={"type": "object", "required": ["runtime", "requester_permission_level"]},
            ),
            MCPToolDefinition(
                name="command_claim",
                description="Claim a structured command with a lease.",
                input_schema={"type": "object", "required": ["command_id", "runtime", "claimed_by", "requester_permission_level"]},
            ),
            MCPToolDefinition(
                name="command_complete",
                description="Complete a claimed command with a structured result.",
                input_schema={"type": "object", "required": ["command_id", "runtime", "claimed_by", "requester_permission_level", "result"]},
            ),
            MCPToolDefinition(
                name="command_fail",
                description="Fail a claimed command with a structured result payload.",
                input_schema={"type": "object", "required": ["command_id", "runtime", "claimed_by", "requester_permission_level"]},
            ),
            MCPToolDefinition(
                name="agent_event_append",
                description="Append an important shared event to the session timeline.",
                input_schema={"type": "object", "required": ["session_id", "runtime", "event_type", "content"]},
            ),
            MCPToolDefinition(
                name="session_digest_get",
                description="Fetch recent session digests without returning full timelines.",
                input_schema={"type": "object", "required": ["session_id", "runtime"]},
            ),
            MCPToolDefinition(
                name="agent_heartbeat",
                description="Update runtime heartbeat and capabilities for an agent.",
                input_schema={"type": "object", "required": ["runtime"]},
            ),
        ]

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if name not in self._tools:
            raise MCPToolError("unknown tool {!r}".format(name))
        return self._tools[name](**(arguments or {}))

    def memory_begin_task(
        self,
        *,
        session_id: str,
        runtime: str,
        agent_id: Optional[str] = None,
        mode: Optional[str] = None,
        name: Optional[str] = None,
        goal: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        context = self.adapters.normalize(
            runtime=runtime,
            agent_id=agent_id,
            session_id=session_id,
            mode=mode,
            metadata=metadata,
        )
        try:
            session = self.storage.get_session(session_id)
            session = self.storage.update_session(
                session_id,
                mode=context.mode,
                status="active",
                metadata={"last_runtime": context.runtime, **context.metadata},
            )
        except Exception:
            session = self.storage.create_session(
                session_id=session_id,
                name=name or "Session {}".format(session_id),
                goal=goal or "Active RelayCore task",
                mode=context.mode,
                created_by=context.agent_id,
                metadata={"last_runtime": context.runtime, **context.metadata},
            )
        heartbeat = self.agent_heartbeat(
            runtime=context.runtime,
            agent_id=context.agent_id,
            session_id=session_id,
            status="active",
            current_task=session.goal,
            metadata=context.metadata,
        )
        self.event_log.append_event(
            session_id=session_id,
            agent_id=context.agent_id,
            runtime=context.runtime,
            mode=context.mode,
            event_type="task_begin",
            content={"session_id": session_id, "goal": session.goal},
            metadata={"source": "mcp"},
        )
        return {
            "session": asdict(session),
            "heartbeat": heartbeat["agent_state"],
            "message": "Session ready for shared long-term memory.",
        }

    def memory_context(
        self,
        *,
        session_id: str,
        runtime: str,
        agent_id: Optional[str] = None,
        query: Optional[str] = None,
        max_items: int = 5,
        max_tokens: int = 1200,
        include_full_content: bool = False,
    ) -> Dict[str, Any]:
        context = self.adapters.normalize(runtime=runtime, agent_id=agent_id, session_id=session_id)
        candidates = self.storage.list_memory_candidates(limit=500)
        filtered = [
            candidate
            for candidate in candidates
            if candidate.status in ("active", "pending", "rejected")
        ]
        ranked = []
        for candidate in filtered:
            reasons = []
            score = 0.4 if candidate.session_id == session_id else 0.1
            if candidate.status == "active":
                score += 0.25
                reasons.append("active memory")
            if candidate.type in ("decision", "rule", "lesson"):
                score += 0.15
                reasons.append("runtime contract type")
            rejected_summary = compact_rejected_summary(candidate)
            if rejected_summary:
                score += 0.35
                reasons.append("keeps rejected/conflict context")
            if query:
                query_score = combined_similarity(query, query, candidate.title, candidate.content)
                score += query_score
                if query_score > 0.5:
                    reasons.append("query match")
            elif candidate.session_id == session_id:
                reasons.append("same session")
            ranked.append((score, reasons, candidate))
        ranked.sort(key=lambda item: item[0], reverse=True)

        items = []
        token_budget = 0
        for score, reasons, candidate in ranked:
            item = {
                "id": candidate.candidate_id,
                "type": candidate.type,
                "title": candidate.title,
                "status": candidate.status,
                "summary": redact_structure(candidate.summary or summarize_content(candidate.content)),
                "why_relevant": ", ".join(reasons[:3]) or "recent memory",
                "rejected_summary": redact_structure(compact_rejected_summary(candidate)),
                "expand_handle": {"candidate_id": candidate.candidate_id, "include_full_content": include_full_content},
            }
            if include_full_content:
                item["content"] = redact_structure(candidate.content)
            projected_tokens = token_budget + estimate_tokens(item["summary"]) + estimate_tokens(item["why_relevant"])
            if include_full_content:
                projected_tokens += estimate_tokens(candidate.content)
            if items and projected_tokens > max_tokens:
                break
            items.append(item)
            token_budget = projected_tokens
            if len(items) >= max_items:
                break

        return {
            "runtime": context.runtime,
            "session_id": session_id,
            "max_items": max_items,
            "max_tokens": max_tokens,
            "include_full_content": include_full_content,
            "items": items,
        }

    def memory_propose(self, **arguments: Any) -> Dict[str, Any]:
        required = ("session_id", "runtime", "type", "title", "content")
        self._require(arguments, *required)
        context = self.adapters.normalize(
            runtime=arguments["runtime"],
            agent_id=arguments.get("agent_id"),
            session_id=arguments["session_id"],
            mode=arguments.get("mode"),
            metadata=arguments.get("metadata"),
        )
        result = self.memory_quality.memory_propose(
            proposed_by=context.agent_id,
            type=arguments["type"],
            title=arguments["title"],
            content=arguments["content"],
            runtime=context.runtime,
            session_id=arguments["session_id"],
            tags=arguments.get("tags"),
            rejected=arguments.get("rejected"),
            metadata=context.metadata,
            relation_hint=arguments.get("relation_hint"),
        )
        return {
            "candidate": redact_structure(asdict(result.candidate)),
            "action": result.action,
            "confidence": result.confidence,
            "quality_score": result.quality_score,
            "duplicate_of": result.duplicate_of,
            "similar_to": result.similar_to,
            "conflicts_with": result.conflicts_with,
            "cluster_id": result.cluster_id,
            "summary": result.summary,
        }

    def memory_add(self, **arguments: Any) -> Dict[str, Any]:
        required = ("session_id", "runtime", "type", "title", "content")
        self._require(arguments, *required)
        context = self.adapters.normalize(
            runtime=arguments["runtime"],
            agent_id=arguments.get("agent_id"),
            session_id=arguments["session_id"],
            mode=arguments.get("mode"),
            metadata=arguments.get("metadata"),
        )
        normalized = self.memory_quality.normalize_proposal(
            proposed_by=context.agent_id,
            type=arguments["type"],
            title=arguments["title"],
            content=arguments["content"],
            runtime=context.runtime,
            session_id=arguments["session_id"],
            tags=arguments.get("tags"),
            rejected=arguments.get("rejected"),
            metadata=context.metadata,
        )
        candidate = self.storage.create_memory_candidate(
            candidate_id="mem-{}".format(uuid4().hex[:12]),
            proposed_by=context.agent_id,
            runtime=context.runtime,
            session_id=arguments["session_id"],
            type=normalized.type,
            title=normalized.title,
            content=normalized.content,
            summary=normalized.summary,
            rejected=normalized.rejected,
            tags=normalized.tags,
            status="active",
            similar_to=[],
            conflicts_with=[],
            recommended_action="memory_add",
            resolved_at=utc_now(),
        )
        cluster = self.storage.upsert_memory_cluster(
            cluster_id="cluster-{}".format(candidate.candidate_id),
            canonical_memory_id=candidate.candidate_id,
            summary=candidate.summary,
            tags=candidate.tags,
            source_count=1,
            quality_score=0.85,
            metadata={"action": "memory_add", "runtime": context.runtime},
        )
        self.storage.record_memory_occurrence(
            memory_id=candidate.candidate_id,
            agent_id=context.agent_id,
            runtime=context.runtime,
            session_id=arguments["session_id"],
            note="Explicit active memory add",
        )
        self.storage.append_audit_log(
            actor=context.agent_id,
            action="memory_add",
            resource_type="memory_candidate",
            resource_id=candidate.candidate_id,
            metadata={"cluster_id": cluster.cluster_id},
        )
        self.event_log.append_event(
            session_id=arguments["session_id"],
            agent_id=context.agent_id,
            runtime=context.runtime,
            mode=context.mode,
            event_type="memory_added",
            content={
                "candidate_id": candidate.candidate_id,
                "action": "memory_add",
                "summary": candidate.summary,
            },
            metadata={"source": "mcp"},
        )
        return {
            "candidate": redact_structure(asdict(candidate)),
            "cluster_id": cluster.cluster_id,
            "action": "memory_add",
            "summary": candidate.summary,
        }

    def memory_commit_task(
        self,
        *,
        session_id: str,
        runtime: str,
        agent_id: Optional[str] = None,
        summary: Optional[str] = None,
        decisions: Optional[List[Any]] = None,
        open_questions: Optional[List[Any]] = None,
        rejected_candidates: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        context = self.adapters.normalize(runtime=runtime, agent_id=agent_id, session_id=session_id)
        latest = self.storage.get_latest_session_digest(session_id)
        next_from_seq = latest.to_seq + 1 if latest else 1
        events = self.storage.list_events_window(session_id, next_from_seq, limit=500)
        digest = None
        if events:
            digest_summary = summary or "Task commit for events {}-{}.".format(events[0].seq, events[-1].seq)
            digest = self.storage.create_session_digest(
                digest_id="digest-{}".format(uuid4().hex[:12]),
                session_id=session_id,
                from_seq=events[0].seq,
                to_seq=events[-1].seq,
                summary=digest_summary,
                decisions=decisions or [],
                open_questions=open_questions or [],
                rejected_candidates=rejected_candidates or [],
            )
        self.storage.update_session(
            session_id,
            metadata={"last_commit_at": utc_now(), "last_commit_runtime": context.runtime},
        )
        self.event_log.append_event(
            session_id=session_id,
            agent_id=context.agent_id,
            runtime=context.runtime,
            mode=context.mode,
            event_type="task_commit",
            content={"summary": summary or "Task committed", "digest_created": digest is not None},
            metadata={"source": "mcp"},
        )
        return {
            "session_id": session_id,
            "digest": redact_structure(serialize_digest(digest)) if digest is not None else None,
            "message": "Task commit recorded.",
        }

    def command_poll(
        self,
        *,
        runtime: str,
        requester_permission_level: str,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        context = self.adapters.normalize(runtime=runtime, agent_id=agent_id, session_id=session_id)
        commands = self.command_bus.list_pending_commands(
            requester_permission_level=requester_permission_level,
            session_id=session_id,
            target_runtime=context.runtime,
            target_agent=None,
            limit=limit,
        )
        return {
            "commands": [redact_structure(serialize_command(command)) for command in commands],
            "count": len(commands),
        }

    def command_claim(
        self,
        *,
        command_id: str,
        runtime: str,
        claimed_by: str,
        requester_permission_level: str,
        lease_seconds: int = 300,
    ) -> Dict[str, Any]:
        context = self.adapters.normalize(runtime=runtime, agent_id=claimed_by)
        command = self.command_bus.claim_command(
            command_id,
            claimed_by=context.agent_id,
            requester_permission_level=requester_permission_level,
            lease_seconds=lease_seconds,
        )
        return {"command": redact_structure(serialize_command(command))}

    def command_complete(
        self,
        *,
        command_id: str,
        runtime: str,
        claimed_by: str,
        requester_permission_level: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        context = self.adapters.normalize(runtime=runtime, agent_id=claimed_by)
        command = self.command_bus.complete_command(
            command_id,
            claimed_by=context.agent_id,
            requester_permission_level=requester_permission_level,
            result=result,
        )
        return {"command": redact_structure(serialize_command(command))}

    def command_fail(
        self,
        *,
        command_id: str,
        runtime: str,
        claimed_by: str,
        requester_permission_level: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        context = self.adapters.normalize(runtime=runtime, agent_id=claimed_by)
        command = self.command_bus.fail_command(
            command_id,
            claimed_by=context.agent_id,
            requester_permission_level=requester_permission_level,
            result=result,
        )
        return {"command": redact_structure(serialize_command(command))}

    def agent_event_append(
        self,
        *,
        session_id: str,
        runtime: str,
        event_type: str,
        content: Dict[str, Any],
        agent_id: Optional[str] = None,
        mode: Optional[str] = None,
        command_id: Optional[str] = None,
        parent_seq: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        context = self.adapters.normalize(
            runtime=runtime,
            agent_id=agent_id,
            session_id=session_id,
            mode=mode,
            metadata=metadata,
        )
        event = self.event_log.append_event(
            session_id=session_id,
            agent_id=context.agent_id,
            runtime=context.runtime,
            mode=context.mode,
            event_type=event_type,
            content=content,
            command_id=command_id,
            parent_seq=parent_seq,
            metadata=context.metadata,
        )
        return {"event": redact_structure(serialize_event(event))}

    def session_digest_get(
        self,
        *,
        session_id: str,
        runtime: str,
        limit: int = 5,
    ) -> Dict[str, Any]:
        self.adapters.normalize(runtime=runtime, session_id=session_id)
        digests = self.storage.list_session_digests(session_id, limit=limit)
        return {"digests": [redact_structure(serialize_digest(digest)) for digest in digests]}

    def agent_heartbeat(
        self,
        *,
        runtime: str,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        role: Optional[str] = None,
        status: str = "active",
        last_seen_seq: int = 0,
        current_task: Optional[str] = None,
        capabilities: Optional[List[Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        context = self.adapters.normalize(
            runtime=runtime,
            agent_id=agent_id,
            session_id=session_id,
            metadata=metadata,
        )
        state = self.storage.upsert_agent_state(
            agent_id=context.agent_id,
            runtime=context.runtime,
            session_id=session_id,
            role=role,
            status=status,
            last_seen_seq=last_seen_seq,
            current_task=current_task,
            capabilities=capabilities,
            metadata=context.metadata,
        )
        return {"agent_state": redact_structure(asdict(state))}

    def _require(self, arguments: Dict[str, Any], *required: str) -> None:
        for name in required:
            if name not in arguments:
                raise MCPToolError("missing required argument {!r}".format(name))
