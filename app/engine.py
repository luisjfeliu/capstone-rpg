"""Deterministic game engine - the single source of truth for all game state.

Design: the LLM agents (app/agent.py) are never allowed to hold or invent
numbers. Every stat change (HP, mana, gold, XP, monster damage) happens here,
reached only through the typed tool layer in app/tools.py. This keeps the
narration free to improvise while the rules stay exact and testable - the
whole module is covered by unit tests and the Gherkin specs in features/.

State lives in the module-level `global_game_state` singleton so that the
Game Master agent, the Companion agent, and the CLI all observe one world.
"""

import random

MONSTER_ASCII = {
    "Goblin Scout": """
     ,-.
    (o.o)
     |=|
    /   \\
   /|   |\\
   `|_|_|'
   """,
    "Orc Berserker": """
      ,,,,,
     (((((((
     \\ o o /
      | - |
     /|   |\\
    / |___| \\
    """,
    "Skeleton Warrior": """
     .---.
    /     \\
   | () () |
    \\  ^  /
     |||||
     |||||
    """,
    "Cave Troll": """
      /\\_/\\
     ((@v@))
     ():::()
      V---V
     /     \\
    /|     |\\
    """,
    "Stone Golem": """
     .=====.
     |[o o]|
    /|_____|\\
     | | | |
     |_|_|_|
    """,
    "Shadow Specter": """
     .-''''-.
    /  __  __\\
   |  (o)  (o) |
   |    __    |
   |   /  \\   |
    \\  \\__/  /
     `------'
    """,
    "Dimension Guardian": """
       /\\
      /  \\
     / () \\
    /  __  \\
   |  [oo]  |
   |   __   |
    \\______/
    """,
    "Fallback": """
     ,-^-.
     |o o|
     \\_-_/
     /| |\\
    """,
}


class Character:
    def __init__(self, name: str, char_class: str, role: str):
        self.name = name
        self.char_class = char_class  # "Wizard" or "Fighter"
        self.role = role  # "player" or "companion"
        self.level = 1
        self.exp = 0
        self.max_hp = 40 if char_class == "Wizard" else 60
        self.hp = self.max_hp

        # Class specific
        if char_class == "Wizard":
            self.max_mana = 30
            self.mana = self.max_mana
            self.intelligence = 15
            self.strength = 5
        else:  # Fighter
            self.max_mana = 0
            self.mana = 0
            self.intelligence = 5
            self.strength = 15

        self.defense_buff = 0
        self.is_taunting = False

    def is_alive(self) -> bool:
        return self.hp > 0

    def restore_all(self):
        self.hp = self.max_hp
        if self.char_class == "Wizard":
            self.mana = self.max_mana
        self.defense_buff = 0
        self.is_taunting = False

    def gain_xp(self, amount: int) -> bool:
        """Gains XP, returns True if leveled up."""
        self.exp += amount
        xp_needed = self.level * 100
        leveled_up = False
        while self.exp >= xp_needed:
            self.exp -= xp_needed
            self.level += 1
            # Raise stats
            self.max_hp = int(self.max_hp * 1.15)
            self.hp = self.max_hp
            if self.char_class == "Wizard":
                self.max_mana = int(self.max_mana * 1.15)
                self.mana = self.max_mana
                self.intelligence = int(self.intelligence * 1.15)
            else:
                self.strength = int(self.strength * 1.15)
            xp_needed = self.level * 100
            leveled_up = True
        return leveled_up


class Monster:
    def __init__(
        self, name: str, hp: int, attack: int, xp_reward: int, gold_reward: int
    ):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.xp_reward = xp_reward
        self.gold_reward = gold_reward

    def is_alive(self) -> bool:
        return self.hp > 0


class Route:
    def __init__(
        self,
        direction: str,
        length: int,
        difficulty: str,
        monster_types: list[str],
        treasure: str,
        xp_mult: float,
    ):
        self.direction = direction  # "left", "forward", "right"
        self.length = length  # number of rooms/sections
        self.difficulty = difficulty  # "easy", "medium", "hard"
        self.monster_types = monster_types
        self.treasure = treasure
        self.xp_mult = xp_mult


