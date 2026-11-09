"""A lightweight Popcorn intent router that invokes TMDB-backed MCP skills."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from mcp import Client

from popcorn.mcp_server import mcp
from popcorn.skills import actor_filmography, movie_discovery


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


def _intent(question: str) -> tuple[str, str] | None:
    value = question.strip().rstrip("?.!")
    actor_patterns = (
        r"(?:what )?movies has (.+?) acted in",
        r"movies (?:with|by) (.+)",
        r"(?:list )?(?:the )?movies starring (.+)",
        r"filmography (?:of|for) (.+)",
    )
    for pattern in actor_patterns:
        match = re.fullmatch(pattern, value, flags=re.IGNORECASE)
        if match and match.group(1).strip():
            return actor_filmography.SKILL_NAME, match.group(1).strip()

    movie_patterns = (
        r"(?:movie|film):\s*(.+)",
        r"(?:tell me about|details (?:for|of)|cast of|who stars in|who is in)\s+(.+)",
        r"who are (?:the )?(?:actors|cast) (?:in|of)\s+(.+)",
    )
    for pattern in movie_patterns:
        match = re.fullmatch(pattern, value, flags=re.IGNORECASE)
        if match and match.group(1).strip():
            return movie_discovery.SKILL_NAME, match.group(1).strip()
    return None


async def _call_tool(
    tool_name: str,
    arguments: dict[str, object],
    trace: ExecutionTrace,
    parent_id: str,
) -> object:
    event = trace.record(
        "mcp.tool.call",
        parent_id=parent_id,
        server="popcorn-tmdb",
        tool=tool_name,
        arguments=arguments,
    )
    try:
        async with Client(mcp) as client:
            result = await client.call_tool(tool_name, arguments)
        if result.is_error:
            event.status = "error"
            message = "; ".join(
                item.text for item in result.content if getattr(item, "text", None)
            )
            raise RuntimeError(message or f"MCP tool failed: {tool_name}")
        structured = result.structured_content
        if structured is None:
            raise RuntimeError(f"MCP tool returned no structured content: {tool_name}")
        if isinstance(structured.get("error"), str):
            raise RuntimeError(structured["error"])
        return structured.get("result") if set(structured) == {"result"} else structured
    except Exception:
        event.status = "error"
        raise


async def answer(question: str, trace: ExecutionTrace | None = None) -> tuple[str, ExecutionTrace]:
    """Route a movie/person question to one bounded Popcorn skill."""
    trace = trace or new_trace()
    agent_event = trace.record("agent.run")
    intent = _intent(question)
    if intent is None:
        response = (
            "I can look up movie details and cast, or list a person's movie acting credits. "
            "Try 'Tell me about The Matrix', 'Who is in The Matrix', or "
            "'What movies has Keanu Reeves acted in?'."
        )
        trace.record("agent.response", parent_id=agent_event.event_id, response=response)
        return response, trace

    skill_name, query = intent
    skill_event = trace.record("skill.invoke", parent_id=agent_event.event_id, skill=skill_name)

    async def invoke(tool: str, arguments: dict[str, object]) -> object:
        return await _call_tool(tool, arguments, trace, skill_event.event_id)

    try:
        if skill_name == movie_discovery.SKILL_NAME:
            response = await movie_discovery.run(query, invoke)
        else:
            response = await actor_filmography.run(query, invoke)
    except Exception as error:
        response = str(error)

    trace.record(
        "agent.response",
        parent_id=agent_event.event_id,
        skill=skill_name,
        response=response,
    )
    return response, trace
