"""Typed tool layer - the only door between the LLM agents and the game engine.

Each function here is registered both as an ADK tool (app/agent.py) and as an
MCP tool (app/mcp_server.py). Docstrings and type hints double as the tool
schemas the model sees, so they are written for the model as much as for
humans. Contract: validate inputs, mutate state only via the engine, and
return structured dicts (never raise) so a bad tool call becomes a polite
in-game error instead of a crash.
"""

from app.engine import global_game_state


def select_character(char_class: str, name: str) -> dict:
    """Creates the player character and their NPC companion to start the game.

    The companion is automatically assigned the complementary class: choosing a
    Wizard pairs the player with Garrick the Fighter; choosing a Fighter pairs
    them with Eldrin the Wizard, so the party always covers both roles.

    Args:
        char_class: The player's chosen class: 'Wizard' or 'Fighter'.
        name: The player's character name. Defaults to 'Hero' if blank.

    Returns:
        A dictionary with the created party (player and companion) or an error.
    """
    g = global_game_state
    char_class = char_class.strip().capitalize()
    if char_class not in ("Wizard", "Fighter"):
        return {"status": "error", "message": "Class must be 'Wizard' or 'Fighter'."}

    name = (name or "").strip() or "Hero"
    player, companion = g.select_character(char_class, name)
    return {
        "status": "success",
        "message": f"{player.name} the {player.char_class} joins forces with {companion.name} the {companion.char_class}!",
        "player": {
            "name": player.name,
            "class": player.char_class,
            "hp": player.hp,
            "mana": player.mana,
        },
        "companion": {
            "name": companion.name,
            "class": companion.char_class,
            "hp": companion.hp,
            "mana": companion.mana,
        },
    }


def get_game_status() -> dict:
    """Gets the current status of the party, including HP, Mana, Level, current level, Gold, and Inventory.

    Returns:
        A dictionary containing the stats and inventory of the party.
    """
    g = global_game_state
    if not g.player:
        return {
            "status": "error",
            "message": "Game not started. No character selected.",
        }

    return {
        "current_level": g.current_level,
        "gold": g.gold,
        "inventory": g.inventory,
        "player": {
            "name": g.player.name,
            "class": g.player.char_class,
            "level": g.player.level,
            "hp": g.player.hp,
            "max_hp": g.player.max_hp,
            "mana": g.player.mana,
            "max_mana": g.player.max_mana,
            "strength": g.player.strength,
            "intelligence": g.player.intelligence,
            "is_alive": g.player.is_alive(),
        },
        "companion": {
            "name": g.companion.name,
            "class": g.companion.char_class,
            "level": g.companion.level,
            "hp": g.companion.hp,
            "max_hp": g.companion.max_hp,
            "mana": g.companion.mana,
            "max_mana": g.companion.max_mana,
            "strength": g.companion.strength,
            "intelligence": g.companion.intelligence,
            "is_alive": g.companion.is_alive(),
        },
        "combat_active": g.combat_active,
        "active_monster": {
            "name": g.active_monster.name,
            "hp": g.active_monster.hp,
            "max_hp": g.active_monster.max_hp,
            "attack": g.active_monster.attack,
        }
        if g.active_monster
        else None,
        "game_over": g.game_over,
        "game_won": g.game_won,
    }


def get_available_routes() -> dict:
    """Gets the generated path/route options for the current level.

    Returns:
        A dictionary containing description of left, forward, and right paths.
    """
    g = global_game_state
    if not g.routes:
        g.generate_level_routes()

    result = {}
    for direction, route in g.routes.items():
        result[direction] = {
            "direction": direction,
            "length": route.length,
            "difficulty": route.difficulty,
            "treasure": route.treasure,
        }
    return result


