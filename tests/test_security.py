from pathlib import Path
import json
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from relaycore.server import create_app
from relaycore.storage import RelayCoreStorage
from relaycore.token_budget import TOKEN_REDACTION


@pytest.fixture
def secured_client(tmp_path: Path):
    storage = RelayCoreStorage(tmp_path / "security.db")
    storage.create_session(
        session_id="session-1",
        name="Security Session",
        goal="Protect admin surfaces",
        mode="assist",
        created_by="codex",
    )
    storage.append_event(
        session_id="session-1",
        agent_id="codex",
        event_type="proposal",
        content={"summary": "ready for stream"},
    )
    storage.create_command(
        command_id="cmd-security-1",
        session_id="session-1",
        mode="assist",
        command_type="review_patch",
        payload={"api_key": "sk-securitysecret", "path": "app.py"},
        created_by="codex",
        target_runtime="claude",
        permission_level="L1",
    )
    app = create_app(
        storage=storage,
        access_token="top-secret",
        cors_allowlist=["https://allowed.example"],
        backup_dir=str(tmp_path / "backups"),
    )
    app.testing = True
    try:
        yield app.test_client(), storage, tmp_path
    finally:
        storage.close()


def test_protected_routes_require_access_token_and_allow_authorized_access(secured_client) -> None:
    client, _, tmp_path = secured_client

    unauthorized = client.get("/metrics")
    assert unauthorized.status_code == 403

    metrics = client.get("/metrics", headers={"Authorization": "Bearer top-secret"})
    assert metrics.status_code == 200
    assert "relaycore_sessions_total 1" in metrics.data.decode("utf-8")

    exported = client.get("/api/export", headers={"X-RelayCore-Access-Token": "top-secret"})
    assert exported.status_code == 200
    command_dump = json.dumps(exported.get_json()["tables"]["commands"], sort_keys=True)
    assert TOKEN_REDACTION in command_dump
    assert "sk-securitysecret" not in command_dump

    backup_target = tmp_path / "snapshots" / "copy.db"
    backed_up = client.post(
        "/api/backup",
        headers={"X-RelayCore-Access-Token": "top-secret"},
        json={"target_path": str(backup_target)},
    )
    assert backed_up.status_code == 201
    assert Path(backed_up.get_json()["backup_path"]).exists()


def test_event_stream_requires_access_token(secured_client) -> None:
    client, _, _ = secured_client

    unauthorized = client.get("/api/events/stream", query_string={"session_id": "session-1"})
    assert unauthorized.status_code == 403

    authorized = client.get(
        "/api/events/stream",
        query_string={"session_id": "session-1"},
        headers={"Authorization": "Bearer top-secret"},
    )
    body = authorized.data.decode("utf-8")

    assert authorized.status_code == 200
    assert authorized.mimetype == "text/event-stream"
    assert "event: event" in body
    assert '"event_type":"proposal"' in body


def test_cors_preflight_allows_same_origin_and_explicit_allowlist(secured_client) -> None:
    client, _, _ = secured_client

    same_origin = client.options(
        "/api/export",
        base_url="http://localhost",
        headers={"Origin": "http://localhost", "Access-Control-Request-Method": "GET"},
    )
    assert same_origin.status_code == 204
    assert same_origin.headers["Access-Control-Allow-Origin"] == "http://localhost"

    allowlisted = client.options(
        "/api/export",
        headers={"Origin": "https://allowed.example", "Access-Control-Request-Method": "GET"},
    )
    assert allowlisted.status_code == 204
    assert allowlisted.headers["Access-Control-Allow-Origin"] == "https://allowed.example"
    assert "Authorization" in allowlisted.headers["Access-Control-Allow-Headers"]

    blocked = client.options(
        "/api/export",
        headers={"Origin": "https://blocked.example", "Access-Control-Request-Method": "GET"},
    )
    assert blocked.status_code == 403
    assert blocked.get_json()["error"] == "origin not allowed"


def test_create_app_respects_explicit_empty_cors_allowlist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RELAYCORE_CORS_ALLOWLIST", "https://env-allowed.example")
    storage = RelayCoreStorage(tmp_path / "empty-allowlist.db")
    storage.create_session(
        session_id="session-1",
        name="Empty Allowlist",
        goal="Honor constructor config",
        mode="assist",
        created_by="codex",
    )
    app = create_app(storage=storage, access_token="top-secret", cors_allowlist=[])
    app.testing = True

    try:
        response = app.test_client().options(
            "/api/export",
            headers={"Origin": "https://env-allowed.example", "Access-Control-Request-Method": "GET"},
        )
        assert response.status_code == 403
        assert response.get_json()["error"] == "origin not allowed"
    finally:
        storage.close()
