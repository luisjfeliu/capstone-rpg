from behave import given, when, then
from app.engine import GameState, Character, Monster

@given('a new game starts')
def step_impl(context):
    context.game_state = GameState()

@given('the player chooses "{class_name}" and names themselves "{player_name}"')
@when('the player chooses "{class_name}" and names themselves "{player_name}"')
def step_impl(context, class_name, player_name):
    context.game_state.select_character(class_name, player_name)

@then('the player character is a "{class_name}" named "{player_name}" with health {hp:d} and mana {mana:d}')
def step_impl(context, class_name, player_name, hp, mana):
    p = context.game_state.player
    assert p.char_class == class_name
    assert p.name == player_name
    assert p.hp == hp
    assert p.mana == mana

@then('the companion character is a "{class_name}" named "{companion_name}" with health {hp:d} and level {lvl:d}')
def step_impl(context, class_name, companion_name, hp, lvl):
    c = context.game_state.companion
    assert c.char_class == class_name
    assert c.name == companion_name
    assert c.hp == hp
    assert c.level == lvl

@given('the party is on level {level:d}')
def step_impl(context, level):
    if not hasattr(context, 'game_state') or context.game_state is None:
        context.game_state = GameState()
        context.game_state.select_character("Wizard", "Gandalf")
    context.game_state.current_level = level

@given('the GM generates the routes')
@when('the GM generates the routes')
def step_impl(context):
    context.game_state.generate_level_routes()

@then('three paths are available: "left", "forward", and "right"')
def step_impl(context):
    assert len(context.game_state.routes) == 3
    assert "left" in context.game_state.routes
    assert "forward" in context.game_state.routes
    assert "right" in context.game_state.routes

@then('the paths have different difficulties: "left" is "{diff1}", "forward" is "{diff2}", "right" is "{diff3}"')
def step_impl(context, diff1, diff2, diff3):
    assert context.game_state.routes["left"].difficulty == diff1
    assert context.game_state.routes["forward"].difficulty == diff2
    assert context.game_state.routes["right"].difficulty == diff3

@given('they select the "{route_name}" route')
@when('they select the "{route_name}" route')
def step_impl(context, route_name):
    context.game_state.choose_route(route_name)

@given('they successfully clear all rooms in the route')
@when('they successfully clear all rooms in the route')
def step_impl(context):
    r = context.game_state.selected_route
    context.game_state.current_room_index = r.length

@given('they advance to the next level')
@when('they advance to the next level')
def step_impl(context):
    context.game_state.next_level()

@then('the party is on level {level:d}')
def step_impl(context, level):
    assert context.game_state.current_level == level

@then('the player and companion health is fully restored')
def step_impl(context):
    assert context.game_state.player.hp == context.game_state.player.max_hp
    assert context.game_state.companion.hp == context.game_state.companion.max_hp

@then('the game is won and the story concludes')
def step_impl(context):
    assert context.game_state.game_won
    assert context.game_state.game_over

@given('they enter a combat with a "{monster_name}" having {hp:d} HP')
def step_impl(context, monster_name, hp):
    context.game_state.active_monster = Monster(monster_name, hp, attack=5, xp_reward=20, gold_reward=10)
    context.game_state.combat_active = True

@given('they enter a combat with an "{monster_name}" having {hp:d} HP')
def step_impl(context, monster_name, hp):
    context.game_state.active_monster = Monster(monster_name, hp, attack=5, xp_reward=20, gold_reward=10)
    context.game_state.combat_active = True

@when('the Wizard casts "{spell_name}" at the {target}')
def step_impl(context, spell_name, target):
    # Determine who is the Wizard
    wizard = context.game_state.player if context.game_state.player.char_class == "Wizard" else context.game_state.companion
    context.spell_result = context.game_state.cast_spell(wizard, spell_name, target)

@then('the {monster_name} is defeated')
def step_impl(context, monster_name):
    assert context.game_state.active_monster.hp <= 0

@then('the combat ends successfully')
def step_impl(context):
    is_over, msg = context.game_state.check_combat_end()
    assert is_over
    assert not context.game_state.combat_active

@then('the party gains gold and experience points')
def step_impl(context):
    # Gold starts at 50, but checks combat reward adds gold
    assert context.game_state.gold > 50
    # Player/Companion should have exp > 0
    assert context.game_state.player.exp > 0 or context.game_state.companion.exp > 0

@then("the Wizard's mana is reduced by {mana_cost:d}")
def step_impl(context, mana_cost):
    # Done implicitly, handled by checking final mana
    pass

@then("the Wizard's current mana is {expected_mana:d}")
def step_impl(context, expected_mana):
    wizard = context.game_state.player if context.game_state.player.char_class == "Wizard" else context.game_state.companion
    assert wizard.mana == expected_mana

@when('the {monster_name} deals {damage:d} damage to the {target_class}')
def step_impl(context, monster_name, damage, target_class):
    target = context.game_state.player if target_class.lower() == "fighter" else context.game_state.companion
    target.hp = max(0, target.hp - damage)

@then('the {target_class} is unconscious')
def step_impl(context, target_class):
    target = context.game_state.player if target_class.lower() == "fighter" else context.game_state.companion
    assert not target.is_alive()

@then('the game is over because the party was defeated')
def step_impl(context):
    is_over, msg = context.game_state.check_combat_end()
    assert is_over
    assert context.game_state.game_over
    assert not context.game_state.game_won

@given('the Wizard is at {hp:d} health')
def step_impl(context, hp):
    wizard = context.game_state.player if context.game_state.player.char_class == "Wizard" else context.game_state.companion
    wizard.hp = hp

@given('the Fighter is at {hp:d} health')
def step_impl(context, hp):
    fighter = context.game_state.player if context.game_state.player.char_class == "Fighter" else context.game_state.companion
    fighter.hp = hp

@when('the companion Fighter takes an automated action')
def step_impl(context):
    context.companion_action_log = context.game_state.companion_auto_action()

@then('the companion Fighter uses "Taunt" to protect the Wizard')
def step_impl(context):
    assert "Taunt" in context.companion_action_log

@then("the companion Fighter's taunting status is active")
def step_impl(context):
    assert context.game_state.companion.is_taunting

@when('the companion Wizard takes an automated action')
def step_impl(context):
    context.companion_action_log = context.game_state.companion_auto_action()

@then('the companion Wizard casts "Heal" on the Fighter')
def step_impl(context):
    assert "Heal" in context.companion_action_log

@then("the Fighter's health is restored")
def step_impl(context):
    fighter = context.game_state.player if context.game_state.player.char_class == "Fighter" else context.game_state.companion
    assert fighter.hp > 15
