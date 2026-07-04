"""Save-game round trip: GameState -> dict -> JSON -> restored GameState."""

import json

from app.engine import GameState


def _play_a_bit() -> GameState:
    state = GameState()
    state.select_character("Wizard", "Gandalf")
    state.generate_level_routes()
    state.choose_route("forward")
    state.current_room_index = 2
    state.current_level = 3
    state.gold = 240
    state.inventory = ["Health Potion", "Elixir of Life"]
    state.player.hp = 17
    state.player.mana = 12
    state.player.level = 2
    state.companion.exp = 80
    return state


def test_save_round_trip_restores_world():
    original = _play_a_bit()

    # Serialize through JSON to prove the snapshot is plain data
    data = json.loads(json.dumps(original.to_save_dict()))

    restored = GameState()
    restored.restore_save_dict(data)

    assert restored.player.name == "Gandalf"
    assert restored.player.hp == 17
    assert restored.player.mana == 12
    assert restored.player.level == 2
    assert restored.companion.name == "Garrick"
    assert restored.companion.exp == 80
    assert restored.current_level == 3
    assert restored.gold == 240
    assert restored.inventory == ["Health Potion", "Elixir of Life"]
    assert restored.current_room_index == 2
    assert set(restored.routes) == {"left", "forward", "right"}
    # selected_route must point at the restored routes dict, not a copy
    assert restored.selected_route is restored.routes["forward"]
    assert (
        restored.selected_route.monster_types == original.selected_route.monster_types
    )


def test_restore_clears_combat_and_game_flags():
    original = _play_a_bit()
    data = original.to_save_dict()

    restored = GameState()
    restored.combat_active = True
    restored.game_over = True
    restored.restore_save_dict(data)

    assert restored.active_monster is None
    assert restored.combat_active is False
    assert restored.game_over is False
    assert restored.game_won is False


def test_save_without_selected_route():
    state = GameState()
    state.select_character("Fighter", "Conan")
    state.generate_level_routes()

    restored = GameState()
    restored.restore_save_dict(json.loads(json.dumps(state.to_save_dict())))
    assert restored.selected_route is None
    assert restored.player.char_class == "Fighter"
