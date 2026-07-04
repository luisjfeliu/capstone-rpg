from app.engine import Character, GameState, Monster


def test_character_initialization():
    state = GameState()
    player, companion = state.select_character("Wizard", "Albus")

    assert player.name == "Albus"
    assert player.char_class == "Wizard"
    assert player.role == "player"
    assert player.hp == 40
    assert player.max_hp == 40
    assert player.mana == 30
    assert player.max_mana == 30

    assert companion.name == "Garrick"
    assert companion.char_class == "Fighter"
    assert companion.role == "companion"
    assert companion.hp == 60
    assert companion.max_hp == 60
    assert companion.mana == 0


def test_gain_xp_and_level_up():
    char = Character("Conan", "Fighter", "player")
    assert char.level == 1
    assert char.exp == 0
    assert char.max_hp == 60

    leveled = char.gain_xp(50)
    assert not leveled
    assert char.level == 1
    assert char.exp == 50

    # 100 XP is needed for lvl 2
    leveled = char.gain_xp(50)
    assert leveled
    assert char.level == 2
    assert char.exp == 0
    assert char.max_hp == int(60 * 1.15)

    # 200 XP is needed for lvl 3
    leveled = char.gain_xp(250)
    assert leveled
    assert char.level == 3
    assert char.exp == 50


def test_route_generation_and_selection():
    state = GameState()
    state.select_character("Wizard", "Albus")
    state.generate_level_routes()

    assert "left" in state.routes
    assert "forward" in state.routes
    assert "right" in state.routes

    left_route = state.routes["left"]
    assert left_route.direction == "left"
    assert left_route.difficulty == "easy"

    state.choose_route("left")
    assert state.selected_route == left_route
    assert state.current_room_index == 0


def test_combat_flow():
    state = GameState()
    player, _companion = state.select_character("Wizard", "Albus")
    state.generate_level_routes()
    state.choose_route("left")

    _desc, is_combat = state.enter_next_room()
    assert is_combat
    assert state.active_monster is not None
    assert state.combat_active

    # Cast fireball
    log = state.cast_spell(player, "Fireball", state.active_monster.name)
    assert "casts Fireball" in log

    # Monster takes damage
    expected_hp = state.active_monster.max_hp - int(player.intelligence * 1.5)
    assert state.active_monster.hp == expected_hp

    # Monster attacks player - taunting makes the target deterministic
    # (otherwise the monster picks player or companion 50/50 at random)
    player.is_taunting = True
    prev_hp = player.hp
    log_monster = state.monster_attack()
    assert "attacks" in log_monster
    assert player.hp < prev_hp


def test_use_item():
    state = GameState()
    player, _companion = state.select_character("Wizard", "Albus")
    player.hp = 10
    player.mana = 5

    assert "Health Potion" in state.inventory
    log = state.use_potion(player, "Health Potion")
    assert "uses a Health Potion" in log
    assert player.hp > 10

    assert "Mana Potion" in state.inventory
    log_mana = state.use_potion(player, "Mana Potion")
    assert "uses a Mana Potion" in log_mana
    assert player.mana > 5


def test_route_treasure_awards_clean_item_name_and_gold():
    # Regression: treasure used to be re-parsed from its display text,
    # putting "a Elixir of Life" into the inventory (unusable by use_potion).
    state = GameState()
    state.select_character("Wizard", "Albus")
    state.generate_level_routes()
    state.choose_route("right")  # hard route awards an Elixir of Life
    route = state.selected_route

    state.current_room_index = route.length  # last room of the path
    state.active_monster = Monster(
        "Cave Troll", hp=10, attack=5, xp_reward=20, gold_reward=10
    )
    state.combat_active = True
    state.active_monster.hp = 0  # monster defeated

    is_over, msg = state.check_combat_end()
    assert is_over
    assert "Path Complete!" in msg
    assert "Elixir of Life" in state.inventory
    assert not any(item.startswith("a ") for item in state.inventory)
    assert state.gold == 50 + 10 + route.treasure_gold
    # the item must be consumable by name
    assert "fully restoring" in state.use_potion(state.player, "Elixir of Life")