class GameState:
    def __init__(self):
        self.player: Character | None = None
        self.companion: Character | None = None
        self.current_level = 1
        self.gold = 50
        self.inventory: list[str] = ["Health Potion", "Mana Potion"]

        self.routes: dict[str, Route] = {}
        self.selected_route: Route | None = None
        self.current_room_index = 0

        self.active_monster: Monster | None = None
        self.combat_active = False
        self.combat_turn = "player"  # "player", "companion", "monster"
        self.combat_log: list[str] = []
        self.game_over = False
        self.game_won = False

    def select_character(
        self, player_class: str, player_name: str
    ) -> tuple[Character, Character]:
        """Initializes the player and companion classes."""
        if player_class.lower() == "wizard":
            self.player = Character(player_name, "Wizard", "player")
            self.companion = Character("Garrick", "Fighter", "companion")
        else:
            self.player = Character(player_name, "Fighter", "player")
            self.companion = Character("Eldrin", "Wizard", "companion")
        return self.player, self.companion

    def get_party(self) -> list[Character]:
        return [self.player, self.companion]

    def generate_level_routes(self):
        """Generates the left, forward, and right paths for the current level."""
        level = self.current_level
        # Difficulty settings
        difficulty_map = {
            1: [("left", 2, "easy"), ("forward", 3, "medium"), ("right", 4, "hard")],
            2: [("left", 3, "easy"), ("forward", 4, "medium"), ("right", 3, "hard")],
            3: [("left", 4, "easy"), ("forward", 3, "medium"), ("right", 5, "hard")],
            4: [("left", 3, "easy"), ("forward", 5, "medium"), ("right", 4, "hard")],
            5: [("left", 4, "easy"), ("forward", 4, "medium"), ("right", 6, "hard")],
            6: [("left", 5, "easy"), ("forward", 6, "medium"), ("right", 5, "hard")],
            7: [("left", 4, "medium"), ("forward", 5, "hard"), ("right", 6, "hard")],
        }

        routes_data = difficulty_map[level]

        # Monster pools by difficulty
        monsters_by_diff = {
            "easy": ["Goblin Scout", "Skeleton Warrior"],
            "medium": ["Orc Berserker", "Shadow Specter"],
            "hard": ["Cave Troll", "Stone Golem"],
        }
        if level == 7:
            monsters_by_diff["hard"].append("Dimension Guardian")

        self.routes = {}
        for direction, length, diff in routes_data:
            monsters = [
                random.choice(monsters_by_diff[diff]) for _ in range(length - 1)
            ]
            # Last room has the mini-boss or exit guardian
            if level == 7 and diff == "hard":
                monsters.append("Dimension Guardian")
            else:
                monsters.append(random.choice(monsters_by_diff[diff]))

            # Treasure logic
            gold_amount = level * (
                20 if diff == "easy" else 40 if diff == "medium" else 80
            )
            item = (
                "Health Potion"
                if diff == "easy"
                else "Mana Potion"
                if diff == "medium"
                else "Elixir of Life"
            )
            treasure_desc = f"{gold_amount} Gold and a {item}"

            self.routes[direction] = Route(
                direction=direction,
                length=length,
                difficulty=diff,
                monster_types=monsters,
                treasure=treasure_desc,
                xp_mult=1.0 if diff == "easy" else 1.3 if diff == "medium" else 1.6,
            )

    def choose_route(self, direction: str):
        if direction not in self.routes:
            raise ValueError(f"Invalid route: {direction}")
        self.selected_route = self.routes[direction]
        self.current_room_index = 0
        self.combat_active = False

    def enter_next_room(self) -> tuple[str, bool]:
        """Enters the next room in the selected route.
        Returns a description of what is in the room and whether it spawns a combat."""
        if not self.selected_route:
            raise ValueError("No route selected.")

        if self.current_room_index >= self.selected_route.length:
            return "You have reached the end of the path.", False

        monster_name = self.selected_route.monster_types[self.current_room_index]
        self.current_room_index += 1

        # Generate monster stats based on level and route difficulty
        level_mult = self.current_level
        diff = self.selected_route.difficulty
        diff_mult = 1.0 if diff == "easy" else 1.4 if diff == "medium" else 1.8

        hp = int(25 * level_mult * diff_mult)
        attack = int(6 * level_mult * diff_mult)
        xp = int(35 * level_mult * diff_mult)
        gold = int(15 * level_mult * diff_mult)

        if monster_name == "Dimension Guardian":
            hp = int(hp * 1.5)
            attack = int(attack * 1.3)
            xp = int(xp * 2)
            gold = int(gold * 2)

        self.active_monster = Monster(monster_name, hp, attack, xp, gold)
        self.combat_active = True
        self.combat_turn = "player"
        self.combat_log = [f"A wild {monster_name} appears! Combat starts!"]

        # Reset defense buffs / taunt
        self.player.defense_buff = 0
        self.player.is_taunting = False
        self.companion.defense_buff = 0
        self.companion.is_taunting = False

        return f"Room {self.current_room_index}: You encounter a {monster_name}!", True

    def cast_spell(self, caster: Character, spell_name: str, target: str) -> str:
        """Resolves spell casting."""
        if caster.char_class != "Wizard":
            return f"{caster.name} is not a Wizard and cannot cast spells."

        spell_name = spell_name.capitalize()

        if spell_name == "Fireball":
            cost = 10
            if caster.mana < cost:
                return f"{caster.name} does not have enough mana to cast Fireball!"
            caster.mana -= cost
            damage = int(caster.intelligence * 1.5)
            if self.active_monster:
                self.active_monster.hp -= damage
                return f"{caster.name} casts Fireball at {target}, dealing {damage} magic damage!"
            return f"{caster.name} casts Fireball, but there is no enemy to target."

        elif spell_name == "Heal":
            cost = 8
            if caster.mana < cost:
                return f"{caster.name} does not have enough mana to cast Heal!"
            caster.mana -= cost
            heal_val = int(caster.intelligence * 1.2)

            # Find heal target
            heal_target = (
                self.player
                if target.lower() == self.player.name.lower()
                or target.lower() == "player"
                else self.companion
            )
            heal_target.hp = min(heal_target.max_hp, heal_target.hp + heal_val)
            return f"{caster.name} casts Heal on {heal_target.name}, restoring {heal_val} HP!"

        elif spell_name == "Shield":
            cost = 5
            if caster.mana < cost:
                return f"{caster.name} does not have enough mana to cast Shield!"
            caster.mana -= cost

            shield_target = (
                self.player
                if target.lower() == self.player.name.lower()
                or target.lower() == "player"
                else self.companion
            )
            shield_target.defense_buff += 5
            return f"{caster.name} casts Shield on {shield_target.name}, increasing defense by 5!"

        return f"Unknown spell: {spell_name}"

    def weapon_attack(self, attacker: Character, target: str) -> str:
        """Resolves standard weapon attack."""
        if not self.active_monster:
            return f"{attacker.name} attacks, but there is no monster."

        damage = attacker.strength
        if attacker.char_class == "Fighter":
            # 20% chance of critical hit
            if random.random() < 0.2:
                damage = int(damage * 1.8)
                self.active_monster.hp -= damage
                return f"{attacker.name} performs a critical weapon attack at {target}, dealing {damage} physical damage!"

        self.active_monster.hp -= damage
        return f"{attacker.name} attacks {target} with their weapon, dealing {damage} physical damage!"

    def companion_auto_action(self) -> str:
        """Automated logic for the NPC companion."""
        c = self.companion
        if not c.is_alive():
            return f"{c.name} is unconscious."

        if c.char_class == "Fighter":
            # Fighter priority:
            # 1. If player (Wizard) is low HP (< 35%), use Taunt to protect them.
            # 2. Otherwise attack the monster.
            if self.player.hp < (self.player.max_hp * 0.35) and not c.is_taunting:
                c.is_taunting = True
                return f"{c.name} uses Taunt, drawing the enemy's attention to protect {self.player.name}!"
            else:
                return self.weapon_attack(c, self.active_monster.name)
        else:  # Wizard
            # Wizard priority:
            # 1. If companion (Fighter) or player is below 40% HP and mana >= 8, cast Heal.
            # 2. If mana >= 10, cast Fireball.
            # 3. Else standard staff attack.
            if self.player.hp < (self.player.max_hp * 0.40) and c.mana >= 8:
                return self.cast_spell(c, "Heal", self.player.name)
            elif c.hp < (c.max_hp * 0.40) and c.mana >= 8:
                return self.cast_spell(c, "Heal", c.name)
            elif c.mana >= 10:
                return self.cast_spell(c, "Fireball", self.active_monster.name)
            else:
                return self.weapon_attack(c, self.active_monster.name)

    def monster_attack(self) -> str:
        """Monster attacks a target."""
        if not self.active_monster or not self.active_monster.is_alive():
            return "The monster is dead."

        # Determine target
        if self.player.is_taunting:
            target = self.player
        elif self.companion.is_taunting:
            target = self.companion
        else:
            # 50/50 target distribution
            target = self.player if random.random() < 0.5 else self.companion

        # Clear taunt states after monster turn
        self.player.is_taunting = False
        self.companion.is_taunting = False

        # Compute damage
        damage = max(1, self.active_monster.attack - target.defense_buff)
        target.hp = max(0, target.hp - damage)

        # Clear temporary defense buffs
        target.defense_buff = max(0, target.defense_buff - 3)

        return f"The {self.active_monster.name} attacks {target.name}, dealing {damage} damage!"

    def use_potion(self, character: Character, potion_name: str) -> str:
        if potion_name not in self.inventory:
            return f"No {potion_name} in inventory!"

        self.inventory.remove(potion_name)
        if potion_name == "Health Potion":
            heal = int(character.max_hp * 0.5)
            character.hp = min(character.max_hp, character.hp + heal)
            return f"{character.name} uses a Health Potion, restoring {heal} HP!"
        elif potion_name == "Mana Potion":
            if character.char_class != "Wizard":
                return f"{character.name} drank the Mana Potion, but felt no magical restoration."
            mana_res = 15
            character.mana = min(character.max_mana, character.mana + mana_res)
            return f"{character.name} uses a Mana Potion, restoring {mana_res} Mana!"
        elif potion_name == "Elixir of Life":
            character.hp = character.max_hp
            if character.char_class == "Wizard":
                character.mana = character.max_mana
            return f"{character.name} uses the Elixir of Life, fully restoring health and mana!"
        return f"Unknown item: {potion_name}"

    def check_combat_end(self) -> tuple[bool, str]:
        """Checks if combat is over. Returns (is_over, message)"""
        if not self.active_monster:
            return True, "No active combat."

        if not self.player.is_alive() or not self.companion.is_alive():
            self.combat_active = False
            self.game_over = True
            return True, "Your party has been defeated. Game Over."

        if not self.active_monster.is_alive():
            self.combat_active = False
            # Distribute rewards
            xp = self.active_monster.xp_reward
            gold = self.active_monster.gold_reward
            self.gold += gold

            p_level = self.player.gain_xp(xp)
            c_level = self.companion.gain_xp(xp)

            msg = f"The {self.active_monster.name} has been defeated! Each party member gains {xp} XP. Found {gold} gold."
            if p_level:
                msg += f" {self.player.name} leveled up to {self.player.level}!"
            if c_level:
                msg += f" {self.companion.name} leveled up to {self.companion.level}!"

            # If last room of the level was cleared, award level treasure
            if (
                self.selected_route
                and self.current_room_index >= self.selected_route.length
            ):
                # Add route rewards
                treasure_desc = self.selected_route.treasure
                # Parse gold and items from treasure_desc
                # (e.g. "80 Gold and a Health Potion")
                gold_award = int(treasure_desc.split()[0])
                item_award = " ".join(treasure_desc.split()[3:])
                self.gold += gold_award
                if item_award and item_award != "and a":
                    self.inventory.append(item_award)
                msg += f"\nPath Complete! You find the level treasure: {treasure_desc}."

            self.active_monster = None
            return True, msg

        return False, ""

    def next_level(self) -> tuple[bool, str]:
        """Attempts to advance to the next level."""
        if self.current_level >= 7:
            self.game_won = True
            self.game_over = True
            return (
                True,
                "You step through the portal on level 7 and cross into another dimension! You have won the game!",
            )

        self.current_level += 1
        # Fully restore party on level advance
        self.player.restore_all()
        self.companion.restore_all()
        self.selected_route = None
        self.current_room_index = 0
        self.generate_level_routes()
        return (
            False,
            f"You advance to level {self.current_level}. The party is fully healed and rested.",
        )


global_game_state = GameState()
