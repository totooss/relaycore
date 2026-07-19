"""Append-only event log coordination and SSE formatting."""

from dataclasses import asdict
import json
from queue import Empty, Queue
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

        decisions = []
        rejected_candidates = []
        event_types = []
        for event in pending_events:
            event_types.append(event.event_type)
            content = event.content
            if event.event_type.startswith("memory_") and isinstance(content, dict):
                candidate_id = content.get("candidate_id")
                if candidate_id:
                    decisions.append(candidate_id)
                if content.get("action") in ("correct", "supersede") or content.get("conflicts_with"):
                    rejected_candidates.extend(content.get("conflicts_with", []))

        summary = "Events {}-{}: {}".format(
            pending_events[0].seq,
            pending_events[-1].seq,
            ", ".join(event_types[:5]) + ("..." if len(event_types) > 5 else ""),
        )
        return self.storage.create_session_digest(
            digest_id="digest-{}".format(uuid4().hex[:12]),
            session_id=session_id,
            from_seq=pending_events[0].seq,
            to_seq=pending_events[-1].seq,
            summary=summary,
            decisions=decisions,
            open_questions=[],
            rejected_candidates=sorted(set(rejected_candidates)),
        )

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
