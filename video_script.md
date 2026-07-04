# Demo Video Script (≤ 5 minutes, YouTube)

Rubric targets: problem statement · why agents · architecture · demo · the build.
Record the terminal at a large font size; have the README architecture diagram
and the eval HTML report open in browser tabs beforehand.

## Shot list

### 1. Problem (0:00–0:30)
Face/voiceover over title slide or README header.
> "Tabletop RPGs need a Game Master who improvises a story AND enforces the
> rules. LLMs are great improvisers but terrible accountants — they hallucinate
> hit points and let you talk your way out of dying. I built a dungeon crawl
> where two Gemini agents narrate and play alongside you, while a deterministic
> game engine keeps every number honest."

### 2. Why agents + architecture (0:30–1:30)
Show the mermaid diagram in README.md.
> "Two ADK agents: a Game Master that narrates and referees, and an NPC
> companion that makes its own tactical decisions. Neither can touch the game
> state directly — they act only through a typed tool layer over a pure-Python
> engine. The same engine is also exposed as an MCP server, so any MCP client
> can play the dungeon. Narration is creative; the math never drifts."

### 3. Live demo (1:30–3:30) — `uv run python -m app.main`
- **(1:30)** Launch. The GM greets you and asks you to choose a character.
  Say: "Notice the agent initiates — this isn't a menu, it's a conversation."
- **(1:50)** Type: `I'll be a Wizard named Gandalf`. Point out the GM calling
  the select_character tool, introducing Garrick the Fighter, and presenting
  three routes with improvised theming; show the Party Status panel.
- **(2:20)** Type `left`. Combat starts — zoom on the ASCII monster art and
  HP/attack stats panel.
- **(2:40)** Choose `1` (Cast Fireball). GM resolves damage via tools; mana
  drops by exactly 10 in the status panel: "the engine did that, not the LLM."
- **(3:00)** **The multi-agent moment**: the Companion's Turn fires. The
  companion agent reads the party state, picks a cooperative action (Taunt or
  Heal if you're hurt), and speaks in character; the GM then narrates it.
  Say: "That decision came from a second agent with its own instruction."
- **(3:20)** Monster's turn hits back; show HP dropping; if the monster dies,
  show XP/gold rewards.

### 4. The build (3:30–4:40)
Quick IDE walkthrough, ~15s per stop:
- `features/cooperative_play.feature` — "The game rules were specified in
  Gherkin BEFORE the code — behave runs 11 scenarios, 59 steps, all green."
- `app/agent.py` — the two Agent definitions and the tool list.
- `app/mcp_server.py` — "the whole engine as an MCP server, same nine tools."
- Eval HTML report (`artifacts/grade_results/results_*.html`) — "an LLM judge
  grades the live agent on 8 game scenarios. The eval loop caught the GM
  asking for confirmation instead of acting — two instruction fixes took the
  score from 4.1 to 4.9 out of 5."
- Terminal: `agents-cli deploy` output / DEPLOYMENT.md — "deployed to Vertex
  AI Agent Runtime with one command; a smoke script queries it live."

### 5. Close (4:40–5:00)
> "Multi-agent ADK, an MCP server, evals as regression tests, and a one-command
> deployment — all in a game you can actually lose. Repo link below. Thanks!"

## Recording checklist
- [ ] Terminal font ≥ 16pt, dark theme, window ~100 columns.
- [ ] Pre-run `agents-cli install` and one warm-up game (model latency).
- [ ] Have README diagram + eval HTML open in tabs.
- [ ] Keep each GM turn on screen ≥ 3 seconds before advancing.
- [ ] Upload to YouTube (public or unlisted), attach to Kaggle Writeup media
      gallery along with a cover image.
