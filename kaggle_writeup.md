# Dungeon of the Forgotten King — a Cooperative Multi-Agent RPG in Your Terminal

*Two Gemini agents — an improvising Game Master and a tactical NPC companion — run a rules-honest dungeon crawl on top of a deterministic game engine, specified with BDD, measured with LLM-as-judge evals, and deployed to Vertex AI Agent Runtime.*

**Track:** Freestyle

---

## The problem

Tabletop role-playing games need a Game Master: someone who improvises a living story *and* referees the rules fairly. That second half is where pure-LLM "AI dungeon" experiences fall apart. Left to narrate freely, a language model hallucinates hit points, forgets your inventory between scenes, and lets a persuasive player talk their way out of dying. The result is charming for five minutes and unsatisfying as a *game*, because nothing is really at stake.

The interesting engineering problem underneath is general and reaches far beyond games: **how do you combine an LLM's creative, conversational strengths with hard state and rules that must never drift?** The same tension appears in customer-service agents that must respect account balances and business workflows that must respect ledgers. A dungeon crawl is a perfect, self-contained testbed — the "business rules" are combat math, and every violation is immediately visible to the player.

## Why agents?

A single chat prompt cannot solve this, because the failure mode *is* the LLM holding state. Our solution needs three properties that map directly onto agent architecture:

1. **Tool-mediated state.** The model must be able to *act* on the world (create characters, resolve attacks, spend mana) but only through typed, validated operations — never by asserting numbers in prose.
2. **Multiple minds.** A cooperative RPG has genuinely different roles with different incentives: the Game Master narrates and referees; the companion NPC is a party member who should make *its own* tactical choices, not just echo the GM. Two agents with separate instructions produce visibly different, believable behavior.
3. **A measurable contract.** "Is the GM good?" must be testable — both the deterministic rules (classic tests) and the narrative quality (LLM-as-judge evaluation).

The Google Agent Development Kit gives all three: `Agent` definitions with per-agent instructions, function tools, and an eval harness through `agents-cli`.

## Architecture

```
Player (terminal, rich UI)
   │  free text + menu choices
   ▼
Game Master agent (ADK root_agent, Gemini) ◄── narrates companion's turn
   │                                                     ▲
   │ tool calls                                          │ own tool calls
   ▼                                                     │
Typed tool layer (app/tools.py) ◄──────── Companion agent (ADK, Gemini)
   │
   ▼
Deterministic game engine (app/engine.py)
HP · mana · gold · XP · routes · monsters · combat math
```

**The engine** (`app/engine.py`) is plain Python and owns every number: character stats, level-scaled monster generation, spell costs, taunt/targeting rules, XP curves, treasure. It has no LLM dependency and is fully covered by unit tests and Gherkin BDD scenarios.

**The tool layer** (`app/tools.py`) is the only door between agents and engine: `select_character`, `get_game_status`, `get_available_routes`, `select_route`, `enter_room`, `execute_weapon_attack`, `execute_cast_spell`, `execute_taunt`, `execute_use_item`, `execute_advance_level`. Each validates inputs and returns structured results, so a hallucinated spell name becomes a polite error object, not corrupted state.

**The Game Master agent** initiates the whole experience: it greets the player, sets the scene, and asks them to choose a character in natural language ("I'll be a Wizard named Gandalf"), then calls `select_character`, introduces the companion, and presents three route choices per dungeon level with improvised theming. Its instruction explicitly forbids inventing HP/mana values that differ from tool results.

**The Companion agent** is the multi-agent payoff. Each combat round it independently reads the party state and decides: Taunt to pull aggro off a fragile ally, Heal below 40% HP, Fireball when the party is safe, otherwise attack — then delivers an in-character line ("I will draw their attention!"). The GM narrates the companion's chosen action back into the shared story. Because both agents act through the same engine, they can never contradict each other's numbers.

**MCP server.** The entire engine is additionally exposed as a Model Context Protocol server (`app/mcp_server.py`, FastMCP over stdio) registering the same ten tool functions — zero logic duplication. Setting `RPG_USE_MCP=1` switches the GM from in-process tools to consuming the engine through ADK's `MCPToolset`, and an integration test drives the server over the real stdio protocol. The dungeon is now a service any MCP client can play.

## How it was built (the vibe-coding story)

The project was built specification-first with AI pair-programming, using the course's toolchain end to end:

1. **Scaffold** — `agents-cli scaffold create` generated the ADK project, test layout, telemetry wiring, and Terraform.
2. **BDD before behavior** — the game rules were written as Gherkin feature files (`features/*.feature`) *before* the engine: character creation, route generation and difficulty tiers, mana costs, defeat conditions, victory on level 7, and — most importantly — the companion's cooperative logic ("NPC Fighter protects low-health Wizard"). `behave` executes 11 scenarios / 59 steps, all green.
3. **Engine + tools + agents** — implemented against those specs, iterating in `agents-cli playground`.
4. **The evaluation loop** — an 8-case eval dataset covers the full arc: opening greeting, character selection, route description, multi-step commands, combat resolution, companion-turn narration, status queries, and graceful rejection of an invalid class ("I want to play as a Bard"). `agents-cli eval generate` runs the live agent; `agents-cli eval grade` applies an LLM judge with a custom response-quality rubric.

That loop caught real behavioral bugs. The first graded run scored **4.125/5**: the judge flagged that the GM asked for confirmation instead of executing multi-step commands ("create a Wizard, then take the left path…") and that it rigidly presented routes after character creation even when the player had asked for something else. Two targeted instruction changes raised the same dataset to **4.875/5**. Playtesting later exposed the GM narrating hallucinated HP numbers that contradicted the live status panel; a "never invent numbers — describe condition qualitatively" rule fixed it (**5.0/5**) — and when that rule over-fired and suppressed legitimate status reports, the eval suite caught the regression at 1.0/5 on the status-query case, which a sharpened rule fixed the same day (**4.875–5.0/5** across runs). Evals-as-regression-tests, working as advertised.

Classic testing runs alongside: 15 pytest cases (engine math, tool validation, a live agent streaming test, the MCP round-trip) and `agents-cli lint` (ruff, formatting, codespell, type checking) all pass clean.

## Deployment

The GM agent is deployed to **Vertex AI Agent Runtime** with `agents-cli deploy`, wrapped by an `AgentEngineApp` that adds Cloud Trace telemetry, Cloud Logging, and a feedback-registration operation. A smoke-test script queries the deployed runtime and streams back live narration. Full reproduction steps — including the honest limitation that game state is in-memory per runtime instance — are in the repo's `DEPLOYMENT.md`. No API keys exist anywhere in the project; all auth is Application Default Credentials.

## Results

- **Playable game**: a complete 7-level dungeon crawl in the terminal — GM-initiated character creation in natural language, ASCII-art monsters, three-way route choices, potions, XP/leveling, and a companion that visibly saves your life.
- **Rules that hold**: 11/11 BDD scenarios and 15/15 tests green; the LLM never owns a number.
- **Measured quality**: LLM-judge score improved 4.125 → 4.875/5 through the eval loop, with the judge's feedback directly driving instruction fixes.
- **Four course concepts in production**: multi-agent ADK system, MCP server, deployability (Agent Runtime), and agents-cli skills across scaffold/lint/eval/deploy.

**Links:** public repository — https://github.com/luisjfeliu/capstone-rpg — and demo video are attached to this writeup.
