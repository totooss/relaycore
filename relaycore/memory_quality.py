"""Memory quality pipeline for normalized memory proposals."""

from dataclasses import dataclass
from difflib import SequenceMatcher
import hashlib
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

from .models import MemoryCandidateRecord
from .storage import MEMORY_LEVELS, RelayCoreStorage, utc_now

if TYPE_CHECKING:
    from .event_log import EventLogService

AUTO_MERGE_THRESHOLD = 0.92
REVIEW_THRESHOLD = 0.75
SUMMARY_LIMIT = 160
SUPPORTED_RELATION_HINTS = frozenset(("merge", "correct", "supersede"))
CONFLICT_SENSITIVE_TYPES = frozenset(("decision", "rule"))


def collapse_whitespace(value: str) -> str:
    return " ".join(value.strip().split())


def normalize_title(value: str) -> str:
    return collapse_whitespace(value)


def normalize_content(value: str) -> str:
    return collapse_whitespace(value)


def normalize_runtime(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = collapse_whitespace(value).lower()
    return normalized or None


def normalize_tags(tags: Optional[List[Any]]) -> List[str]:
    normalized_tags = []
    seen = set()
    for tag in tags or []:
        cleaned = collapse_whitespace(str(tag)).lower()
        if cleaned and cleaned not in seen:
            normalized_tags.append(cleaned)
            seen.add(cleaned)
    return normalized_tags


def normalize_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in (metadata or {}).items():
        cleaned_key = collapse_whitespace(str(key))
        if not cleaned_key:
            continue
        cleaned[cleaned_key] = value
    return cleaned


def normalize_trace_refs(trace_refs: Optional[List[Any]], *, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in trace_refs or []:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "session_id": item.get("session_id") or session_id,
                "event_seq": item.get("event_seq"),
                "candidate_id": item.get("candidate_id"),
                "artifact_id": item.get("artifact_id"),
                "source_location": collapse_whitespace(str(item.get("source_location") or "")).strip() or None,
            }
        )
    return normalized


