"""Integration test for the game-engine MCP server (app/mcp_server.py).

Spawns the server as a real stdio subprocess - exactly how ADK's MCPToolset
consumes it when RPG_USE_MCP=1 - and exercises the protocol end to end:
initialize, list_tools, and a select_character/get_game_status round trip
against the state held inside the server process.
"""

import json
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED_TOOLS = {
    "select_character",
    "get_game_status",
    "get_available_routes",
    "select_route",
    "enter_room",
    "execute_weapon_attack",
    "execute_cast_spell",
    "execute_use_item",
    "execute_advance_level",
}

SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-m", "app.mcp_server"],
)


def _payload(result) -> dict:
    """Extracts the JSON dict a tool returned from an MCP CallToolResult."""
    assert not result.isError, f"MCP tool call failed: {result.content}"
    return json.loads(result.content[0].text)


@pytest.mark.asyncio
async def test_mcp_server_tools_round_trip() -> None:
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # All game tools are exposed over MCP.
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert EXPECTED_TOOLS <= names, f"Missing tools: {EXPECTED_TOOLS - names}"

            # Before character selection the engine reports an error status.
            status = _payload(await session.call_tool("get_game_status", {}))
            assert status.get("status") == "error"

            # Character creation mutates state inside the server process...
            created = _payload(
                await session.call_tool(
                    "select_character",
                    {"char_class": "wizard", "name": "Testa"},
                )
            )
            assert created["status"] == "success"
            assert created["player"]["class"] == "Wizard"

            # ...and is visible on the next call over the same connection.
            status = _payload(await session.call_tool("get_game_status", {}))
            assert status["player"]["name"] == "Testa"
            assert status["companion"]["class"] == "Fighter"
