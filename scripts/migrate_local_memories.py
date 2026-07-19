from __future__ import annotations

import argparse
import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from relaycore.mcp_server import RelayCoreMCPServer
from relaycore.storage import RelayCoreStorage
from relaycore.token_budget import SENSITIVE_VALUE_RE, TOKEN_REDACTION, redact_text


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "relaycore.db"
DEFAULT_SESSION_ID = "local-memory-migration-2026-07-19"
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)\b\S*(api[_-]?key|token|secret|password|passwd|access[_-]?token|refresh[_-]?token|private[_-]?key|client[_-]?secret)\S*\s*[:=]\s*\S+"
)


@dataclass(frozen=True)
class MemoryEntry:
    source: str
    adapter: str
    type: str
    title: str
    content: str
    tags: List[str]


@dataclass(frozen=True)
class SourceSkip:
    source: str
    classification: str
    detail: str


@dataclass(frozen=True)
class MigrationReport:
    session_id: str
    dry_run: bool
    db_path: str
    imported_count: int
    skipped_count: int
    entries: List[Dict[str, object]]
    skips: List[Dict[str, str]]


@dataclass(frozen=True)
class MigrationOptions:
    include_history: bool = False
    include_runtime_store: bool = False


class SourceAdapter:
    name = "source"

    def discover(self, home_dir: Path) -> Sequence[Path]:
        raise NotImplementedError

    def extract(self, path: Path) -> tuple[List[MemoryEntry], List[SourceSkip]]:
        raise NotImplementedError


class ClaudeProjectMemoryAdapter(SourceAdapter):
    name = "claude-project-memory"

    def discover(self, home_dir: Path) -> Sequence[Path]:
        return sorted((home_dir / ".claude/projects").glob("*/memory/MEMORY.md"))

    def extract(self, path: Path) -> tuple[List[MemoryEntry], List[SourceSkip]]:
        entries: List[MemoryEntry] = []
        for raw_line in path.read_text(errors="ignore").splitlines():
            line = raw_line.strip()
            if not line.startswith("- [") or " — " not in line:
                continue
            prefix, summary = line.split(" — ", 1)
            title = prefix.split("](", 1)[0][3:].strip()
            summary = redact_text(summary.strip())
            memory_type = classify_memory_type(title)
            entries.append(
                MemoryEntry(
                    source=str(path),
                    adapter=self.name,
                    type=memory_type,
                    title=title,
                    content=summary,
                    tags=["migration", "claude-memory", "claude-project"],
                )
            )
        return entries, []


class CodexMigrationNoteAdapter(SourceAdapter):
    name = "codex-migration-note"

    def discover(self, home_dir: Path) -> Sequence[Path]:
        path = home_dir / ".codex/zwapp-ui-migration-memory.md"
        return [path] if path.exists() else []

    def extract(self, path: Path) -> tuple[List[MemoryEntry], List[SourceSkip]]:
        text = path.read_text(errors="ignore")
        sections: Dict[str, List[str]] = {}
        current = None
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if line.startswith("## "):
                current = line[3:].strip()
                sections[current] = []
                continue
            if current and line.strip().startswith("- "):
                sections[current].append(redact_text(line.strip()[2:]))

        entries: List[MemoryEntry] = []
        goals = sections.get("已确认目标", [])
        if goals:
            entries.append(
                MemoryEntry(
                    source=str(path),
                    adapter=self.name,
                    type="decision",
                    title="zwapp UI migration visual source",
                    content="; ".join(goals[:4]),
                    tags=["migration", "codex-memory", "zwapp"],
                )
            )
        current_phase = sections.get("当前阶段", [])
        if current_phase:
            entries.append(
                MemoryEntry(
                    source=str(path),
                    adapter=self.name,
                    type="rule",
                    title="zwapp UI migration execution rule",
                    content="; ".join(current_phase[:3]),
                    tags=["migration", "codex-memory", "zwapp"],
                )
            )
        return entries, []


