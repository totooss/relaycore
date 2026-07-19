from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from echomemory.storage import EchoMemoryStorage
from scripts.migrate_local_memories import MigrationOptions, collect_entries, migrate


def seed_home(home: Path) -> None:
    (home / ".codex").mkdir(parents=True, exist_ok=True)
    (home / ".claude/projects/project-a/memory").mkdir(parents=True, exist_ok=True)
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    (home / "Stock_review _system/WaveformTheory-Clean").mkdir(parents=True, exist_ok=True)

    (home / ".codex/zwapp-ui-migration-memory.md").write_text(
        "\n".join(
            [
                "# zwapp UI migration memory",
                "## 已确认目标",
                "- Use main-ios and main-android as the only visual source.",
                "- Keep real data bindings in place.",
                "## 当前阶段",
                "- Continue the full UI replacement.",
                "- Do not overstate completion.",
            ]
        )
    )
    (home / ".codex/session_index.jsonl").write_text(
        "\n".join(
            [
                '{"id":"1","thread_name":"推进 UI 迁移","updated_at":"2026-07-19T05:42:03.388581Z"}',
                '{"id":"2","thread_name":"继续补测试","updated_at":"2026-07-18T05:42:03.388581Z"}',
            ]
        )
        + "\n"
    )
    (home / ".claude/projects/project-a/memory/MEMORY.md").write_text(
        "\n".join(
            [
                "- [Autonomous continuation preference](a.md) — Keep advancing through planned tasks without pausing.",
                "- [Wait for explicit instruction](b.md) — Do not start operating until the user explicitly says 开始.",
            ]
        )
        + "\n"
    )
    (home / ".claude.json").write_text('{"theme":"auto"}\n')
    (home / ".codex/.codex-global-state.json").write_text('{"project-order":[]}\n')
    (home / ".claude/history.jsonl").write_text('{"display":"hello","sessionId":"1","timestamp":1}\n')
    (home / ".codex/history.jsonl").write_text('{"session_id":"1","text":"nihao","ts":1}\n')
    (home / "Stock_review _system/WaveformTheory-Clean/memory.md").write_text("API_KEY=sk-secretvalue\n")
    connection = sqlite3.connect(str(home / ".codex/memories_1.sqlite"))
    try:
        connection.execute(
            """
            CREATE TABLE stage1_outputs (
                thread_id TEXT PRIMARY KEY,
                source_updated_at INTEGER NOT NULL,
                raw_memory TEXT NOT NULL,
                rollout_summary TEXT NOT NULL,
                rollout_slug TEXT,
                generated_at INTEGER NOT NULL,
                usage_count INTEGER,
                last_usage INTEGER,
                selected_for_phase2 INTEGER NOT NULL DEFAULT 0,
                selected_for_phase2_source_updated_at INTEGER
            )
            """
        )
        connection.execute(
            """
            INSERT INTO stage1_outputs(
                thread_id, source_updated_at, raw_memory, rollout_summary, rollout_slug, generated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("thread-1", 1, "raw", "Use rollout summaries as compact migration candidates.", "rollout-a", 2),
        )
        connection.commit()
    finally:
        connection.close()


def test_collect_entries_classifies_sources_and_skips(tmp_path: Path) -> None:
    seed_home(tmp_path)

    entries, skips = collect_entries(tmp_path)

    titles = {entry.title for entry in entries}
    classifications = {skip.classification for skip in skips}

    assert "zwapp UI migration visual source" in titles
    assert "Recent Codex task themes" in titles
    assert "Autonomous continuation preference" in titles
    assert "Wait for explicit instruction" in titles
    assert "config_not_memory" in classifications
    assert "history_not_memory" in classifications
    assert "secret_only_content" in classifications
    assert "unsupported_runtime_store" in classifications


def test_collect_entries_can_opt_into_history_and_runtime_store(tmp_path: Path) -> None:
    seed_home(tmp_path)

    entries, skips = collect_entries(
        tmp_path,
        MigrationOptions(include_history=True, include_runtime_store=True),
    )

    titles = {entry.title for entry in entries}
    classifications = {skip.classification for skip in skips}

    assert "Recent Claude history themes" in titles
    assert "Recent Codex history themes" in titles
    assert "Codex runtime rollout rollout-a" in titles
    assert "history_not_memory" not in classifications
    assert "unsupported_runtime_store" not in classifications


def test_migrate_supports_dry_run_without_creating_database(tmp_path: Path) -> None:
    seed_home(tmp_path)
    db_path = tmp_path / "dry-run.db"

    report = migrate(
        db_path=db_path,
        session_id="dry-run-session",
        home_dir=tmp_path,
        dry_run=True,
    )

    assert report.dry_run is True
    assert report.imported_count == 0
    assert report.entries
    assert not db_path.exists()


def test_migrate_imports_entries_into_echomemory(tmp_path: Path) -> None:
    seed_home(tmp_path)
    db_path = tmp_path / "echomemory.db"

    report = migrate(
        db_path=db_path,
        session_id="import-session",
        home_dir=tmp_path,
        dry_run=False,
    )

    assert report.dry_run is False
    assert report.imported_count == len(report.entries)
    storage = EchoMemoryStorage(db_path)
    try:
        session = storage.get_session("import-session")
        assert session.metadata["last_commit_runtime"] == "codex"
        candidates = storage.list_memory_candidates(session_id="import-session", limit=50)
        assert len(candidates) == report.imported_count
        assert any(candidate.title == "Recent Codex task themes" for candidate in candidates)
    finally:
        storage.close()
