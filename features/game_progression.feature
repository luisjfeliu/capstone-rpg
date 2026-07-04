Feature: Game Progression and Path Selection
  As a player
  I want to choose paths across 7 levels
  So that I can reach the portal to another dimension on level 7

  Scenario: Starting the game and choosing a class
    Given a new game starts
    When the player chooses "Wizard" and names themselves "Gandalf"
    Then the player character is a "Wizard" named "Gandalf" with health 40 and mana 30
    And the companion character is a "Fighter" named "Garrick" with health 60 and level 1

  Scenario: Level generation and route choice
    Given the party is on level 1
    When the GM generates the routes
    Then three paths are available: "left", "forward", and "right"
    And the paths have different difficulties: "left" is "easy", "forward" is "medium", "right" is "hard"

  Scenario: Advancing levels without dying
    Given the party is on level 1
    And the GM generates the routes
    When they select the "left" route
    And they successfully clear all rooms in the route
    And they advance to the next level
    Then the party is on level 2
    And the player and companion health is fully restored

  Scenario: Reaching the final portal
    Given the party is on level 7
    And the GM generates the routes
    And they select the "left" route
    When they successfully clear all rooms in the route
    And they advance to the next level
    Then the game is won and the story concludes

  Scenario: The GM creates the party through the select_character tool
    Given the game engine state is reset
    When the GM calls the select_character tool with class "Wizard" and name "Gandalf"
    Then the tool reports success
    And the global party has a "Wizard" player named "Gandalf" and companion "Garrick" the "Fighter"

  Scenario: The select_character tool rejects an unknown class
    Given the game engine state is reset
    When the GM calls the select_character tool with class "Bard" and name "Lute"
    Then the tool reports an error and no party is created