class CodexSessionIndexAdapter(SourceAdapter):
    name = "codex-session-index"

    def discover(self, home_dir: Path) -> Sequence[Path]:
        path = home_dir / ".codex/session_index.jsonl"
        return [path] if path.exists() else []

    def extract(self, path: Path) -> tuple[List[MemoryEntry], List[SourceSkip]]:
        titles = []
        for raw_line in path.read_text(errors="ignore").splitlines():
            if not raw_line.strip():
                continue
            row = json.loads(raw_line)
            title = redact_text(str(row.get("thread_name", "")).strip())
            updated_at = str(row.get("updated_at", "")).strip()
            if title:
                titles.append((updated_at, title))
        titles.sort(reverse=True)
        if not titles:
            return [], [SourceSkip(str(path), "empty_index", "No non-empty thread titles were found.")]
        summary = "; ".join("{}: {}".format(updated_at[:10], title) for updated_at, title in titles[:8])
        return [
            MemoryEntry(
                source=str(path),
                adapter=self.name,
                type="lesson",
                title="Recent Codex task themes",
                content=summary,
                tags=["migration", "codex-memory", "session-topics"],
            )
        ], []


class ClaudeHistoryAdapter(SourceAdapter):
    name = "claude-history"

    def discover(self, home_dir: Path) -> Sequence[Path]:
        path = home_dir / ".claude/history.jsonl"
        return [path] if path.exists() else []

    def extract(self, path: Path) -> tuple[List[MemoryEntry], List[SourceSkip]]:
        snippets = []
        for raw_line in path.read_text(errors="ignore").splitlines():
            if not raw_line.strip():
                continue
            row = json.loads(raw_line)
            text = compact_text(str(row.get("display", "")).strip())
            if text:
                snippets.append(text)
        snippets = dedupe_snippets(snippets)
        if not snippets:
            return [], [SourceSkip(str(path), "empty_history", "No usable Claude history snippets were found.")]
        return [
            MemoryEntry(
                source=str(path),
                adapter=self.name,
                type="lesson",
                title="Recent Claude history themes",
                content="; ".join(snippets[:8]),
                tags=["migration", "claude-history", "session-topics"],
            )
        ], []


class CodexHistoryAdapter(SourceAdapter):
    name = "codex-history"

    def discover(self, home_dir: Path) -> Sequence[Path]:
        path = home_dir / ".codex/history.jsonl"
        return [path] if path.exists() else []

    def extract(self, path: Path) -> tuple[List[MemoryEntry], List[SourceSkip]]:
        snippets = []
        for raw_line in path.read_text(errors="ignore").splitlines():
            if not raw_line.strip():
                continue
            row = json.loads(raw_line)
            text = compact_text(str(row.get("text", "")).strip())
            if text:
                snippets.append(text)
        snippets = dedupe_snippets(snippets)
        if not snippets:
            return [], [SourceSkip(str(path), "empty_history", "No usable Codex history snippets were found.")]
        return [
            MemoryEntry(
                source=str(path),
                adapter=self.name,
                type="lesson",
                title="Recent Codex history themes",
                content="; ".join(snippets[:8]),
                tags=["migration", "codex-history", "session-topics"],
            )
        ], []


class CodexRuntimeStoreAdapter(SourceAdapter):
    name = "codex-runtime-store"

    def discover(self, home_dir: Path) -> Sequence[Path]:
        path = home_dir / ".codex/memories_1.sqlite"
        return [path] if path.exists() else []

    def extract(self, path: Path) -> tuple[List[MemoryEntry], List[SourceSkip]]:
        connection = sqlite3.connect(str(path))
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                """
                SELECT thread_id, rollout_summary, rollout_slug
                FROM stage1_outputs
                ORDER BY generated_at DESC
                LIMIT 8
                """
            ).fetchall()
        finally:
            connection.close()
        if not rows:
            return [], [SourceSkip(str(path), "empty_runtime_store", "No stage1 runtime memory rows were found.")]

        entries = []
        for row in rows:
            summary = compact_text(redact_text(str(row["rollout_summary"] or "")))
            if not summary:
                continue
            entries.append(
                MemoryEntry(
                    source=str(path),
                    adapter=self.name,
                    type="lesson",
                    title="Codex runtime rollout {}".format(row["rollout_slug"] or row["thread_id"]),
                    content=summary,
                    tags=["migration", "codex-runtime-store", "rollout-memory"],
                )
            )
        if not entries:
            return [], [SourceSkip(str(path), "empty_runtime_store", "Runtime store rows existed but did not contain usable summaries.")]
        return entries, []


def classify_memory_type(title: str) -> str:
    text = title.lower()
    if any(token in text for token in ("mode", "control", "wait", "pause", "boundary", "instruction", "scope")):
        return "rule"
    if any(token in text for token in ("decision", "source", "contract")):
        return "decision"
    return "lesson"


