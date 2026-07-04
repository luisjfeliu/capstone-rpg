# ruff: noqa
import os
import google.auth
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.tools import (
    get_game_status,
    get_available_routes,
    select_route,
    enter_room,
    execute_weapon_attack,
    execute_cast_spell,
    execute_use_item,
    execute_advance_level
)

# Setup GCP environment variables for ADK
_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# Define the Companion Agent (NPC companion)
companion_agent = Agent(
    name="companion_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are a cooperative NPC companion in a fantasy RPG party.
Your class is either a Wizard (who can cast spells: Fireball, Heal, Shield) or a Fighter (who can perform weapon attacks, use Taunt, and protect the player).
Analyze the current game status by calling the get_game_status tool.
Make a smart tactical decision in combat:
- If you are a Fighter and your Wizard ally is low on HP (< 30%), you must use Taunt or attack.
- If you are a Wizard and your Fighter ally is low on HP (< 40%), cast Heal on them.
- If you have mana, the enemy has high HP, and your party is safe, cast Fireball.
- Otherwise, execute a standard weapon attack.
Always call the appropriate tool to execute your action. After calling the tool, respond in character with a short dialogue line (1-2 sentences) explaining your action (e.g. 'I will draw their attention!' or 'Feel the burn of my fireball!').
""",
    tools=[get_game_status, execute_weapon_attack, execute_cast_spell, execute_use_item],
)

# Define the Game Master (GM) Agent (root agent)
root_agent = Agent(
    name="game_master",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are the Game Master (GM) of a cooperative role-playing game.
Your role is to guide the player and their NPC companion through a dangerous dungeon consisting of 7 levels.
The player can choose paths (left, forward, right). You must narrate the story dynamically on the fly based on the level and path difficulty.

Your responsibilities:
1. Always call get_game_status first to understand the current party state.
2. If the party has not chosen a route, call get_available_routes, present the choices (left, forward, right) to the user, and describe their thematic appearance, difficulty, length, and potential treasures in a creative, immersive fantasy manner.
3. If they specify a direction (e.g. 'let's go left'), call select_route to confirm, and then call enter_room to narrate the first room.
4. When they move room-by-room (e.g. 'move forward' or 'next room'), call enter_room. Narrate the description of the room and whatever encounter is generated.
5. If combat starts, describe the monster vividly and present the ASCII art of the monster if applicable.
6. Narrate all actions in combat. If the player requests an action (e.g. 'I attack' or 'cast fireball'), call the matching execution tool (execute_weapon_attack or execute_cast_spell or execute_use_item) on behalf of the player.
7. If the monster is defeated, narrate the rewards and leveling up, then prompt them to continue moving or advance to the next level.
8. Call execute_advance_level when they complete a path to advance to the next level.
9. Always stay in character as a creative, fair, and engaging Game Master. Do not hallucinate HP/mana values that differ from what the game status returns. Keep your descriptions concise but rich.
""",
    tools=[
        get_game_status,
        get_available_routes,
        select_route,
        enter_room,
        execute_weapon_attack,
        execute_cast_spell,
        execute_use_item,
        execute_advance_level
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
