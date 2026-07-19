from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from relaycore.memory_quality import MemoryQualityService, summarize_content
from relaycore.storage import RelayCoreStorage


@pytest.fixture
def storage(tmp_path: Path) -> RelayCoreStorage:
    repository = RelayCoreStorage(tmp_path / "memory-quality.db")
    try:
        yield repository
    finally:
        repository.close()


@pytest.fixture
def quality(storage: RelayCoreStorage) -> MemoryQualityService:
    return MemoryQualityService(storage)


def create_active_decision(storage: RelayCoreStorage) -> None:
    storage.create_memory_candidate(
        candidate_id="mem-active",
        proposed_by="codex",
        runtime="codex",
        session_id="session-1",
        type="decision",
        title="Primary Database",
        content="Use SQLite for the MVP control plane.",
        summary="Use SQLite for the MVP control plane.",
        tags=["storage"],
        status="active",
    )


def test_memory_propose_creates_normalized_candidate_and_cluster(quality: MemoryQualityService, storage: RelayCoreStorage) -> None:
    result = quality.memory_propose(
        proposed_by="codex",
        type=" Decision ",
        title="  Runtime   Contract  ",
        content="RelayCore should stay the only durable memory backend for this project.   " * 3,
        runtime=" CodeX ",
        tags=["Runtime", "runtime", " memory "],
        metadata={" owner ": "codex"},
    )

    assert result.action == "create_new"
    assert result.candidate.status == "pending"
    assert result.candidate.title == "Runtime Contract"
    assert result.candidate.tags == ["runtime", "memory"]
    assert len(result.summary) <= 160

    cluster = storage.get_memory_cluster(result.cluster_id)
    assert cluster.canonical_memory_id == result.candidate.candidate_id
    assert cluster.metadata["action"] == "create_new"


def test_exact_duplicate_is_merged_deterministically(quality: MemoryQualityService, storage: RelayCoreStorage) -> None:
    first = quality.memory_propose(
        proposed_by="codex",
        type="decision",
        title="Database Choice",
        content="Use SQLite for the MVP.",
        tags=["storage"],
    )

    duplicate = quality.memory_propose(
        proposed_by="claude",
        type="decision",
        title=" database choice ",
        content="Use   SQLite for the MVP.",
        tags=["storage", "db"],
    )

    assert first.candidate.status == "pending"
    assert duplicate.action == "merge"
    assert duplicate.candidate.status == "merged"
    assert duplicate.duplicate_of == first.candidate.candidate_id
    assert duplicate.summary.startswith("Duplicate of")

    cluster = storage.get_memory_cluster_by_canonical(first.candidate.candidate_id)
    assert cluster is not None
    assert cluster.source_count >= 2


def test_similar_memory_is_flagged_for_merge_review(quality: MemoryQualityService) -> None:
    quality.memory_propose(
        proposed_by="codex",
        type="decision",
        title="Storage Backend",
        content="Use SQLite as the local durable store for the MVP control plane.",
        tags=["storage"],
    )

    review = quality.memory_propose(
        proposed_by="claude",
        type="decision",
        title="Storage Backend",
        content="Use SQLite as the durable local storage layer for the MVP control plane.",
        tags=["storage", "review"],
    )

    assert review.candidate.status == "pending"
    assert review.action == "merge"
    assert review.similar_to
    assert not review.conflicts_with


def test_conflicting_active_decision_is_preserved_for_review(quality: MemoryQualityService) -> None:
    create_active_decision(quality.storage)

    result = quality.memory_propose(
        proposed_by="claude",
        type="decision",
        title="Primary Database",
        content="Use PostgreSQL for the MVP control plane.",
        relation_hint="supersede",
        tags=["storage"],
    )

    assert result.candidate.status == "pending"
    assert result.action == "supersede"
    assert result.conflicts_with == ["mem-active"]
    assert result.duplicate_of is None
    assert quality.storage.list_audit_logs(resource_type="memory_candidate")[0].action == "memory_propose_conflict"


def test_summary_helper_stays_compact() -> None:
    content = "a" * 300
    summary = summarize_content(content)
    assert len(summary) == 160
    assert summary.endswith("...")
