import asyncio

from mcp import Client

from popcorn.mcp_server import mcp


def test_mcp_server_exposes_working_greeting_tool():
    async def call_tool():
        async with Client(mcp) as client:
            tools = await client.list_tools()
            assert "say_hello" in {tool.name for tool in tools.tools}
            result = await client.call_tool("say_hello", {"name": "World"})
            return result.structured_content

    assert asyncio.run(call_tool()) == {"result": "Hello, World! Welcome to Popcorn."}
