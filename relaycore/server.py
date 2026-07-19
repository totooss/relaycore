"""Lightweight REST API server for RelayCore command bus operations."""

from dataclasses import asdict
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .command_bus import (
    BadRequestError,
    CommandBusService,
    ConflictError,
    PermissionDeniedError,
    serialize_command,
)
from .event_log import EventLogService, serialize_digest, serialize_event
from .memory_quality import MemoryQualityService
from .web_ui import MissionControlUI
from .storage import RelayCoreStorage, NotFoundError, StorageError
from .token_budget import estimate_payload_tokens
from werkzeug.exceptions import HTTPException, MethodNotAllowed, NotFound
from werkzeug.routing import Map, Rule
from werkzeug.test import Client
from werkzeug.wrappers import Request, Response


def create_app(
    *,
    db_path: Optional[str] = None,
    storage: Optional[RelayCoreStorage] = None,
    command_bus: Optional[CommandBusService] = None,
    event_log: Optional[EventLogService] = None,
    memory_quality: Optional[MemoryQualityService] = None,
    access_token: Optional[str] = None,
    cors_allowlist: Optional[list] = None,
    backup_dir: Optional[str] = None,
) -> "RelayCoreAPI":
    repository = storage
    if repository is None:
        if command_bus is not None:
            repository = command_bus.storage
        elif event_log is not None:
            repository = event_log.storage
        elif memory_quality is not None:
            repository = memory_quality.storage
        else:
            repository = RelayCoreStorage(db_path)

    event_service = event_log or EventLogService(repository)
    command_service = command_bus or CommandBusService(repository, event_log=event_service)
    if command_service.event_log is None:
        command_service.event_log = event_service
    memory_service = memory_quality or MemoryQualityService(repository, event_log=event_service)
    if memory_service.event_log is None:
        memory_service.event_log = event_service

    web_ui = MissionControlUI(repository, command_service, event_service, memory_service)
    resolved_allowlist = (
        cors_allowlist
        if cors_allowlist is not None
        else _split_env_list(os.environ.get("RELAYCORE_CORS_ALLOWLIST"))
    )
    resolved_token = access_token if access_token is not None else os.environ.get("RELAYCORE_ACCESS_TOKEN")
    resolved_backup_dir = backup_dir or os.environ.get("RELAYCORE_BACKUP_DIR")
    return RelayCoreAPI(
        command_service,
        event_service,
        memory_service,
        web_ui,
        storage=repository,
        access_token=resolved_token,
        cors_allowlist=resolved_allowlist,
        backup_dir=resolved_backup_dir,
    )


