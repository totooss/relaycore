"""Runtime adapter helpers and collaboration-mode templates."""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = " ".join(str(value).strip().split())
    return cleaned or None


@dataclass(frozen=True)
class RuntimeContext:
    runtime: str
    agent_id: str
    session_id: Optional[str]
    mode: Optional[str]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class CollaborationModeTemplate:
    name: str
    summary: str
    description: str
    participants: List[str]
    workflow: List[str]
    command_defaults: Dict[str, Any]
    output_expectations: List[str]

    def to_payload(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeAdapter:
    runtime: str
    agent_prefix: str
    default_mode: str = "assist"

    def normalize_context(
        self,
        *,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        mode: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RuntimeContext:
        normalized_runtime = self.runtime
        normalized_agent_id = _clean(agent_id) or "{}-agent".format(self.agent_prefix)
        normalized_session_id = _clean(session_id)
        normalized_mode = _clean(mode) or self.default_mode
        return RuntimeContext(
            runtime=normalized_runtime,
            agent_id=normalized_agent_id,
            session_id=normalized_session_id,
            mode=normalized_mode,
            metadata=dict(metadata or {}),
        )


class RuntimeAdapterRegistry:
    """Keep one shared normalization path across supported runtimes."""

    def __init__(self) -> None:
        self._adapters = {
            "codex": RuntimeAdapter(runtime="codex", agent_prefix="codex"),
            "claude": RuntimeAdapter(runtime="claude", agent_prefix="claude"),
            "generic": RuntimeAdapter(runtime="generic", agent_prefix="generic"),
        }

    def get(self, runtime: Optional[str]) -> RuntimeAdapter:
        normalized = (_clean(runtime) or "generic").lower()
        return self._adapters.get(normalized, RuntimeAdapter(runtime=normalized, agent_prefix=normalized))

    def normalize(
        self,
        *,
        runtime: Optional[str],
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        mode: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RuntimeContext:
        adapter = self.get(runtime)
        return adapter.normalize_context(
            agent_id=agent_id,
            session_id=session_id,
            mode=mode,
            metadata=metadata,
        )


class CollaborationModeRegistry:
    """Shared structured collaboration modes across runtimes."""

    def __init__(self) -> None:
        self._templates: Dict[str, CollaborationModeTemplate] = {
            "assist": CollaborationModeTemplate(
                name="assist",
                summary="One agent leads and another unblocks with targeted support.",
                description="Use when one runtime owns implementation and another contributes scoped assistance.",
                participants=["lead", "assistant"],
                workflow=[
                    "Lead agent publishes the concrete task.",
                    "Assistant returns focused help, not a parallel rewrite.",
                    "Lead merges the result and commits the outcome.",
                ],
                command_defaults={"permission_level": "L1", "priority": 90, "command_type": "assist_task"},
                output_expectations=["compact answer", "single owner", "clear handoff"],
            ),
            "review": CollaborationModeTemplate(
                name="review",
                summary="One agent implements while another critiques risks and regressions.",
                description="Use when code or plans need structured review before acceptance.",
                participants=["implementer", "reviewer"],
                workflow=[
                    "Implementer publishes scope and current state.",
                    "Reviewer identifies bugs, risks, and test gaps.",
                    "Implementer resolves findings or records rejected changes.",
                ],
                command_defaults={"permission_level": "L1", "priority": 80, "command_type": "review_patch"},
                output_expectations=["findings first", "risk notes", "verification plan"],
            ),
            "adversarial": CollaborationModeTemplate(
                name="adversarial",
                summary="A challenger actively stresses a proposal to surface weak assumptions.",
                description="Use when the team wants a deliberate challenge pass before committing.",
                participants=["proposer", "challenger", "resolver"],
                workflow=[
                    "Proposer states the intended direction and supporting evidence.",
                    "Challenger attacks assumptions, edge cases, and hidden regressions.",
                    "Resolver updates the decision, preserves rejected options, and records why.",
                ],
                command_defaults={"permission_level": "L2", "priority": 60, "command_type": "challenge_plan"},
                output_expectations=["opposing arguments", "rejected options preserved", "resolution note"],
            ),
            "debate": CollaborationModeTemplate(
                name="debate",
                summary="Two agents compare competing approaches before selecting a direction.",
                description="Use when multiple credible options need a structured comparison.",
                participants=["side_a", "side_b", "moderator"],
                workflow=[
                    "Side A presents option A.",
                    "Side B presents option B.",
                    "Moderator extracts tradeoffs and names the preferred path.",
                ],
                command_defaults={"permission_level": "L2", "priority": 70, "command_type": "debate_options"},
                output_expectations=["tradeoff matrix", "decision summary", "losing option rationale"],
            ),
            "pipeline": CollaborationModeTemplate(
                name="pipeline",
                summary="Multiple agents work in ordered stages with explicit handoffs.",
                description="Use when a task should pass through sequential roles rather than shared free-form work.",
                participants=["stage_1", "stage_2", "stage_3"],
                workflow=[
                    "Stage 1 prepares context and artifacts.",
                    "Stage 2 transforms or reviews the output.",
                    "Stage 3 validates and closes the task.",
                ],
                command_defaults={"permission_level": "L1", "priority": 85, "command_type": "pipeline_stage"},
                output_expectations=["stage handoff", "artifact pointers", "validation status"],
            ),
        }

    def get(self, mode: Optional[str]) -> CollaborationModeTemplate:
        normalized = (_clean(mode) or "assist").lower()
        if normalized not in self._templates:
            raise ValueError("unsupported collaboration mode {!r}".format(normalized))
        return self._templates[normalized]

    def list(self) -> List[CollaborationModeTemplate]:
        return [self._templates[name] for name in ("assist", "review", "adversarial", "debate", "pipeline")]