def compact_text(value: str, limit: int = 160) -> str:
    text = " ".join(redact_text(value).split())
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def dedupe_snippets(snippets: Sequence[str]) -> List[str]:
    values = []
    seen = set()
    for snippet in snippets:
        if snippet in seen:
            continue
        seen.add(snippet)
        values.append(snippet)
    return values


def detect_secret_only_file(path: Path) -> bool:
    text = path.read_text(errors="ignore").strip()
    if not text:
        return False
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines and all(SENSITIVE_ASSIGNMENT_RE.search(line) for line in lines):
        return True
    if SENSITIVE_VALUE_RE.search(text) or SENSITIVE_ASSIGNMENT_RE.search(text):
        stripped = SENSITIVE_VALUE_RE.sub("", text)
        stripped = SENSITIVE_ASSIGNMENT_RE.sub("", stripped)
        stripped = re.sub(r"[\s:=_-]+", "", stripped)
        return len(stripped) < 32
    return False


def inspect_known_skips(home_dir: Path, options: MigrationOptions) -> List[SourceSkip]:
    skips: List[SourceSkip] = []

    config_paths = [
        home_dir / ".claude.json",
        home_dir / ".codex/.codex-global-state.json",
        home_dir / ".claude/config.json",
        home_dir / ".claude/settings.json",
    ]
    for path in config_paths:
        if path.exists():
            skips.append(SourceSkip(str(path), "config_not_memory", "Configuration/state file excluded from migration."))

    if not options.include_history:
        history_paths = [
            home_dir / ".claude/history.jsonl",
            home_dir / ".codex/history.jsonl",
        ]
        for path in history_paths:
            if path.exists():
                skips.append(SourceSkip(str(path), "history_not_memory", "Conversation history is not imported as durable memory by default."))

    secret_candidate = home_dir / "Stock_review _system/WaveformTheory-Clean/memory.md"
    if secret_candidate.exists():
        if detect_secret_only_file(secret_candidate):
            skips.append(SourceSkip(str(secret_candidate), "secret_only_content", "File appears to contain secret material instead of durable memory."))
        else:
            text = secret_candidate.read_text(errors="ignore")
            if (
                TOKEN_REDACTION in redact_text(text)
                or SENSITIVE_VALUE_RE.search(text)
                or SENSITIVE_ASSIGNMENT_RE.search(text)
            ):
                skips.append(SourceSkip(str(secret_candidate), "contains_secret", "File contains mixed content with sensitive material and was not auto-imported."))

    codex_memory_db = home_dir / ".codex/memories_1.sqlite"
    if codex_memory_db.exists() and not options.include_runtime_store:
        skips.append(SourceSkip(str(codex_memory_db), "unsupported_runtime_store", "Runtime-managed SQLite store is not imported directly by this script."))

    return skips


def build_adapters(options: MigrationOptions) -> List[SourceAdapter]:
    adapters: List[SourceAdapter] = [
        CodexMigrationNoteAdapter(),
        CodexSessionIndexAdapter(),
        ClaudeProjectMemoryAdapter(),
    ]
    if options.include_history:
        adapters.extend([ClaudeHistoryAdapter(), CodexHistoryAdapter()])
    if options.include_runtime_store:
        adapters.append(CodexRuntimeStoreAdapter())
    return adapters


def collect_entries(home_dir: Path, options: MigrationOptions | None = None) -> tuple[List[MemoryEntry], List[SourceSkip]]:
    options = options or MigrationOptions()
    entries: List[MemoryEntry] = []
    skips = inspect_known_skips(home_dir, options)

    for adapter in build_adapters(options):
        for path in adapter.discover(home_dir):
            try:
                extracted, adapter_skips = adapter.extract(path)
            except Exception as error:
                skips.append(SourceSkip(str(path), "parse_error", "{}: {}".format(type(error).__name__, error)))
                continue
            entries.extend(extracted)
            skips.extend(adapter_skips)

    return dedupe_entries(entries), skips


