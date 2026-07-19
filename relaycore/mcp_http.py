"""Streamable HTTP MCP bridge for RelayCore."""

import argparse
from typing import Any, Dict, Optional

from .mcp_server import RelayCoreMCPServer
from .storage import DEFAULT_DB_PATH, RelayCoreStorage, resolve_database_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run RelayCore as a streamable HTTP MCP server.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Database path.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument("--port", type=int, default=9090, help="Bind port.")
    parser.add_argument("--path", default="/mcp", help="Streamable HTTP mount path.")
    parser.add_argument("--name", default="RelayCore", help="MCP server name.")
    return parser


def build_mcp_app(
    *,
    name: str,
    db_path: str,
    host: str,
    port: int,
    path: str,
):
    from mcp.server.fastmcp import FastMCP

    storage = RelayCoreStorage(resolve_database_path(db_path))
    bridge = RelayCoreMCPServer(storage=storage)
    mcp = FastMCP(
        name,
        host=host,
        port=port,
        streamable_http_path=path,
        json_response=True,
        stateless_http=True,
        instructions=(
            "RelayCore exposes shared memory, command, digest, and event tools for local AI runtimes."
        ),
    )

    @mcp.tool()
    def memory_begin_task(
        session_id: str,
        runtime: str,
        agent_id: Optional[str] = None,
        mode: Optional[str] = None,
        name: Optional[str] = None,
        goal: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create or resume a shared task session."""
        return bridge.memory_begin_task(
            session_id=session_id,
            runtime=runtime,
            agent_id=agent_id,
            mode=mode,
            name=name,
            goal=goal,
            metadata=metadata,
        )

    @mcp.tool()
    def memory_context(
        session_id: str,
        runtime: str,
        agent_id: Optional[str] = None,
        query: Optional[str] = None,
        max_items: int = 5,
        max_tokens: int = 1200,
        include_full_content: bool = False,
    ) -> Dict[str, Any]:
        """Fetch compact relevant memory context."""
        return bridge.memory_context(
            session_id=session_id,
            runtime=runtime,
            agent_id=agent_id,
            query=query,
            max_items=max_items,
            max_tokens=max_tokens,
            include_full_content=include_full_content,
        )

    @mcp.tool()
    def memory_propose(
        session_id: str,
        runtime: str,
        type: str,
        title: str,
        content: str,
        agent_id: Optional[str] = None,
        mode: Optional[str] = None,
        tags: Optional[list] = None,
        rejected: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
        relation_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Normalize and score a proposed memory entry."""
        return bridge.memory_propose(
            session_id=session_id,
            runtime=runtime,
            type=type,
            title=title,
            content=content,
            agent_id=agent_id,
            mode=mode,
            tags=tags,
            rejected=rejected,
            metadata=metadata,
            relation_hint=relation_hint,
        )

    @mcp.tool()
    def memory_add(
        session_id: str,
        runtime: str,
        type: str,
        title: str,
        content: str,
        agent_id: Optional[str] = None,
        mode: Optional[str] = None,
        tags: Optional[list] = None,
        rejected: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist an explicit active memory entry."""
        return bridge.memory_add(
            session_id=session_id,
            runtime=runtime,
            type=type,
            title=title,
            content=content,
            agent_id=agent_id,
            mode=mode,
            tags=tags,
            rejected=rejected,
            metadata=metadata,
        )

    @mcp.tool()
    def memory_commit_task(
        session_id: str,
        runtime: str,
        summary: str,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Commit a compact task summary and create a digest."""
        return bridge.memory_commit_task(
            session_id=session_id,
            runtime=runtime,
            summary=summary,
            agent_id=agent_id,
            metadata=metadata,
        )

    @mcp.tool()
    def command_poll(
        runtime: str,
        requester_permission_level: str,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        target_agent: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Poll pending commands for a runtime or agent."""
        return bridge.command_poll(
            runtime=runtime,
            requester_permission_level=requester_permission_level,
            agent_id=agent_id,
            session_id=session_id,
            target_agent=target_agent,
            limit=limit,
        )

    @mcp.tool()
    def command_claim(
        command_id: str,
        runtime: str,
        claimed_by: str,
        requester_permission_level: str,
        lease_seconds: int = 300,
    ) -> Dict[str, Any]:
        """Claim a structured command."""
        return bridge.command_claim(
            command_id=command_id,
            runtime=runtime,
            claimed_by=claimed_by,
            requester_permission_level=requester_permission_level,
            lease_seconds=lease_seconds,
        )

    @mcp.tool()
    def command_complete(
        command_id: str,
        runtime: str,
        claimed_by: str,
        requester_permission_level: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Complete a claimed command."""
        return bridge.command_complete(
            command_id=command_id,
            runtime=runtime,
            claimed_by=claimed_by,
            requester_permission_level=requester_permission_level,
            result=result,
        )

    @mcp.tool()
    def command_fail(
        command_id: str,
        runtime: str,
        claimed_by: str,
        requester_permission_level: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Fail a claimed command."""
        return bridge.command_fail(
            command_id=command_id,
            runtime=runtime,
            claimed_by=claimed_by,
            requester_permission_level=requester_permission_level,
            result=result,
        )

    @mcp.tool()
    def agent_event_append(
        session_id: str,
        runtime: str,
        event_type: str,
        content: Dict[str, Any],
        agent_id: Optional[str] = None,
        mode: Optional[str] = None,
        command_id: Optional[str] = None,
        parent_seq: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Append an important event to the shared timeline."""
        return bridge.agent_event_append(
            session_id=session_id,
            runtime=runtime,
            event_type=event_type,
            content=content,
            agent_id=agent_id,
            mode=mode,
            command_id=command_id,
            parent_seq=parent_seq,
            metadata=metadata,
        )

    @mcp.tool()
    def session_digest_get(
        session_id: str,
        runtime: str,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """Fetch recent session digests."""
        return bridge.session_digest_get(session_id=session_id, runtime=runtime, limit=limit)

    @mcp.tool()
    def agent_heartbeat(
        runtime: str,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        role: Optional[str] = None,
        status: str = "active",
        current_task: Optional[str] = None,
        capabilities: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update runtime heartbeat and shared agent state."""
        return bridge.agent_heartbeat(
            runtime=runtime,
            agent_id=agent_id,
            session_id=session_id,
            role=role,
            status=status,
            current_task=current_task,
            capabilities=capabilities,
            metadata=metadata,
        )

    return mcp, storage


def main() -> int:
    args = build_arg_parser().parse_args()
    mcp, storage = build_mcp_app(
        name=args.name,
        db_path=args.db,
        host=args.host,
        port=args.port,
        path=args.path,
    )
    try:
        mcp.run(transport="streamable-http")
        return 0
    finally:
        storage.close()


if __name__ == "__main__":
    raise SystemExit(main())
