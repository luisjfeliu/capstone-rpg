"""MCP server exposing the RPG game engine as standard MCP tools.

This wraps the exact same tool functions the ADK agents use in-process
(`app/tools.py`), so any MCP-capable client (the GM agent via MCPToolset when
RPG_USE_MCP=1, Claude Desktop, MCP Inspector, ...) can drive the game engine
over the Model Context Protocol.

Design note: the game state lives inside THIS process (the module-level
`global_game_state` in app/engine.py). In MCP mode the state therefore
belongs to the server subprocess, not the CLI - which is why the CLI's rich
status panels run the agents with in-process tools by default, and MCP mode
is exercised through the ADK playground and the integration tests.

Run with: uv run python -m app.mcp_server
"""

from mcp.server.fastmcp import FastMCP

from app.tools import (
    enter_room,
    execute_advance_level,
    execute_cast_spell,
    execute_taunt,
    execute_use_item,
    execute_weapon_attack,
    get_available_routes,
    get_game_status,
    select_character,
    select_route,
)

mcp = FastMCP("capstone-rpg")

# Register the existing ADK tool functions unchanged - their docstrings and
# type hints double as the MCP tool schemas.
for tool_fn in (
    select_character,
    get_game_status,
    get_available_routes,
    select_route,
    enter_room,
    execute_weapon_attack,
    execute_cast_spell,
    execute_taunt,
    execute_use_item,
    execute_advance_level,
):
    mcp.tool()(tool_fn)


if __name__ == "__main__":
    # stdio transport: the client (e.g. ADK's MCPToolset) spawns this process
    # and communicates over stdin/stdout.
    mcp.run()
