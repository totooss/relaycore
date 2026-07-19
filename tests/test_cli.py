from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from relaycore.cli import build_parser, command_export, command_init_db, command_mcp_http


def test_command_init_db_creates_database(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "relaycore.db"

    status = command_init_db(str(db_path))
    captured = capsys.readouterr()

    assert status == 0
    assert db_path.exists()
    assert "Initialized database" in captured.out


def test_command_export_prints_snapshot(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "relaycore.db"
    command_init_db(str(db_path))

    status = command_export(str(db_path), redact=True)
    captured = capsys.readouterr()

    assert status == 0
    assert '"tables"' in captured.out


def test_cli_parser_includes_mcp_http_command() -> None:
    args = build_parser().parse_args(["mcp-http", "--port", "9090"])
    assert args.command == "mcp-http"
    assert args.port == 9090


def test_command_mcp_http_requires_python_310_plus(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "version_info", (3, 9, 22))
    status = command_mcp_http(
        db_path=str(tmp_path / "relaycore.db"),
        host="127.0.0.1",
        port=9090,
        path="/mcp",
        name="RelayCore",
    )
    captured = capsys.readouterr()

    assert status == 2
    assert "requires Python 3.10+" in captured.out
