from pathlib import Path
import sqlite3

from relaycore.single_db import SingleDBConstraintError, consolidate_legacy_database, enforce_single_runtime_db
from relaycore.storage import RelayCoreStorage


def test_enforce_single_runtime_db_rejects_legacy_split(tmp_path: Path) -> None:
    canonical_path = tmp_path / "relaycore.db"
    legacy_path = tmp_path / "echomemory.db"

    canonical = RelayCoreStorage(canonical_path)
    canonical.close()

    legacy = RelayCoreStorage(legacy_path)
    try:
        legacy.create_session(
            session_id="legacy-session",
            name="Legacy Session",
            goal="Imported old memory",
            mode="assist",
            created_by="tester",
        )
        legacy.create_memory_candidate(
            candidate_id="legacy-memory-1",
            proposed_by="tester",
            runtime="codex",
            session_id="legacy-session",
            type="lesson",
            title="Legacy memory",
            content="This came from the legacy database.",
            status="active",
        )
    finally:
        legacy.close()

    try:
        enforce_single_runtime_db(canonical_path)
        raise AssertionError("expected single-db enforcement to reject the legacy split")
    except SingleDBConstraintError as error:
        message = str(error)
        assert "echomemory.db" in message
        assert "relaycore.db" in message


def test_consolidate_legacy_database_imports_memory_and_archives_source(tmp_path: Path) -> None:
    canonical_path = tmp_path / "relaycore.db"
    legacy_path = tmp_path / "echomemory.db"

    canonical = RelayCoreStorage(canonical_path)
    try:
        canonical.create_session(
            session_id="current-session",
            name="Current Session",
            goal="Current memory",
            mode="assist",
            created_by="tester",
        )
        canonical.create_memory_candidate(
            candidate_id="current-memory-1",
            proposed_by="tester",
            runtime="codex",
            session_id="current-session",
            type="rule",
            title="Current rule",
            content="Stay on the canonical database.",
            status="active",
        )
    finally:
        canonical.close()

    connection = sqlite3.connect(str(legacy_path))
    try:
        connection.executescript(
            """
            CREATE TABLE sessions (
              session_id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              goal TEXT NOT NULL,
              mode TEXT NOT NULL,
              status TEXT DEFAULT 'active',
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              metadata TEXT DEFAULT '{}'
            );
            CREATE TABLE session_digests (
              digest_id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              from_seq INTEGER NOT NULL,
              to_seq INTEGER NOT NULL,
              summary TEXT NOT NULL,
              decisions TEXT DEFAULT '[]',
              open_questions TEXT DEFAULT '[]',
              rejected_candidates TEXT DEFAULT '[]',
              created_at TEXT NOT NULL
            );
            CREATE TABLE memory_candidates (
              candidate_id TEXT PRIMARY KEY,
              proposed_by TEXT NOT NULL,
              runtime TEXT,
              session_id TEXT,
              type TEXT NOT NULL,
              title TEXT NOT NULL,
              content TEXT NOT NULL,
              summary TEXT DEFAULT '',
              rejected TEXT DEFAULT '[]',
              tags TEXT DEFAULT '[]',
              status TEXT DEFAULT 'pending',
              similar_to TEXT DEFAULT '[]',
              conflicts_with TEXT DEFAULT '[]',
              recommended_action TEXT DEFAULT '',
              created_at TEXT NOT NULL,
              resolved_at TEXT
            );
            CREATE TABLE memory_occurrences (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              memory_id TEXT NOT NULL,
              agent_id TEXT NOT NULL,
              runtime TEXT,
              session_id TEXT,
              observed_at TEXT NOT NULL,
              note TEXT DEFAULT ''
            );
            CREATE TABLE memory_clusters (
              cluster_id TEXT PRIMARY KEY,
              canonical_memory_id TEXT NOT NULL,
              summary TEXT NOT NULL,
              tags TEXT DEFAULT '[]',
              source_count INTEGER DEFAULT 1,
              quality_score REAL DEFAULT 0.5,
              updated_at TEXT NOT NULL,
              metadata TEXT DEFAULT '{}'
            );
            """
        )
        connection.execute(
            """
            INSERT INTO sessions (
              session_id, name, goal, mode, status, created_by, created_at, updated_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-session",
                "Legacy Session",
                "Imported old memory",
                "assist",
                "active",
                "tester",
                "2026-07-19T08:34:38+00:00",
                "2026-07-19T08:34:38+00:00",
                '{"source":"legacy"}',
            ),
        )
        connection.execute(
            """
            INSERT INTO session_digests (
              digest_id, session_id, from_seq, to_seq, summary, decisions, open_questions, rejected_candidates, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-digest-1",
                "legacy-session",
                1,
                10,
                "Imported 1 safe local memory entry.",
                '["Legacy memory"]',
                "[]",
                "[]",
                "2026-07-19T08:34:38+00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO memory_candidates (
              candidate_id, proposed_by, runtime, session_id, type, title, content, summary,
              rejected, tags, status, similar_to, conflicts_with, recommended_action, created_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-memory-1",
                "tester",
                "codex",
                "legacy-session",
                "lesson",
                "Legacy memory",
                "This came from the legacy database.",
                "This came from the legacy database.",
                "[]",
                '["migration"]',
                "active",
                "[]",
                "[]",
                "memory_add",
                "2026-07-19T08:34:38+00:00",
                "2026-07-19T08:34:38+00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO memory_occurrences (
              memory_id, agent_id, runtime, session_id, observed_at, note
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-memory-1",
                "tester",
                "codex",
                "legacy-session",
                "2026-07-19T08:34:38+00:00",
                "Imported from the legacy DB.",
            ),
        )
        connection.execute(
            """
            INSERT INTO memory_clusters (
              cluster_id, canonical_memory_id, summary, tags, source_count, quality_score, updated_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "cluster-legacy-memory-1",
                "legacy-memory-1",
                "Legacy memory cluster",
                '["migration"]',
                1,
                0.8,
                "2026-07-19T08:34:38+00:00",
                '{"source":"legacy"}',
            ),
        )
        connection.commit()
    finally:
        connection.close()

    report = consolidate_legacy_database(source_path=legacy_path, target_path=canonical_path)

    assert report.imported_counts["sessions"] == 1
    assert report.imported_counts["memory_candidates"] == 1
    assert report.imported_counts["memory_clusters"] == 1
    assert report.imported_counts["memory_occurrences"] == 1
    assert report.imported_counts["session_digests"] == 1
    assert report.archive_path is not None
    assert report.archive_path.exists()
    assert not legacy_path.exists()
    assert report.backup_path.exists()

    merged = RelayCoreStorage(canonical_path)
    try:
        sessions = {session.session_id for session in merged.list_sessions()}
        assert "current-session" in sessions
        assert "legacy-session" in sessions

        imported_candidate = merged.get_memory_candidate("legacy-memory-1")
        assert imported_candidate.memory_level == "L1"
        assert imported_candidate.decision_status == "accepted"
        assert imported_candidate.summary == "This came from the legacy database."

        digests = {digest.digest_id for digest in merged.list_session_digests("legacy-session", limit=10)}
        assert "legacy-digest-1" in digests
    finally:
        merged.close()
