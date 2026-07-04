Feature: Cooperative Play
  The player and the NPC companion must cooperate
  The companion must make rational cooperative choices

  Scenario: NPC Fighter protects low-health Wizard
    Given a new game starts
    And the player chooses "Wizard" and names themselves "Gandalf"
    And the Wizard is at 10 health
    When the companion Fighter takes an automated action
    Then the companion Fighter uses "Taunt" to protect the Wizard
    And the companion Fighter's taunting status is active

  Scenario: NPC Wizard heals injured Fighter player
    Given a new game starts
    And the player chooses "Fighter" and names themselves "Aragorn"
    And the Fighter is at 15 health
    When the companion Wizard takes an automated action
    Then the companion Wizard casts "Heal" on the Fighter
    And the Fighter's health is restored
