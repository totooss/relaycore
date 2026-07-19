"""RelayCore command-line entrypoints."""

import argparse
import json
import os
from pathlib import Path
from typing import Optional

from werkzeug.serving import run_simple

from .migrations import initialize_database
from .server import create_app
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

    export_parser = subparsers.add_parser("export", help="Export a redacted storage snapshot as JSON.")
    export_parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Database path.")
    export_parser.add_argument("--redact", action="store_true", default=False, help="Redact sensitive material in the export.")

    return parser


def command_init_db(db_path: str) -> int:
    resolved = initialize_database(db_path)
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
    resolved_db = initialize_database(db_path)
    app = create_app(
        db_path=str(resolved_db),
        access_token=access_token,
        cors_allowlist=cors_origins or None,
        backup_dir=backup_dir,
    )
    run_simple(hostname=host, port=port, application=app, use_reloader=False, use_debugger=False)
    return 0


def command_export(db_path: str, *, redact: bool) -> int:
    storage = RelayCoreStorage(resolve_database_path(db_path))
    try:
        snapshot = storage.export_snapshot(redact=redact)
        print(json.dumps(snapshot, ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    finally:
        storage.close()


def main() -> int:
    args = build_parser().parse_args()
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
    if args.command == "export":
        return command_export(args.db, redact=args.redact)
    raise ValueError("unsupported command {!r}".format(args.command))
