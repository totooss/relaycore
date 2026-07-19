from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from relaycore.cli import command_export, command_init_db


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
