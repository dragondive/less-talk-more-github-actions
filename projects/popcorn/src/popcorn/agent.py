"""A small skill router that calls the local MCP server."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from mcp import Client

from popcorn.mcp_server import mcp


@dataclass
class TraceEvent:
    event_id: str
    parent_id: str | None
    name: str
    started_at: str
    status: str = "ok"
    attributes: dict[str, object] = field(default_factory=dict)
    ended_at: str | None = None


@dataclass
class ExecutionTrace:
    request_id: str
    execution_id: str
    events: list[TraceEvent] = field(default_factory=list)

    def record(
        self,
        name: str,
        *,
        parent_id: str | None = None,
        status: str = "ok",
        **attributes: object,
    ) -> TraceEvent:
        now = datetime.now(timezone.utc).isoformat()
        event = TraceEvent(
            event_id=str(uuid4()),
            parent_id=parent_id,
            name=name,
            started_at=now,
            ended_at=now,
            status=status,
            attributes=attributes,
        )
        self.events.append(event)
        return event

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "0.1",
            "request_id": self.request_id,
            "execution_id": self.execution_id,
            "events": [asdict(event) for event in self.events],
        }


def new_trace() -> ExecutionTrace:
    return ExecutionTrace(request_id=str(uuid4()), execution_id=str(uuid4()))


async def _call_tool(
    tool_name: str,
    arguments: dict[str, object],
    trace: ExecutionTrace,
    parent_id: str,
) -> object:
    call_event = trace.record(
        "mcp.tool.call",
        parent_id=parent_id,
        server="popcorn-demo",
        tool=tool_name,
        arguments=arguments,
    )
    try:
        async with Client(mcp) as client:
            result = await client.call_tool(tool_name, arguments)
        if result.is_error:
            call_event.status = "error"
            raise RuntimeError(f"MCP tool failed: {tool_name}")
        structured = result.structured_content
        if structured is None:
            raise RuntimeError(f"MCP tool returned no structured content: {tool_name}")
        if set(structured) == {"result"}:
            return structured["result"]
        return structured
    except Exception:
        call_event.status = "error"
        raise


async def answer(question: str, trace: ExecutionTrace | None = None) -> tuple[str, ExecutionTrace]:
    """Handle a request through a skill and an MCP tool."""
    trace = trace or new_trace()
    agent_event = trace.record("agent.run")
    normalized = question.strip()

    if normalized.casefold().startswith("movie fit:"):
        skill_name = "movie_fit"
        skill_event = trace.record("skill.invoke", parent_id=agent_event.event_id, skill=skill_name)
        title = normalized.partition(":")[2].strip() or "The Matrix"
        profile = await _call_tool(
            "get_movie_profile", {"title": title}, trace, skill_event.event_id
        )
        if not isinstance(profile, dict):
            raise TypeError("Movie profile MCP tool returned an invalid result")
        response = (
            f"{profile['title']} may suit an action fan: it is listed as "
            f"{profile['genres']} and described as {profile['tone']}. "
            f"Source: {profile['source']}."
        )
    else:
        skill_name = "greeting"
        skill_event = trace.record("skill.invoke", parent_id=agent_event.event_id, skill=skill_name)
        folded = normalized.casefold()
        if folded.startswith("hello"):
            name = normalized[len("hello") :].strip(" ,.!?") or "World"
        elif folded.startswith("hi"):
            name = normalized[len("hi") :].strip(" ,.!?") or "World"
        else:
            name = normalized or "World"
        response = await _call_tool("say_hello", {"name": name}, trace, skill_event.event_id)
        if not isinstance(response, str):
            raise TypeError("Greeting MCP tool returned an invalid result")

    trace.record(
        "agent.response",
        parent_id=agent_event.event_id,
        skill=skill_name,
        response=response,
    )
    return response, trace