class RelayCoreAPI:
    """A tiny WSGI app for the command-bus REST surface."""

    def __init__(
        self,
        command_bus: CommandBusService,
        event_log: EventLogService,
        memory_quality: MemoryQualityService,
        web_ui: MissionControlUI,
        storage: RelayCoreStorage,
        access_token: Optional[str] = None,
        cors_allowlist: Optional[list] = None,
        backup_dir: Optional[str] = None,
    ) -> None:
        self.command_bus = command_bus
        self.event_log = event_log
        self.memory_quality = memory_quality
        self.web_ui = web_ui
        self.storage = storage
        self.access_token = access_token
        self.cors_allowlist = cors_allowlist or []
        self.backup_dir = Path(backup_dir).expanduser() if backup_dir else self.storage.db_path.parent / "backups"
        self.testing = False
        self.url_map = Map(
            [
                Rule("/", methods=["GET"], endpoint="mission_control"),
                Rule("/mission-control", methods=["GET"], endpoint="mission_control"),
                Rule("/mission-control/memories", methods=["GET"], endpoint="memory_view"),
                Rule("/mission-control/commands", methods=["POST"], endpoint="mission_control_publish"),
                Rule(
                    "/mission-control/memory-candidates/resolve",
                    methods=["POST"],
                    endpoint="mission_control_resolve_candidate",
                ),
                Rule("/api/commands", methods=["POST"], endpoint="publish_command"),
                Rule("/api/commands/pending", methods=["GET"], endpoint="list_pending_commands"),
                Rule("/api/commands/<command_id>/claim", methods=["POST"], endpoint="claim_command"),
                Rule("/api/commands/<command_id>/complete", methods=["POST"], endpoint="complete_command"),
                Rule("/api/commands/<command_id>/fail", methods=["POST"], endpoint="fail_command"),
                Rule("/api/events", methods=["POST"], endpoint="append_event"),
                Rule("/api/events", methods=["GET"], endpoint="list_events"),
                Rule("/api/events/stream", methods=["GET"], endpoint="stream_events"),
                Rule(
                    "/api/memory-candidates/<candidate_id>/resolve",
                    methods=["POST"],
                    endpoint="resolve_memory_candidate",
                ),
                Rule("/api/export", methods=["GET"], endpoint="export_snapshot"),
                Rule("/api/backup", methods=["POST"], endpoint="backup_database"),
                Rule("/metrics", methods=["GET"], endpoint="metrics"),
            ]
        )

    def __call__(self, environ: Dict[str, Any], start_response: Any) -> Any:
        request = Request(environ)
        if request.method == "OPTIONS":
            response = self._handle_options(request)
        else:
            response = self._dispatch_request(request)
        response = self._apply_cors(request, response)
        return response(environ, start_response)

    def test_client(self) -> Client:
        return Client(self, Response)

    def _dispatch_request(self, request: Request) -> Response:
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            handler = getattr(self, "_{}".format(endpoint))
            return handler(request, **values)
        except BadRequestError as error:
            return self._json_response({"error": str(error)}, 400)
        except PermissionDeniedError as error:
            return self._json_response({"error": str(error)}, 403)
        except NotFoundError as error:
            return self._json_response({"error": str(error)}, 404)
        except ConflictError as error:
            return self._json_response({"error": str(error)}, 409)
        except StorageError as error:
            return self._json_response({"error": str(error)}, 400)
        except (NotFound, MethodNotAllowed, HTTPException) as error:
            return self._json_response({"error": error.description}, getattr(error, "code", 500))

    def _mission_control(self, request: Request) -> Response:
        html = self.web_ui.render_dashboard(
            session_id=request.args.get("session_id"),
            lang=request.args.get("lang"),
        )
        return Response(html, status=200, mimetype="text/html")

    def _memory_view(self, request: Request) -> Response:
        html = self.web_ui.render_memory_page(
            session_id=request.args.get("session_id"),
            status=request.args.get("status"),
            memory_type=request.args.get("type"),
            query=request.args.get("q"),
            lang=request.args.get("lang"),
        )
        return Response(html, status=200, mimetype="text/html")

    def _mission_control_publish(self, request: Request) -> Response:
        form = request.form.to_dict()
        session_id = form.get("session_id")
        lang = form.get("lang")
        try:
            flash = self.web_ui.handle_command_form(form, lang=lang)
            html = self.web_ui.render_dashboard(session_id=session_id, flash=flash, lang=lang)
            return Response(html, status=200, mimetype="text/html")
        except ValueError as error:
            html = self.web_ui.render_dashboard(session_id=session_id, error=str(error), lang=lang)
            return Response(html, status=400, mimetype="text/html")

    def _mission_control_resolve_candidate(self, request: Request) -> Response:
        form = request.form.to_dict()
        session_id = form.get("session_id")
        lang = form.get("lang")
        try:
            flash = self.web_ui.handle_conflict_form(form, lang=lang)
            html = self.web_ui.render_dashboard(session_id=session_id, flash=flash, lang=lang)
            return Response(html, status=200, mimetype="text/html")
        except ValueError as error:
            html = self.web_ui.render_dashboard(session_id=session_id, error=str(error), lang=lang)
            return Response(html, status=400, mimetype="text/html")

    def _publish_command(self, request: Request) -> Response:
        payload = self._json_body(request)
        existing = None
        if payload.get("idempotency_key"):
            existing = self.command_bus.find_command_by_idempotency_key(payload["idempotency_key"])
        command = self.command_bus.publish_command(
            session_id=payload["session_id"],
            mode=payload["mode"],
            command_type=payload["command_type"],
            payload=payload["payload"],
            created_by=payload["created_by"],
            target_agent=payload.get("target_agent"),
            target_runtime=payload.get("target_runtime"),
            priority=payload.get("priority", 100),
            permission_level=payload.get("permission_level", "L1"),
            idempotency_key=payload.get("idempotency_key"),
        )
        status_code = 200 if existing is not None else 201
        return self._json_response({"command": serialize_command(command)}, status_code)

    def _list_pending_commands(self, request: Request) -> Response:
        commands = self.command_bus.list_pending_commands(
            requester_permission_level=request.args.get("requester_permission_level", "L1"),
            session_id=request.args.get("session_id"),
            target_runtime=request.args.get("target_runtime"),
            target_agent=request.args.get("target_agent"),
            limit=int(request.args.get("limit", 50)),
        )
        return self._json_response({"commands": [serialize_command(command) for command in commands]}, 200)

    def _claim_command(self, request: Request, command_id: str) -> Response:
        payload = self._json_body(request)
        command = self.command_bus.claim_command(
            command_id,
            claimed_by=payload["claimed_by"],
            requester_permission_level=payload.get("requester_permission_level", "L1"),
            lease_seconds=payload.get("lease_seconds", 300),
        )
        return self._json_response({"command": serialize_command(command)}, 200)

    def _complete_command(self, request: Request, command_id: str) -> Response:
        payload = self._json_body(request)
        command = self.command_bus.complete_command(
            command_id,
            claimed_by=payload["claimed_by"],
            result=payload["result"],
            requester_permission_level=payload.get("requester_permission_level", "L1"),
        )
        return self._json_response({"command": serialize_command(command)}, 200)

    def _fail_command(self, request: Request, command_id: str) -> Response:
        payload = self._json_body(request)
        command = self.command_bus.fail_command(
            command_id,
            claimed_by=payload["claimed_by"],
            result=payload.get("result"),
            requester_permission_level=payload.get("requester_permission_level", "L1"),
        )
        return self._json_response({"command": serialize_command(command)}, 200)

    def _append_event(self, request: Request) -> Response:
        payload = self._json_body(request)
        event = self.event_log.append_event(
            session_id=payload["session_id"],
            agent_id=payload["agent_id"],
            event_type=payload["event_type"],
            content=payload["content"],
            runtime=payload.get("runtime"),
            mode=payload.get("mode"),
            command_id=payload.get("command_id"),
            parent_seq=payload.get("parent_seq"),
            metadata=payload.get("metadata"),
        )
        latest_digest = self.event_log.storage.get_latest_session_digest(payload["session_id"])
        response: Dict[str, Any] = {"event": serialize_event(event)}
        if latest_digest is not None and latest_digest.to_seq == event.seq:
            response["digest"] = serialize_digest(latest_digest)
        return self._json_response(response, 201)

    def _resolve_memory_candidate(self, request: Request, candidate_id: str) -> Response:
        payload = self._json_body(request)
        candidate = self.memory_quality.resolve_candidate(
            candidate_id,
            status=payload.get("status", "active"),
            actor=payload.get("actor", "api"),
            runtime=payload.get("runtime"),
            mode=payload.get("mode"),
            recommended_action=payload.get("recommended_action"),
            metadata=payload.get("metadata"),
        )
        return self._json_response({"candidate": asdict(candidate)}, 200)

    def _list_events(self, request: Request) -> Response:
        session_id = request.args.get("session_id")
        if not session_id:
            raise BadRequestError("session_id is required")
        after_seq_value = request.args.get("after_seq")
        after_seq = int(after_seq_value) if after_seq_value is not None else None
        limit = int(request.args.get("limit", 50))
        events = self.event_log.list_events(session_id, after_seq=after_seq, limit=limit)
        digests = self.event_log.storage.list_session_digests(session_id, limit=10)
        return self._json_response(
            {
                "events": [serialize_event(event) for event in events],
                "digests": [serialize_digest(digest) for digest in digests],
            },
            200,
        )

    def _stream_events(self, request: Request) -> Response:
        session_id = request.args.get("session_id")
        if not session_id:
            raise BadRequestError("session_id is required")
        after_seq_value = request.args.get("after_seq")
        after_seq = int(after_seq_value) if after_seq_value is not None else None
        limit = int(request.args.get("limit", 50))
        self._require_access_token(request)
        stream_kwargs = {"after_seq": after_seq, "backlog_limit": limit}
        if self.testing:
            stream_kwargs.update({"poll_timeout": 0.05, "max_live_messages": 1, "max_heartbeats": 1})
        stream = self.event_log.stream_events(session_id, **stream_kwargs)
        return Response(stream, status=200, mimetype="text/event-stream", direct_passthrough=True)

    def _export_snapshot(self, request: Request) -> Response:
        self._require_access_token(request)
        redact = request.args.get("redact", "1") != "0"
        snapshot = self.storage.export_snapshot(redact=redact)
        return self._json_response(snapshot, 200)

    def _backup_database(self, request: Request) -> Response:
        self._require_access_token(request)
        payload = self._json_body(request) if request.data else {}
        target_path = payload.get("target_path")
        if target_path:
            backup_path = self.storage.backup_database(target_path)
        else:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = self.storage.backup_database(
                self.backup_dir / "{}-backup.db".format(self.storage.db_path.stem)
            )
        self.storage.append_audit_log(
            actor="system",
            action="database_backup",
            resource_type="database",
            resource_id=str(backup_path),
            metadata={"target_path": str(backup_path)},
        )
        return self._json_response({"backup_path": str(backup_path)}, 201)

    def _metrics(self, request: Request) -> Response:
        self._require_access_token(request)
        lines = self._build_metrics_lines(request)
        response = Response("\n".join(lines) + "\n", status=200, mimetype="text/plain")
        return response

    def _json_body(self, request: Request) -> Dict[str, Any]:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            raise BadRequestError("request body must be a JSON object")
        return payload

    def _json_response(self, payload: Dict[str, Any], status_code: int) -> Response:
        return Response(json.dumps(payload), status=status_code, mimetype="application/json")

    def _handle_options(self, request: Request) -> Response:
        response = Response("", status=204)
        return response

    def _apply_cors(self, request: Request, response: Response) -> Response:
        origin = request.headers.get("Origin")
        if not origin:
            return response
        if not self._origin_allowed(request, origin):
            return self._json_response({"error": "origin not allowed"}, 403)
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-RelayCore-Access-Token"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Vary"] = "Origin"
        return response

    def _origin_allowed(self, request: Request, origin: str) -> bool:
        request_origin = "{}://{}".format(request.scheme, request.host)
        if origin == request_origin:
            return True
        return origin in self.cors_allowlist

    def _require_access_token(self, request: Request) -> None:
        if not self.access_token:
            return
        provided = request.headers.get("X-RelayCore-Access-Token")
        if not provided and request.headers.get("Authorization", "").startswith("Bearer "):
            provided = request.headers.get("Authorization", "")[7:].strip()
        if not provided:
            provided = request.args.get("access_token")
        if provided != self.access_token:
            raise PermissionDeniedError("missing or invalid access token")

    def _build_metrics_lines(self, request: Request) -> list:
        session_id = request.args.get("session_id")
        lines = [
            "# RelayCore metrics",
            "relaycore_sessions_total {}".format(len(self.storage.list_sessions())),
            "relaycore_commands_total {}".format(len(self.storage.list_commands(limit=1000))),
            "relaycore_events_total {}".format(self._count_rows("agent_events")),
            "relaycore_digests_total {}".format(self._count_rows("session_digests")),
            "relaycore_candidates_total {}".format(self._count_rows("memory_candidates")),
            "relaycore_agent_states_total {}".format(self._count_rows("agent_states")),
            "relaycore_audit_logs_total {}".format(self._count_rows("audit_logs")),
        ]
        for status in ("pending", "claimed", "completed", "failed"):
            lines.append(
                'relaycore_commands_status_total{{status="{}"}} {}'.format(
                    status,
                    len(self.storage.list_commands(status=status, limit=1000)),
                )
            )
        for status in ("pending", "active", "merged", "corrected", "superseded", "archived", "rejected"):
            lines.append(
                'relaycore_candidates_status_total{{status="{}"}} {}'.format(
                    status,
                    len(self.storage.list_memory_candidates(status=status, limit=1000)),
                )
            )
        if session_id:
            commands = self.storage.list_commands(session_id=session_id, limit=1000)
            events = self.event_log.list_events(session_id, limit=1000)
            candidates = self.storage.list_memory_candidates(session_id=session_id, limit=1000)
            digests = self.storage.list_session_digests(session_id, limit=1000)
            lines.extend(
                [
                    'relaycore_session_commands{{session_id="{}"}} {}'.format(session_id, len(commands)),
                    'relaycore_session_events{{session_id="{}"}} {}'.format(session_id, len(events)),
                    'relaycore_session_candidates{{session_id="{}"}} {}'.format(session_id, len(candidates)),
                    'relaycore_session_digests{{session_id="{}"}} {}'.format(session_id, len(digests)),
                    'relaycore_session_token_estimate{{session_id="{}"}} {}'.format(
                        session_id,
                        estimate_payload_tokens(
                            [command.payload for command in commands[:5]],
                            [event.content for event in events[:10]],
                            [candidate.summary for candidate in candidates[:5]],
                            [digest.summary for digest in digests[:5]],
                        ),
                    ),
                ]
            )
        return lines

    def _count_rows(self, table_name: str) -> int:
        row = self.storage.connection.execute("SELECT COUNT(*) FROM {}".format(table_name)).fetchone()
        return int(row[0])


def _split_env_list(value: Optional[str]) -> list:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]