def normalize_artifact_refs(artifact_refs: Optional[List[Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in artifact_refs or []:
        if isinstance(item, dict):
            artifact_id = item.get("artifact_id")
            if artifact_id:
                normalized.append({"artifact_id": str(artifact_id), "label": item.get("label")})
        elif item:
            normalized.append({"artifact_id": str(item), "label": None})
    return normalized


def normalize_memory_level(memory_level: Optional[str], memory_type: str) -> str:
    if memory_level:
        value = collapse_whitespace(memory_level).upper()
        if value in MEMORY_LEVELS:
            return value
    if memory_type in ("decision", "rule", "fact", "lesson"):
        return "L1"
    if memory_type in ("scenario", "workflow"):
        return "L2"
    return "L1"


def normalize_rejected(rejected: Optional[List[Any]]) -> List[str]:
    values = []
    for item in rejected or []:
        cleaned = collapse_whitespace(str(item))
        if cleaned:
            values.append(cleaned)
    return values


def summarize_content(content: str, limit: int = SUMMARY_LIMIT) -> str:
    content = collapse_whitespace(content)
    if len(content) <= limit:
        return content
    clipped = content[: limit - 3].rstrip()
    return clipped + "..."


def normalize_claim_text(value: str) -> str:
    value = re.sub(r"[^\w\s]+", " ", value.lower())
    return collapse_whitespace(value)


def content_hash(memory_type: str, title: str, content: str) -> str:
    digest_input = "{}\n{}\n{}".format(memory_type, normalize_claim_text(title), normalize_claim_text(content))
    return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()


def similarity_score(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_claim_text(left), normalize_claim_text(right)).ratio()


def token_jaccard(left: str, right: str) -> float:
    left_tokens = set(normalize_claim_text(left).split())
    right_tokens = set(normalize_claim_text(right).split())
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def combined_similarity(title_left: str, content_left: str, title_right: str, content_right: str) -> float:
    title_ratio = similarity_score(title_left, title_right)
    content_ratio = similarity_score(content_left, content_right)
    content_jaccard = token_jaccard(content_left, content_right)
    return (title_ratio * 0.35) + (content_ratio * 0.45) + (content_jaccard * 0.20)


def should_flag_conflict(
    memory_type: str,
    title: str,
    content: str,
    existing: MemoryCandidateRecord,
    score: float,
) -> bool:
    if memory_type not in CONFLICT_SENSITIVE_TYPES:
        return False
    if existing.status != "active":
        return False
    if existing.type != memory_type:
        return False
    title_ratio = similarity_score(title, existing.title)
    same_title = title_ratio >= 0.92
    content_ratio = similarity_score(content, existing.content)
    return same_title and content_ratio < AUTO_MERGE_THRESHOLD and score >= 0.55


@dataclass(frozen=True)
class NormalizedMemoryProposal:
    proposed_by: str
    type: str
    title: str
    content: str
    runtime: Optional[str]
    session_id: Optional[str]
    tags: List[str]
    rejected: List[str]
    summary: str
    metadata: Dict[str, Any]
    relation_hint: Optional[str]
    content_hash: str
    trace_refs: List[Dict[str, Any]]
    artifact_refs: List[Dict[str, Any]]
    memory_level: str


@dataclass(frozen=True)
class SimilarityMatch:
    candidate_id: str
    score: float
    status: str


@dataclass(frozen=True)
class MemoryProposalResult:
    candidate: MemoryCandidateRecord
    action: str
    confidence: float
    quality_score: float
    duplicate_of: Optional[str]
    similar_to: List[str]
    conflicts_with: List[str]
    cluster_id: str
    summary: str


class MemoryQualityService:
    """Apply normalization, dedupe, and conflict checks before persistence."""

    def __init__(self, storage: RelayCoreStorage, event_log: Optional["EventLogService"] = None) -> None:
        self.storage = storage
        self.event_log = event_log

    def normalize_proposal(
        self,
        *,
        proposed_by: str,
        type: str,
        title: str,
        content: str,
        runtime: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[List[Any]] = None,
        rejected: Optional[List[Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        relation_hint: Optional[str] = None,
        trace_refs: Optional[List[Any]] = None,
        artifact_refs: Optional[List[Any]] = None,
        memory_level: Optional[str] = None,
    ) -> NormalizedMemoryProposal:
        normalized_type = collapse_whitespace(type).lower()
        normalized_title = normalize_title(title)
        normalized_content = normalize_content(content)
        normalized_runtime = normalize_runtime(runtime)
        normalized_tags = normalize_tags(tags)
        normalized_rejected = normalize_rejected(rejected)
        normalized_metadata = normalize_metadata(metadata)
        normalized_trace_refs = normalize_trace_refs(trace_refs, session_id=session_id)
        normalized_artifact_refs = normalize_artifact_refs(artifact_refs)
        hint = collapse_whitespace(relation_hint).lower() if relation_hint else None
        if hint and hint not in SUPPORTED_RELATION_HINTS:
            hint = None
        normalized_level = normalize_memory_level(memory_level, normalized_type)
        summary = summarize_content(normalized_content)
        return NormalizedMemoryProposal(
            proposed_by=collapse_whitespace(proposed_by),
            type=normalized_type,
            title=normalized_title,
            content=normalized_content,
            runtime=normalized_runtime,
            session_id=session_id,
            tags=normalized_tags,
            rejected=normalized_rejected,
            summary=summary,
            metadata=normalized_metadata,
            relation_hint=hint,
            content_hash=content_hash(normalized_type, normalized_title, normalized_content),
            trace_refs=normalized_trace_refs,
            artifact_refs=normalized_artifact_refs,
            memory_level=normalized_level,
        )

    def list_relevant_candidates(self, proposal: NormalizedMemoryProposal) -> List[MemoryCandidateRecord]:
        candidates = self.storage.list_memory_candidates(limit=500)
        return [
            candidate
            for candidate in candidates
            if candidate.type == proposal.type and candidate.status not in ("archived", "rejected")
        ]

    def find_exact_duplicate(
        self,
        proposal: NormalizedMemoryProposal,
        candidates: List[MemoryCandidateRecord],
    ) -> Optional[MemoryCandidateRecord]:
        for candidate in candidates:
            existing_hash = content_hash(candidate.type, candidate.title, candidate.content)
            if existing_hash == proposal.content_hash:
                return candidate
        return None

    def find_similarity_matches(
        self,
        proposal: NormalizedMemoryProposal,
        candidates: List[MemoryCandidateRecord],
    ) -> List[SimilarityMatch]:
        matches = []
        for candidate in candidates:
            score = combined_similarity(proposal.title, proposal.content, candidate.title, candidate.content)
            if score >= REVIEW_THRESHOLD:
                matches.append(
                    SimilarityMatch(
                        candidate_id=candidate.candidate_id,
                        score=score,
                        status=candidate.status,
                    )
                )
        matches.sort(key=lambda match: match.score, reverse=True)
        return matches

    def detect_conflicts(
        self,
        proposal: NormalizedMemoryProposal,
        candidates: List[MemoryCandidateRecord],
    ) -> List[SimilarityMatch]:
        conflicts = []
        for candidate in candidates:
            score = combined_similarity(proposal.title, proposal.content, candidate.title, candidate.content)
            if should_flag_conflict(proposal.type, proposal.title, proposal.content, candidate, score):
                conflicts.append(
                    SimilarityMatch(
                        candidate_id=candidate.candidate_id,
                        score=score,
                        status=candidate.status,
                    )
                )
        conflicts.sort(key=lambda match: match.score, reverse=True)
        return conflicts

    def memory_propose(
        self,
        *,
        proposed_by: str,
        type: str,
        title: str,
        content: str,
        runtime: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[List[Any]] = None,
        rejected: Optional[List[Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        relation_hint: Optional[str] = None,
        candidate_id: Optional[str] = None,
        trace_refs: Optional[List[Any]] = None,
        artifact_refs: Optional[List[Any]] = None,
        memory_level: Optional[str] = None,
    ) -> MemoryProposalResult:
        proposal = self.normalize_proposal(
            proposed_by=proposed_by,
            type=type,
            title=title,
            content=content,
            runtime=runtime,
            session_id=session_id,
            tags=tags,
            rejected=rejected,
            metadata=metadata,
            relation_hint=relation_hint,
            trace_refs=trace_refs,
            artifact_refs=artifact_refs,
            memory_level=memory_level,
        )
        if proposal.memory_level == "L3" and not proposal.trace_refs:
            raise ValueError("L3 canonical memory requires trace_refs from L1 or L2 evidence")

        candidates = self.list_relevant_candidates(proposal)
        exact_duplicate = self.find_exact_duplicate(proposal, candidates)
        similarity_matches = self.find_similarity_matches(proposal, candidates)
        conflicts = self.detect_conflicts(proposal, candidates)

        if exact_duplicate is not None:
            return self._persist_merged_result(proposal, exact_duplicate, 1.0, candidate_id)

        if conflicts:
            return self._persist_review_result(
                proposal=proposal,
                action=proposal.relation_hint or "correct",
                similar_to=[match.candidate_id for match in similarity_matches[:3]],
                conflicts_with=[match.candidate_id for match in conflicts[:3]],
                confidence=min(0.94, conflicts[0].score),
                quality_score=0.6,
                candidate_id=candidate_id,
            )

        if similarity_matches and similarity_matches[0].score >= AUTO_MERGE_THRESHOLD:
            canonical = self.storage.get_memory_candidate(similarity_matches[0].candidate_id)
            return self._persist_merged_result(proposal, canonical, similarity_matches[0].score, candidate_id)

        if similarity_matches:
            return self._persist_review_result(
                proposal=proposal,
                action=proposal.relation_hint or "merge",
                similar_to=[match.candidate_id for match in similarity_matches[:3]],
                conflicts_with=[],
                confidence=similarity_matches[0].score,
                quality_score=max(0.55, similarity_matches[0].score),
                candidate_id=candidate_id,
            )

        return self._persist_new_candidate_result(proposal, candidate_id)

    def resolve_candidate(
        self,
        candidate_id: str,
        *,
        status: str,
        actor: str,
        runtime: Optional[str] = None,
        mode: Optional[str] = None,
        recommended_action: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryCandidateRecord:
        candidate = self.storage.get_memory_candidate(candidate_id)
        resolved = self.storage.resolve_memory_candidate(
            candidate_id,
            status,
            recommended_action=recommended_action,
        )
        self.storage.append_audit_log(
            actor=collapse_whitespace(actor),
            action="memory_candidate_resolve",
            resource_type="memory_candidate",
            resource_id=candidate_id,
            metadata=normalize_metadata(
                {
                    "from_status": candidate.status,
                    "to_status": resolved.status,
                    "recommended_action": recommended_action or resolved.recommended_action,
                    "runtime": runtime,
                    "mode": mode,
                    **(metadata or {}),
                }
            ),
        )
        if self.event_log is not None and resolved.session_id:
            event_type = "memory_conflict_resolved" if candidate.conflicts_with else "memory_resolved"
            self.event_log.append_event(
                session_id=resolved.session_id,
                agent_id=collapse_whitespace(actor),
                runtime=runtime,
                mode=mode,
                event_type=event_type,
                content={
                    "candidate_id": candidate_id,
                    "node_id": resolved.node_id,
                    "status": resolved.status,
                    "previous_status": candidate.status,
                    "recommended_action": resolved.recommended_action,
                    "conflicts_with": candidate.conflicts_with,
                },
                trace_refs=resolved.trace_refs,
                artifact_refs=resolved.artifact_refs,
                metadata={"source": "memory_quality", **normalize_metadata(metadata)},
            )
        if resolved.status in ("superseded", "rejected", "corrected"):
            self._record_rejected_knowledge(
                candidate=candidate,
                resolved=resolved,
                actor=collapse_whitespace(actor),
                runtime=runtime,
                mode=mode,
                metadata=metadata,
            )
        return resolved

    def promote_candidate(
        self,
        candidate_id: str,
        *,
        target_level: str,
        actor: str,
        runtime: Optional[str] = None,
        mode: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryCandidateRecord:
        candidate = self.storage.get_memory_candidate(candidate_id)
        normalized_target = normalize_memory_level(target_level, candidate.type)
        if normalized_target != "L3":
            raise ValueError("only promotion to L3 is supported in this phase")
        if candidate.memory_level not in ("L1", "L2"):
            raise ValueError("only L1 or L2 memory can be promoted to L3")
        if candidate.status != "active":
            raise ValueError("only active memory can be promoted to L3")
        if not candidate.trace_refs:
            raise ValueError("canonical promotion requires trace_refs")

        promoted = self.storage.update_memory_candidate(
            candidate_id,
            memory_level="L3",
            decision_status="accepted",
        )
        self.storage.append_audit_log(
            actor=collapse_whitespace(actor),
            action="memory_candidate_promote",
            resource_type="memory_candidate",
            resource_id=candidate_id,
            metadata=normalize_metadata(
                {
                    "from_level": candidate.memory_level,
                    "to_level": "L3",
                    "runtime": runtime,
                    "mode": mode,
                    **(metadata or {}),
                }
            ),
        )
        if self.event_log is not None and promoted.session_id:
            self.event_log.append_event(
                session_id=promoted.session_id,
                agent_id=collapse_whitespace(actor),
                runtime=runtime,
                mode=mode,
                event_type="memory_promoted",
                content={
                    "candidate_id": promoted.candidate_id,
                    "node_id": promoted.node_id,
                    "memory_level": promoted.memory_level,
                },
                trace_refs=promoted.trace_refs,
                artifact_refs=promoted.artifact_refs,
                metadata={"source": "memory_quality", **normalize_metadata(metadata)},
            )
        return promoted

    def _persist_merged_result(
        self,
        proposal: NormalizedMemoryProposal,
        canonical: MemoryCandidateRecord,
        confidence: float,
        candidate_id: Optional[str],
    ) -> MemoryProposalResult:
        created = self.storage.create_memory_candidate(
            candidate_id=candidate_id or self._generate_candidate_id(),
            proposed_by=proposal.proposed_by,
            runtime=proposal.runtime,
            session_id=proposal.session_id,
            type=proposal.type,
            title=proposal.title,
            content=proposal.content,
            summary="Duplicate of {}.".format(canonical.title),
            rejected=proposal.rejected,
            tags=proposal.tags,
            status="merged",
            similar_to=[canonical.candidate_id],
            conflicts_with=[],
            recommended_action="merge",
            node_id="memory-node-{}".format(candidate_id or uuid4().hex[:8]),
            trace_refs=proposal.trace_refs or canonical.trace_refs,
            artifact_refs=proposal.artifact_refs,
            memory_level=proposal.memory_level,
            decision_status="accepted",
            resolved_at=utc_now(),
        )
        self.storage.record_memory_occurrence(
            memory_id=canonical.candidate_id,
            agent_id=proposal.proposed_by,
            runtime=proposal.runtime,
            session_id=proposal.session_id,
            note="Merged duplicate proposal {}".format(created.candidate_id),
        )
        cluster = self._upsert_cluster(
            canonical_memory_id=canonical.candidate_id,
            summary=summarize_content(canonical.summary or canonical.content),
            tags=sorted(set(canonical.tags + proposal.tags)),
            quality_score=max(0.8, confidence),
            metadata={
                "action": "merge",
                "confidence": round(confidence, 3),
                "duplicate_of": canonical.candidate_id,
                "content_hash": proposal.content_hash,
            },
            increment_sources=True,
        )
        self.storage.append_audit_log(
            actor=proposal.proposed_by,
            action="memory_propose_merge",
            resource_type="memory_candidate",
            resource_id=created.candidate_id,
            metadata={"canonical_memory_id": canonical.candidate_id, "cluster_id": cluster.cluster_id},
        )
        self._append_memory_event(
            session_id=proposal.session_id,
            actor=proposal.proposed_by,
            runtime=proposal.runtime,
            event_type="memory_merged",
            content={
                "candidate_id": created.candidate_id,
                "node_id": created.node_id,
                "duplicate_of": canonical.candidate_id,
                "action": "merge",
                "confidence": round(confidence, 3),
            },
            trace_refs=created.trace_refs,
            artifact_refs=created.artifact_refs,
        )
        return MemoryProposalResult(
            candidate=created,
            action="merge",
            confidence=round(confidence, 3),
            quality_score=cluster.quality_score,
            duplicate_of=canonical.candidate_id,
            similar_to=[canonical.candidate_id],
            conflicts_with=[],
            cluster_id=cluster.cluster_id,
            summary=created.summary,
        )

    def _persist_review_result(
        self,
        *,
        proposal: NormalizedMemoryProposal,
        action: str,
        similar_to: List[str],
        conflicts_with: List[str],
        confidence: float,
        quality_score: float,
        candidate_id: Optional[str],
    ) -> MemoryProposalResult:
        created = self.storage.create_memory_candidate(
            candidate_id=candidate_id or self._generate_candidate_id(),
            proposed_by=proposal.proposed_by,
            runtime=proposal.runtime,
            session_id=proposal.session_id,
            type=proposal.type,
            title=proposal.title,
            content=proposal.content,
            summary=proposal.summary,
            rejected=proposal.rejected,
            tags=proposal.tags,
            status="pending",
            similar_to=similar_to,
            conflicts_with=conflicts_with,
            recommended_action=action,
            node_id="memory-node-{}".format(candidate_id or uuid4().hex[:8]),
            trace_refs=proposal.trace_refs,
            artifact_refs=proposal.artifact_refs,
            memory_level=proposal.memory_level,
            decision_status="candidate",
        )
        self.storage.record_memory_occurrence(
            memory_id=created.candidate_id,
            agent_id=proposal.proposed_by,
            runtime=proposal.runtime,
            session_id=proposal.session_id,
            note="Pending review proposal",
        )
        cluster = self._upsert_cluster(
            canonical_memory_id=created.candidate_id,
            summary=proposal.summary,
            tags=proposal.tags,
            quality_score=quality_score,
            metadata={
                "action": action,
                "confidence": round(confidence, 3),
                "similar_to": similar_to,
                "conflicts_with": conflicts_with,
                "content_hash": proposal.content_hash,
                "metadata": proposal.metadata,
            },
            increment_sources=False,
        )
        audit_action = "memory_propose_conflict" if conflicts_with else "memory_propose_review"
        self.storage.append_audit_log(
            actor=proposal.proposed_by,
            action=audit_action,
            resource_type="memory_candidate",
            resource_id=created.candidate_id,
            metadata={"cluster_id": cluster.cluster_id, "action": action},
        )
        self._append_memory_event(
            session_id=proposal.session_id,
            actor=proposal.proposed_by,
            runtime=proposal.runtime,
            event_type="memory_review_required",
            content={
                "candidate_id": created.candidate_id,
                "node_id": created.node_id,
                "action": action,
                "similar_to": similar_to,
                "conflicts_with": conflicts_with,
                "confidence": round(confidence, 3),
            },
            trace_refs=created.trace_refs,
            artifact_refs=created.artifact_refs,
        )
        return MemoryProposalResult(
            candidate=created,
            action=action,
            confidence=round(confidence, 3),
            quality_score=cluster.quality_score,
            duplicate_of=None,
            similar_to=similar_to,
            conflicts_with=conflicts_with,
            cluster_id=cluster.cluster_id,
            summary=created.summary,
        )

    def _persist_new_candidate_result(
        self,
        proposal: NormalizedMemoryProposal,
        candidate_id: Optional[str],
    ) -> MemoryProposalResult:
        created = self.storage.create_memory_candidate(
            candidate_id=candidate_id or self._generate_candidate_id(),
            proposed_by=proposal.proposed_by,
            runtime=proposal.runtime,
            session_id=proposal.session_id,
            type=proposal.type,
            title=proposal.title,
            content=proposal.content,
            summary=proposal.summary,
            rejected=proposal.rejected,
            tags=proposal.tags,
            status="pending",
            similar_to=[],
            conflicts_with=[],
            recommended_action=proposal.relation_hint or "create_new",
            node_id="memory-node-{}".format(candidate_id or uuid4().hex[:8]),
            trace_refs=proposal.trace_refs,
            artifact_refs=proposal.artifact_refs,
            memory_level=proposal.memory_level,
            decision_status="candidate",
        )
        self.storage.record_memory_occurrence(
            memory_id=created.candidate_id,
            agent_id=proposal.proposed_by,
            runtime=proposal.runtime,
            session_id=proposal.session_id,
            note="New candidate proposal",
        )
        cluster = self._upsert_cluster(
            canonical_memory_id=created.candidate_id,
            summary=proposal.summary,
            tags=proposal.tags,
            quality_score=0.72,
            metadata={
                "action": proposal.relation_hint or "create_new",
                "confidence": 0.72,
                "content_hash": proposal.content_hash,
                "metadata": proposal.metadata,
            },
            increment_sources=False,
        )
        self.storage.append_audit_log(
            actor=proposal.proposed_by,
            action="memory_propose_new",
            resource_type="memory_candidate",
            resource_id=created.candidate_id,
            metadata={"cluster_id": cluster.cluster_id},
        )
        self._append_memory_event(
            session_id=proposal.session_id,
            actor=proposal.proposed_by,
            runtime=proposal.runtime,
            event_type="memory_proposed",
            content={
                "candidate_id": created.candidate_id,
                "node_id": created.node_id,
                "action": proposal.relation_hint or "create_new",
                "confidence": 0.72,
            },
            trace_refs=created.trace_refs,
            artifact_refs=created.artifact_refs,
        )
        return MemoryProposalResult(
            candidate=created,
            action=proposal.relation_hint or "create_new",
            confidence=0.72,
            quality_score=cluster.quality_score,
            duplicate_of=None,
            similar_to=[],
            conflicts_with=[],
            cluster_id=cluster.cluster_id,
            summary=created.summary,
        )

    def _upsert_cluster(
        self,
        *,
        canonical_memory_id: str,
        summary: str,
        tags: List[str],
        quality_score: float,
        metadata: Dict[str, Any],
        increment_sources: bool,
    ):
        existing = self.storage.get_memory_cluster_by_canonical(canonical_memory_id)
        source_count = existing.source_count + 1 if existing and increment_sources else 1
        merged_tags = tags
        if existing:
            merged_tags = sorted(set(existing.tags + tags))
            source_count = existing.source_count + 1 if increment_sources else existing.source_count
        cluster_id = existing.cluster_id if existing else "cluster-{}".format(canonical_memory_id)
        merged_metadata = dict(existing.metadata) if existing else {}
        merged_metadata.update(metadata)
        return self.storage.upsert_memory_cluster(
            cluster_id=cluster_id,
            canonical_memory_id=canonical_memory_id,
            summary=summary,
            tags=merged_tags,
            source_count=max(1, source_count),
            quality_score=round(quality_score, 3),
            metadata=merged_metadata,
        )

    def _generate_candidate_id(self) -> str:
        return "mem-{}".format(uuid4().hex[:12])

    def _append_memory_event(
        self,
        *,
        session_id: Optional[str],
        actor: str,
        runtime: Optional[str],
        event_type: str,
        content: Dict[str, Any],
        trace_refs: Optional[List[Any]] = None,
        artifact_refs: Optional[List[Any]] = None,
    ) -> None:
        if self.event_log is None or not session_id:
            return
        self.event_log.append_event(
            session_id=session_id,
            agent_id=actor,
            runtime=runtime,
            event_type=event_type,
            content=content,
            trace_refs=trace_refs,
            artifact_refs=artifact_refs,
            metadata={"source": "memory_quality"},
        )

    def _record_rejected_knowledge(
        self,
        *,
        candidate: MemoryCandidateRecord,
        resolved: MemoryCandidateRecord,
        actor: str,
        runtime: Optional[str],
        mode: Optional[str],
        metadata: Optional[Dict[str, Any]],
    ) -> None:
        reason = ""
        if metadata and metadata.get("reason"):
            reason = collapse_whitespace(str(metadata["reason"]))
        if not reason:
            reason = resolved.recommended_action or resolved.status
        accepted_candidate_id = None
        if metadata and metadata.get("accepted_candidate_id"):
            accepted_candidate_id = str(metadata["accepted_candidate_id"])
        elif candidate.conflicts_with:
            accepted_candidate_id = str(candidate.conflicts_with[0])

        rejected = self.storage.create_rejected_knowledge(
            rejected_id="reject-{}".format(uuid4().hex[:12]),
            session_id=resolved.session_id,
            candidate_id=resolved.candidate_id,
            accepted_candidate_id=accepted_candidate_id,
            decision_type=resolved.type,
            reason=reason,
            trace_refs=resolved.trace_refs or candidate.trace_refs,
            artifact_refs=resolved.artifact_refs or candidate.artifact_refs,
            metadata=normalize_metadata(
                {
                    "previous_status": candidate.status,
                    "status": resolved.status,
                    "recommended_action": resolved.recommended_action,
                    "runtime": runtime,
                    "mode": mode,
                    **(metadata or {}),
                }
            ),
        )
        self.storage.append_audit_log(
            actor=actor,
            action="rejected_knowledge_recorded",
            resource_type="rejected_knowledge",
            resource_id=rejected.rejected_id,
            metadata={"candidate_id": resolved.candidate_id},
        )
        if self.event_log is not None and resolved.session_id:
            self.event_log.append_event(
                session_id=resolved.session_id,
                agent_id=actor,
                runtime=runtime,
                mode=mode,
                event_type="rejected_knowledge_recorded",
                content={
                    "candidate_id": resolved.candidate_id,
                    "rejected_id": rejected.rejected_id,
                    "accepted_candidate_id": accepted_candidate_id,
                    "reason": reason,
                },
                trace_refs=rejected.trace_refs,
                artifact_refs=rejected.artifact_refs,
                metadata={"source": "memory_quality"},
            )
