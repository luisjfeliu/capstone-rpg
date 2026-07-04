# Runbook — Local End-to-End Verification

Follow these steps in order to verify the whole project on a fresh machine.
Every step lists the expected outcome so failures are obvious.

## 0. Prerequisites (once)

```bash
# Tooling
curl -LsSf https://astral.sh/uv/install.sh | sh      # uv (Python toolchain)
uv tool install google-agents-cli                    # agents-cli
# Google Cloud SDK: https://cloud.google.com/sdk/docs/install

# Auth + project (the agents call Gemini via Vertex AI with ADC - no API keys)
gcloud auth application-default login
gcloud config set project <your-project-id>          # e.g. kaggle-ai-agents-478322
```

## 1. Install dependencies

```bash
agents-cli install
```
**Expect:** `uv sync` completes without errors; `.venv/` created.

## 2. Static checks

```bash
agents-cli lint
```
**Expect:** `All checks passed!` (ruff check, ruff format, codespell, ty).

## 3. Unit + integration tests

```bash
uv run pytest tests/unit tests/integration
```
**Expect:** `15 passed`. Notes:
- `tests/integration/test_agent.py` calls the live Gemini model — needs ADC.
- `tests/integration/test_mcp_server.py` spawns `app/mcp_server.py` as a real
  stdio subprocess and round-trips MCP tool calls — no network needed.

## 4. BDD scenarios (game rules)

```bash
uv run behave
```
**Expect:** `3 features passed ... 11 scenarios passed, 59 steps passed`.

## 5. Full CLI playthrough (the demo path)

```bash
uv run python -m app.main
```

Scripted walkthrough with expected outcomes:

| Step | You do | Expect |
|---|---|---|
| 1 | (nothing) | GM greets you, sets the dungeon scene, asks you to choose Wizard or Fighter and a name |
| 2 | Type `I'll be a Wizard named Gandalf` | GM calls `select_character`, introduces Garrick the Fighter companion, presents 3 routes (left/forward/right) with difficulty and treasure; Party Status panel shows Gandalf (40 HP / 30 mana) + Garrick (60 HP) |
| 3 | Type `left` at the path prompt | GM narrates the first room; a monster appears with ASCII art in a red Combat Encounter panel |
| 4 | Choose `1` (Cast Fireball) | GM resolves the attack via `execute_cast_spell`; monster HP drops; mana drops by 10 |
| 5 | (automatic) Companion's Turn | Companion agent picks its own tactical action (attack/Taunt/Heal) and speaks in character; GM narrates it |
| 6 | (automatic) Monster's Turn | Monster attacks a party member; HP drops in status panel |
| 7 | Repeat combat until the monster dies | GM narrates rewards: XP, gold; possible level-up |
| 8 | Choose `1` (Move Forward) until the route is cleared | GM calls `execute_advance_level`; party fully healed; level counter increments; new routes presented |

Optional checks:
- Type gibberish at step 2 → after 4 rounds the CLI falls back to a direct
  class prompt (the game cannot wedge).
- Reach level 7 and clear a route → victory message; party death → game over.

## 6. MCP server smoke

```bash
uv run pytest tests/integration/test_mcp_server.py -v   # protocol round-trip
RPG_USE_MCP=1 uv run adk web app/                        # GM consumes tools over MCP
```
**Expect:** test passes; in the web UI the GM plays normally (state lives in
the MCP subprocess, so the terminal status panels don't apply here).

## 7. Evaluation (LLM-as-judge)

```bash
agents-cli eval generate    # runs the 8-case dataset against the live agent
agents-cli eval grade       # grades traces; prints score table
open artifacts/grade_results/results_*.html   # detailed judge feedback
```
**Expect:** `num_cases_error 0`, mean `custom_response_quality` ≥ 4.5/5.

## 8. Deployment smoke test (after `agents-cli deploy`)

```bash
uv run python scripts/remote_smoke.py
```
**Expect:** a narrated Game Master response streamed from the deployed
Agent Runtime instance. See [DEPLOYMENT.md](DEPLOYMENT.md).

## Troubleshooting

- **401 / credential errors** → `gcloud auth application-default login`.
- **Model 404** → check `GOOGLE_CLOUD_LOCATION` is `global` (set in
  `app/agent.py`); do not change the model name.
- **Eval grades mix old runs** → `eval grade` grades every trace file in
  `artifacts/traces/`; delete stale ones before re-grading.
