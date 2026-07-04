"""Unit tests for the ADK tool layer (app/tools.py).

The tools operate on the module-level `global_game_state` singleton (shared
by the GM and companion agents), so each test resets the relevant fields on
that same object - rebinding the name would break the reference the tools
module already holds.
"""

from app.engine import Monster, global_game_state
from app.tools import execute_taunt, get_game_status, select_character


def _reset_state():
    global_game_state.player = None
    global_game_state.companion = None
    global_game_state.routes = {}
    global_game_state.selected_route = None
    global_game_state.game_over = False
    global_game_state.game_won = False


def test_select_character_wizard_pairs_fighter_companion():
    _reset_state()
    result = select_character("Wizard", "Gandalf")
    assert result["status"] == "success"
    assert result["player"] == {
        "name": "Gandalf",
        "class": "Wizard",
        "hp": 40,
        "mana": 30,
    }
    assert result["companion"]["name"] == "Garrick"
    assert result["companion"]["class"] == "Fighter"


def test_select_character_is_case_insensitive():
    _reset_state()
    result = select_character("fighter", "Aragorn")
    assert result["status"] == "success"
    assert result["player"]["class"] == "Fighter"
    assert result["companion"]["class"] == "Wizard"


def test_select_character_rejects_unknown_class():
    _reset_state()
    result = select_character("Bard", "Lute")
    assert result["status"] == "error"
    assert global_game_state.player is None


def test_select_character_defaults_blank_name_to_hero():
    _reset_state()
    result = select_character("Wizard", "   ")
    assert result["status"] == "success"
    assert result["player"]["name"] == "Hero"


def test_get_game_status_errors_before_selection_then_reports_party():
    _reset_state()
    assert get_game_status()["status"] == "error"

    select_character("Wizard", "Gandalf")
    status = get_game_status()
    assert status["player"]["name"] == "Gandalf"
    assert status["companion"]["is_alive"] is True
    assert status["combat_active"] is False


def test_execute_taunt_redirects_monster_to_fighter():
    _reset_state()
    select_character("Wizard", "Gandalf")  # companion Garrick is the Fighter
    global_game_state.active_monster = Monster(
        "Goblin Scout", hp=30, attack=5, xp_reward=10, gold_reward=5
    )
    global_game_state.combat_active = True

    result = execute_taunt("Garrick")
    assert result["status"] == "success"
    assert global_game_state.companion.is_taunting

    # The taunt must actually redirect the monster's attack
    log = global_game_state.monster_attack()
    assert "Garrick" in log
    assert global_game_state.player.hp == global_game_state.player.max_hp


def test_execute_taunt_rejected_for_wizard_and_outside_combat():
    _reset_state()
    select_character("Wizard", "Gandalf")
    assert execute_taunt("Gandalf")["status"] == "error"  # no combat

    global_game_state.active_monster = Monster(
        "Goblin Scout", hp=30, attack=5, xp_reward=10, gold_reward=5
    )
    global_game_state.combat_active = True
    result = execute_taunt("Gandalf")  # Wizards cannot taunt
    assert result["status"] == "error"
    assert "only Fighters" in result["message"]