def select_route(direction: str) -> dict:
    """Selects the route direction ('left', 'forward', or 'right') for the party to proceed.

    Args:
        direction: The chosen path direction: 'left', 'forward', or 'right'.

    Returns:
        A dictionary indicating confirmation.
    """
    g = global_game_state
    direction = direction.lower().strip()
    if direction not in ["left", "forward", "right"]:
        return {
            "status": "error",
            "message": "Direction must be 'left', 'forward', or 'right'.",
        }
    try:
        g.choose_route(direction)
        return {
            "status": "success",
            "message": f"Route selected: {direction}. Moving forward!",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def enter_room() -> dict:
    """Enters the next room along the chosen path. May trigger a combat encounter.

    Returns:
        A dictionary containing the description of what happened in the room.
    """
    g = global_game_state
    if not g.selected_route:
        return {
            "status": "error",
            "message": "No route selected. Select a route first.",
        }

    if g.current_room_index >= g.selected_route.length:
        return {
            "status": "complete",
            "message": "You have cleared this route. You can advance to the next level.",
        }

    try:
        desc, is_combat = g.enter_next_room()
        return {
            "status": "combat" if is_combat else "explore",
            "message": desc,
            "room_index": g.current_room_index,
            "total_rooms": g.selected_route.length,
            "monster": {
                "name": g.active_monster.name,
                "hp": g.active_monster.hp,
                "attack": g.active_monster.attack,
            }
            if g.active_monster
            else None,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def execute_weapon_attack(attacker_name: str, target: str) -> dict:
    """Executes a weapon attack by the specified character.

    Args:
        attacker_name: The name of the character attacking.
        target: The name of the target monster.

    Returns:
        A dictionary detailing the damage dealt.
    """
    g = global_game_state
    if not g.combat_active or not g.active_monster:
        return {"status": "error", "message": "No active combat."}

    attacker = None
    if g.player.name.lower() == attacker_name.lower():
        attacker = g.player
    elif g.companion.name.lower() == attacker_name.lower():
        attacker = g.companion

    if not attacker:
        return {
            "status": "error",
            "message": f"Character {attacker_name} not found in party.",
        }

    if not attacker.is_alive():
        return {
            "status": "error",
            "message": f"{attacker.name} is unconscious and cannot attack.",
        }

    log = g.weapon_attack(attacker, target)
    g.combat_log.append(log)

    # Check if combat ends
    is_over, end_msg = g.check_combat_end()
    if is_over:
        g.combat_log.append(end_msg)

    return {
        "status": "success",
        "log": log,
        "combat_ended": is_over,
        "end_message": end_msg if is_over else "",
    }


def execute_cast_spell(attacker_name: str, spell_name: str, target: str) -> dict:
    """Casts a magical spell by the specified wizard character.

    Args:
        attacker_name: The name of the character casting the spell.
        spell_name: The name of the spell ('Fireball', 'Heal', 'Shield').
        target: The name of the target (monster or party member name).

    Returns:
        A dictionary detailing the spell effect.
    """
    g = global_game_state
    attacker = None
    if g.player.name.lower() == attacker_name.lower():
        attacker = g.player
    elif g.companion.name.lower() == attacker_name.lower():
        attacker = g.companion

    if not attacker:
        return {
            "status": "error",
            "message": f"Character {attacker_name} not found in party.",
        }

    if not attacker.is_alive():
        return {
            "status": "error",
            "message": f"{attacker.name} is unconscious and cannot cast spells.",
        }

    log = g.cast_spell(attacker, spell_name, target)
    g.combat_log.append(log)

    # Check if combat ends
    is_over, end_msg = g.check_combat_end()
    if is_over:
        g.combat_log.append(end_msg)

    return {
        "status": "success",
        "log": log,
        "combat_ended": is_over,
        "end_message": end_msg if is_over else "",
    }


def execute_taunt(character_name: str) -> dict:
    """Makes a Fighter taunt the monster, forcing it to attack them on its next turn.

    Taunting is how a Fighter protects a wounded ally: the monster's next
    attack is redirected to the taunting character instead of being chosen
    at random. The effect lasts for one monster turn.

    Args:
        character_name: The name of the Fighter who taunts.

    Returns:
        A dictionary confirming the taunt or an error.
    """
    g = global_game_state
    if not g.combat_active or not g.active_monster:
        return {"status": "error", "message": "No active combat."}

    character = None
    if g.player.name.lower() == character_name.lower():
        character = g.player
    elif g.companion.name.lower() == character_name.lower():
        character = g.companion

    if not character:
        return {
            "status": "error",
            "message": f"Character {character_name} not found in party.",
        }
    if character.char_class != "Fighter":
        return {
            "status": "error",
            "message": f"{character.name} is a {character.char_class} - only Fighters can Taunt.",
        }
    if not character.is_alive():
        return {
            "status": "error",
            "message": f"{character.name} is unconscious and cannot taunt.",
        }

    character.is_taunting = True
    log = f"{character.name} taunts the {g.active_monster.name}, drawing its attention!"
    g.combat_log.append(log)
    return {"status": "success", "log": log}


def execute_use_item(character_name: str, potion_name: str) -> dict:
    """Uses a potion or elixir from inventory on the specified character.

    Args:
        character_name: The name of the character using the potion.
        potion_name: The name of the potion ('Health Potion', 'Mana Potion', 'Elixir of Life').

    Returns:
        A dictionary detailing the potion effect.
    """
    g = global_game_state
    character = None
    if g.player.name.lower() == character_name.lower():
        character = g.player
    elif g.companion.name.lower() == character_name.lower():
        character = g.companion

    if not character:
        return {"status": "error", "message": f"Character {character_name} not found."}

    log = g.use_potion(character, potion_name)
    return {"status": "success", "log": log}


def execute_advance_level() -> dict:
    """Advances the party to the next level (1-7), healing and resetting route selection.

    Returns:
        A dictionary confirming advancement and portal win status.
    """
    g = global_game_state
    try:
        is_win, msg = g.next_level()
        return {
            "status": "won" if is_win else "success",
            "message": msg,
            "current_level": g.current_level,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
