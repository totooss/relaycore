"""Append-only event log coordination and SSE formatting."""

from dataclasses import asdict
import json
from queue import Empty, Queue
import re
from threading import Lock
from typing import Any, Dict, Generator, List, Optional
from uuid import uuid4

from .models import AgentEventRecord, SessionDigestRecord
from .storage import RelayCoreStorage
from .token_budget import redact_structure

DIGEST_BATCH_SIZE = 10
STREAM_BACKLOG_LIMIT = 100


def serialize_event(event: AgentEventRecord) -> Dict[str, Any]:
    return asdict(event)


def serialize_digest(digest: SessionDigestRecord) -> Dict[str, Any]:
    return asdict(digest)


def format_sse(event_name: str, data: Dict[str, Any], event_id: Optional[int] = None) -> str:
    lines = []
    if event_id is not None:
        lines.append("id: {}".format(event_id))
    lines.append("event: {}".format(event_name))
    for line in json.dumps(data, separators=(",", ":"), sort_keys=True).splitlines():
        lines.append("data: {}".format(line))
    lines.append("")
    return "\n".join(lines) + "\n"


class EventStreamBroker:
    """In-memory fan-out for lightweight SSE subscriptions."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._subscribers: Dict[str, List[Queue]] = {}

    def subscribe(self, session_id: str) -> Queue:
        queue: Queue = Queue()
        with self._lock:
            self._subscribers.setdefault(session_id, []).append(queue)
        return queue

    def unsubscribe(self, session_id: str, queue: Queue) -> None:
        with self._lock:
            listeners = self._subscribers.get(session_id, [])
            if queue in listeners:
                listeners.remove(queue)
            if not listeners and session_id in self._subscribers:
                del self._subscribers[session_id]

    def publish(self, session_id: str, payload: str) -> None:
        with self._lock:
            listeners = list(self._subscribers.get(session_id, []))
        for queue in listeners:
            queue.put(payload)


class EventLogService:
    """Coordinate event appends, compact reads, digests, and SSE output."""

    def __init__(self, storage: RelayCoreStorage, broker: Optional[EventStreamBroker] = None) -> None:
        self.storage = storage
        self.broker = broker or EventStreamBroker()

    def append_event(
        self,
        *,
        session_id: str,
        agent_id: str,
        event_type: str,
        content: Dict[str, Any],
        runtime: Optional[str] = None,
        mode: Optional[str] = None,
        command_id: Optional[str] = None,
        parent_seq: Optional[int] = None,
        node_id: Optional[str] = None,
        trace_refs: Optional[List[Dict[str, Any]]] = None,
        artifact_refs: Optional[List[Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentEventRecord:
        event = self.storage.append_event(
            session_id=session_id,
            agent_id=agent_id,
            runtime=runtime,
            mode=mode,
            event_type=event_type,
            content=content,
            command_id=command_id,
            parent_seq=parent_seq,
            node_id=node_id,
            trace_refs=trace_refs,
            artifact_refs=artifact_refs,
            metadata=metadata,
        )
        self.broker.publish(
            session_id,
            format_sse("event", {"event": serialize_event(event)}, event_id=event.seq),
        )
        self.storage.append_audit_log(
            actor=agent_id,
            action="event_append",
            resource_type="agent_event",
            resource_id=str(event.seq),
            metadata=redact_structure(
                {
                    "session_id": session_id,
                    "event_type": event_type,
                    "command_id": command_id,
                    "content": content,
                    "metadata": metadata or {},
                }
            ),
        )
        digest = self.maybe_generate_digest(session_id)
        if digest is not None:
            self.broker.publish(
                session_id,
                format_sse("digest", {"digest": serialize_digest(digest)}, event_id=digest.to_seq),
            )
        return event

    def list_events(self, session_id: str, after_seq: Optional[int] = None, limit: int = 100) -> List[AgentEventRecord]:
        bounded_limit = max(1, min(limit, STREAM_BACKLOG_LIMIT))
        return self.storage.list_events(session_id, after_seq=after_seq, limit=bounded_limit)

    def maybe_generate_digest(self, session_id: str) -> Optional[SessionDigestRecord]:
        latest_digest = self.storage.get_latest_session_digest(session_id)
        next_from_seq = (latest_digest.to_seq + 1) if latest_digest is not None else 1
        pending_events = self.storage.list_events_window(session_id, next_from_seq, limit=DIGEST_BATCH_SIZE)
        if len(pending_events) < DIGEST_BATCH_SIZE:
            return None

        decisions: List[Dict[str, Any]] = []
        open_questions: List[Dict[str, Any]] = []
        rejected_candidates = []
        event_types = []
        artifact_refs: List[Any] = []
        trace_refs: List[Any] = []
        for event in pending_events:
            event_types.append(event.event_type)
            content = event.content
            trace_refs.extend(event.trace_refs or [])
            artifact_refs.extend(event.artifact_refs or [])
            if event.event_type.startswith("memory_") and isinstance(content, dict):
                candidate_id = content.get("candidate_id")
                if candidate_id:
                    decisions.append(
                        {
                            "candidate_id": candidate_id,
                            "node_id": content.get("node_id") or event.node_id,
                            "summary": content.get("summary") or content.get("action") or event.event_type,
                            "trace_refs": event.trace_refs,
                            "artifact_refs": event.artifact_refs,
                        }
                    )
                if content.get("action") in ("correct", "supersede") or content.get("conflicts_with"):
                    rejected_candidates.extend(content.get("conflicts_with", []))
                if event.event_type == "memory_review_required":
                    open_questions.append(
                        {
                            "node_id": event.node_id,
                            "question": "Resolve memory review for {}".format(candidate_id or "candidate"),
                            "trace_refs": event.trace_refs,
                        }
                    )
            questions = self._extract_open_questions(event)
            open_questions.extend(questions)

        summary = "Events {}-{}: {}".format(
            pending_events[0].seq,
            pending_events[-1].seq,
            ", ".join(event_types[:5]) + ("..." if len(event_types) > 5 else ""),
        )
        normalized_trace_refs = self._dedupe_json_items(trace_refs)
        normalized_artifact_refs = self._dedupe_json_items(artifact_refs)
        return self.storage.create_session_digest(
            digest_id="digest-{}".format(uuid4().hex[:12]),
            session_id=session_id,
            from_seq=pending_events[0].seq,
            to_seq=pending_events[-1].seq,
            summary=summary,
            decisions=decisions,
            open_questions=self._dedupe_json_items(open_questions),
            rejected_candidates=sorted(set(rejected_candidates)),
            node_id="digest-node-{}-{}".format(session_id, pending_events[-1].seq),
            trace_refs=normalized_trace_refs,
            artifact_refs=normalized_artifact_refs,
            task_canvas=self._build_task_canvas(pending_events),
        )

    def build_trace_bundle(
        self,
        *,
        trace_refs: Optional[List[Any]] = None,
        artifact_refs: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        normalized_trace_refs = self._dedupe_json_items(trace_refs or [])
        normalized_artifact_refs = self._dedupe_json_items(artifact_refs or [])
        evidence = []
        for trace_ref in normalized_trace_refs:
            event_seq = trace_ref.get("event_seq") if isinstance(trace_ref, dict) else None
            if event_seq is None:
                continue
            try:
                event = self.storage.get_event(int(event_seq))
            except Exception:
                continue
            evidence.append(serialize_event(event))

        artifacts = []
        for artifact_ref in normalized_artifact_refs:
            artifact_id = artifact_ref.get("artifact_id") if isinstance(artifact_ref, dict) else artifact_ref
            if not artifact_id:
                continue
            try:
                artifact = self.storage.get_artifact(str(artifact_id))
            except Exception:
                continue
            artifacts.append(asdict(artifact))
        return {
            "trace_refs": normalized_trace_refs,
            "artifact_refs": normalized_artifact_refs,
            "events": evidence,
            "artifacts": artifacts,
        }

    def stream_events(
        self,
        session_id: str,
        *,
        after_seq: Optional[int] = None,
        backlog_limit: int = 50,
        heartbeat: bool = True,
        poll_timeout: float = 15.0,
        max_live_messages: Optional[int] = None,
        max_heartbeats: Optional[int] = None,
    ) -> Generator[bytes, None, None]:
        backlog = self.list_events(session_id, after_seq=after_seq, limit=backlog_limit)
        for event in backlog:
            yield format_sse("event", {"event": serialize_event(event)}, event_id=event.seq).encode("utf-8")

        queue = self.broker.subscribe(session_id)
        live_messages = 0
        heartbeat_count = 0
        try:
            while True:
                try:
                    payload = queue.get(timeout=max(0.01, poll_timeout))
                    live_messages += 1
                    heartbeat_count = 0
                    yield payload.encode("utf-8")
                    if max_live_messages is not None and live_messages >= max_live_messages:
                        break
                except Empty:
                    if not heartbeat:
                        continue
                    heartbeat_count += 1
                    yield format_sse("heartbeat", {"session_id": session_id}).encode("utf-8")
                    if max_heartbeats is not None and heartbeat_count >= max_heartbeats:
                        break
        finally:
            self.broker.unsubscribe(session_id, queue)

    def _build_task_canvas(self, events: List[AgentEventRecord]) -> str:
        lines = ["graph TD"]
        for event in events:
            node_name = self._canvas_node_name(event.node_id)
            lines.append('{}["{} #{}"]'.format(node_name, event.event_type, event.seq))
            if event.parent_seq is not None:
                parent_name = self._canvas_node_name("event-{}".format(event.parent_seq))
                lines.append("{} --> {}".format(parent_name, node_name))
        return "\n".join(lines)

    def _extract_open_questions(self, event: AgentEventRecord) -> List[Dict[str, Any]]:
        content = event.content if isinstance(event.content, dict) else {}
        questions = []
        if "open_questions" in content and isinstance(content["open_questions"], list):
            for item in content["open_questions"]:
                questions.append(
                    {
                        "node_id": event.node_id,
                        "question": str(item),
                        "trace_refs": event.trace_refs,
                    }
                )
        summary = str(content.get("summary", "")).strip()
        if summary.endswith("?"):
            questions.append(
                {
                    "node_id": event.node_id,
                    "question": summary,
                    "trace_refs": event.trace_refs,
                }
            )
        return questions

    def _canvas_node_name(self, node_id: str) -> str:
        return re.sub(r"[^A-Za-z0-9_]", "_", node_id)

    def _dedupe_json_items(self, items: List[Any]) -> List[Any]:
        deduped: List[Any] = []
        seen = set()
        for item in items:
            key = json.dumps(item, sort_keys=True, separators=(",", ":"))
            if key in seen:
                continue
            deduped.append(item)
            seen.add(key)
        return deduped
