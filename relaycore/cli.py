"""RelayCore command-line entrypoints."""

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Optional

from werkzeug.serving import run_simple

from .migrations import initialize_database
from .server import create_app
from .single_db import SingleDBConstraintError, consolidate_legacy_database, enforce_single_runtime_db
from .storage import DEFAULT_DB_PATH, RelayCoreStorage, resolve_database_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RelayCore command-line interface.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-db", help="Initialize the SQLite database.")
    init_parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Database path.")

    serve_parser = subparsers.add_parser("serve", help="Run the Mission Control/API server.")
    serve_parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Database path.")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    serve_parser.add_argument("--port", type=int, default=8080, help="Bind port.")
    serve_parser.add_argument("--access-token", help="Optional access token override.")
    serve_parser.add_argument("--cors-origin", action="append", default=[], help="Allowed CORS origin. Repeatable.")
    serve_parser.add_argument("--backup-dir", help="Backup directory override.")

    mcp_http_parser = subparsers.add_parser(
        "mcp-http",
        help="Run the streamable HTTP MCP bridge for Codex/Claude-style runtimes.",
    )
    mcp_http_parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Database path.")
    mcp_http_parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    mcp_http_parser.add_argument("--port", type=int, default=9090, help="Bind port.")
    mcp_http_parser.add_argument("--path", default="/mcp", help="Streamable HTTP mount path.")
    mcp_http_parser.add_argument("--name", default="RelayCore", help="MCP server name.")

    export_parser = subparsers.add_parser("export", help="Export a redacted storage snapshot as JSON.")
    export_parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Database path.")
    export_parser.add_argument("--redact", action="store_true", default=False, help="Redact sensitive material in the export.")

    consolidate_parser = subparsers.add_parser(
        "consolidate-db",
        help="Merge legacy EchoMemory/RelayCore SQLite data into the canonical relaycore.db.",
    )
    consolidate_parser.add_argument("--source", default="echomemory.db", help="Legacy source database path.")
    consolidate_parser.add_argument("--target", default=str(DEFAULT_DB_PATH), help="Canonical RelayCore database path.")
    consolidate_parser.add_argument(
        "--keep-source",
        action="store_true",
        help="Keep the source database file instead of archiving it after a successful merge.",
    )

    return parser


def command_init_db(db_path: str) -> int:
    resolved = initialize_database(enforce_single_runtime_db(db_path))
    print("Initialized database at {}".format(resolved))
    return 0


def command_serve(
    *,
    db_path: str,
    host: str,
    port: int,
    access_token: Optional[str],
    cors_origins: list,
    backup_dir: Optional[str],
) -> int:
    resolved_db = initialize_database(enforce_single_runtime_db(db_path))
    app = create_app(
        db_path=str(resolved_db),
        access_token=access_token,
        cors_allowlist=cors_origins or None,
        backup_dir=backup_dir,
    )
    run_simple(
        hostname=host,
        port=port,
        application=app,
        use_reloader=False,
        use_debugger=False,
        threaded=True,
    )
    return 0


def command_export(db_path: str, *, redact: bool) -> int:
    storage = RelayCoreStorage(resolve_database_path(enforce_single_runtime_db(db_path)))
    try:
        snapshot = storage.export_snapshot(redact=redact)
        print(json.dumps(snapshot, ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    finally:
        storage.close()


def command_consolidate_db(*, source_path: str, target_path: str, keep_source: bool) -> int:
    report = consolidate_legacy_database(
        source_path=source_path,
        target_path=target_path,
        archive_source=not keep_source,
    )
    imported_summary = ", ".join(
        "{}={}".format(table, count)
        for table, count in sorted(report.imported_counts.items())
        if count
    ) or "no new rows imported"
    skipped_summary = ", ".join(
        "{}={}".format(table, count)
        for table, count in sorted(report.skipped_counts.items())
        if count
    ) or "no skipped rows"
    print("Consolidated legacy database into {}".format(report.target_path))
    print("Backup:", report.backup_path)
    print("Imported:", imported_summary)
    print("Skipped:", skipped_summary)
    if report.archive_path is not None:
        print("Archived source:", report.archive_path)
    else:
        print("Source kept at:", report.source_path)
    return 0


def command_mcp_http(
    *,
    db_path: str,
    host: str,
    port: int,
    path: str,
    name: str,
) -> int:
    if sys.version_info < (3, 10):
        major = sys.version_info[0]
        minor = sys.version_info[1]
        print(
            "relaycore mcp-http requires Python 3.10+ because the MCP SDK does not support Python {}.{}.".format(
                major,
                minor,
            )
        )
        print("Use a separate Python 3.10+ environment and install with: pip install -e .[mcp]")
        return 2

    try:
        from .mcp_http import main as mcp_http_main
    except ModuleNotFoundError as error:
        if error.name == "mcp":
            print("Missing optional dependency 'mcp'. Install it with: pip install -e .[mcp]")
            return 2
        raise

    argv = [
        "relaycore mcp-http",
        "--db",
        str(enforce_single_runtime_db(db_path)),
        "--host",
        host,
        "--port",
        str(port),
        "--path",
        path,
        "--name",
        name,
    ]
    original_argv = sys.argv
    try:
        sys.argv = argv
        return mcp_http_main()
    finally:
        sys.argv = original_argv


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "init-db":
            return command_init_db(args.db)
        if args.command == "serve":
            return command_serve(
                db_path=args.db,
                host=args.host,
                port=args.port,
                access_token=args.access_token or os.environ.get("RELAYCORE_ACCESS_TOKEN"),
                cors_origins=args.cors_origin,
                backup_dir=args.backup_dir,
            )
        if args.command == "mcp-http":
            return command_mcp_http(
                db_path=args.db,
                host=args.host,
                port=args.port,
                path=args.path,
                name=args.name,
            )
        if args.command == "export":
            return command_export(args.db, redact=args.redact)
        if args.command == "consolidate-db":
            return command_consolidate_db(
                source_path=args.source,
                target_path=args.target,
                keep_source=args.keep_source,
            )
    except SingleDBConstraintError as error:
        print(str(error))
        return 2
    raise ValueError("unsupported command {!r}".format(args.command))
