import asyncio

from popcorn.agent import answer


def test_agent_invokes_skill_and_mcp_tool_and_emits_trace():
    response, trace = asyncio.run(answer("Hello Maya"))
    assert response == "Hello, Maya! Welcome to Popcorn."
    assert any(event.attributes.get("skill") == "greeting" for event in trace.events)
    assert any(event.attributes.get("tool") == "say_hello" for event in trace.events)
    assert trace.to_dict()["schema_version"] == "0.1"