def dedupe_entries(entries: Iterable[MemoryEntry]) -> List[MemoryEntry]:
    deduped: List[MemoryEntry] = []
    seen = set()
    for entry in entries:
        key = (entry.type, entry.title, entry.content)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def build_report(
    *,
    session_id: str,
    db_path: Path,
    dry_run: bool,
    entries: List[MemoryEntry],
    skips: List[SourceSkip],
    imported_count: int,
) -> MigrationReport:
    return MigrationReport(
        session_id=session_id,
        dry_run=dry_run,
        db_path=str(db_path),
        imported_count=imported_count,
        skipped_count=len(skips),
        entries=[
            {
                "source": entry.source,
                "adapter": entry.adapter,
                "type": entry.type,
                "title": entry.title,
                "tags": entry.tags,
            }
            for entry in entries
        ],
        skips=[asdict(skip) for skip in skips],
    )


def write_report(report: MigrationReport, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(asdict(report), ensure_ascii=True, indent=2, sort_keys=True) + "\n")


def print_report(report: MigrationReport) -> None:
    mode = "Dry run" if report.dry_run else "Imported"
    print("{} {} entries into {}".format(mode, report.imported_count, report.db_path))
    print("Session:", report.session_id)
    print("Skipped sources:", report.skipped_count)
    print("Entries:")
    for entry in report.entries:
        print("  - [{}] {} ({})".format(entry["type"], entry["title"], entry["adapter"]))
    if report.skips:
        print("Skipped:")
        for skip in report.skips:
            print("  - {} [{}] {}".format(skip["source"], skip["classification"], skip["detail"]))


def migrate(
    *,
    db_path: Path,
    session_id: str,
    home_dir: Path,
    dry_run: bool = False,
    options: MigrationOptions | None = None,
) -> MigrationReport:
    options = options or MigrationOptions()
    entries, skips = collect_entries(home_dir, options)
    if dry_run or not entries:
        return build_report(
            session_id=session_id,
            db_path=db_path,
            dry_run=dry_run,
            entries=entries,
            skips=skips,
            imported_count=0 if dry_run else len(entries),
        )

    storage = RelayCoreStorage(db_path)
    server = RelayCoreMCPServer(storage=storage)
    try:
        server.call_tool(
            "memory_begin_task",
            {
                "session_id": session_id,
                "runtime": "codex",
                "agent_id": "codex-memory-migrator",
                "name": "Local Memory Migration",
                "goal": "Import safe local Claude/Codex memory into RelayCore",
                "metadata": {"source": "local-memory-migration-script"},
            },
        )
        imported = 0
        for entry in entries:
            server.call_tool(
                "memory_add",
                {
                    "session_id": session_id,
                    "runtime": "codex",
                    "agent_id": "codex-memory-migrator",
                    "type": entry.type,
                    "title": entry.title,
                    "content": "{}\n\nSource: {}".format(entry.content, entry.source),
                    "tags": entry.tags,
                },
            )
            imported += 1

        server.call_tool(
            "memory_commit_task",
            {
                "session_id": session_id,
                "runtime": "codex",
                "agent_id": "codex-memory-migrator",
                "summary": "Imported {} safe local memory entries.".format(imported),
                "decisions": [entry.title for entry in entries if entry.type == "decision"],
                "rejected_candidates": [skip.source for skip in skips],
            },
        )
        return build_report(
            session_id=session_id,
            db_path=db_path,
            dry_run=False,
            entries=entries,
            skips=skips,
            imported_count=imported,
        )
    finally:
        storage.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migrate safe local Claude/Codex memories into RelayCore.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Target RelayCore SQLite path.")
    parser.add_argument("--session-id", default=DEFAULT_SESSION_ID, help="Target RelayCore session id.")
    parser.add_argument("--home", default=str(Path.home()), help="Home directory to scan for Claude/Codex memory sources.")
    parser.add_argument("--dry-run", action="store_true", help="Inspect and report importable memories without writing to RelayCore.")
    parser.add_argument("--include-history", action="store_true", help="Include summarized Claude/Codex history as importable memory.")
    parser.add_argument("--include-runtime-store", action="store_true", help="Include supported Codex runtime store summaries when present.")
    parser.add_argument("--report", help="Optional JSON report path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = migrate(
        db_path=Path(args.db).expanduser(),
        session_id=args.session_id,
        home_dir=Path(args.home).expanduser(),
        dry_run=args.dry_run,
        options=MigrationOptions(
            include_history=args.include_history,
            include_runtime_store=args.include_runtime_store,
        ),
    )
    if args.report:
        write_report(report, Path(args.report).expanduser())
    print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
