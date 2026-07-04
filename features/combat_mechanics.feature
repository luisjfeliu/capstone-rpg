Feature: Combat Mechanics
  As the party explores the dungeon, they face monsters
  The combat rules must resolve correctly

  Scenario: Winning a combat and receiving rewards
    Given a new game starts
    And the player chooses "Wizard" and names themselves "Gandalf"
    And they enter a combat with a "Goblin Scout" having 10 HP
    When the Wizard casts "Fireball" at the Goblin Scout
    Then the Goblin Scout is defeated
    And the combat ends successfully
    And the party gains gold and experience points

  Scenario: Casting spells consumes mana
    Given a new game starts
    And the player chooses "Wizard" and names themselves "Gandalf"
    And they enter a combat with an "Orc Berserker" having 40 HP
    When the Wizard casts "Fireball" at the Orc Berserker
    Then the Wizard's mana is reduced by 10
    And the Wizard's current mana is 20

  Scenario: Defeat when health reaches zero
    Given a new game starts
    And the player chooses "Fighter" and names themselves "Aragorn"
    And they enter a combat with a "Cave Troll" having 100 HP
    When the Cave Troll deals 100 damage to the Fighter
    Then the Fighter is unconscious
    And the game is over because the party was defeated
