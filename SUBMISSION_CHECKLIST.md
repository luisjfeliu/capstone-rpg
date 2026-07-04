# Kaggle Capstone Project: Submission Checklist

Track: **Freestyle** · Deadline: **July 6, 2026, 11:59 PM PT**

A valid submission = Kaggle Writeup (≤ 2,500 words, with a selected track) +
Media Gallery (cover image required, video required) + attached public video +
attached public project link. Judging: 30 pts pitch (concept/video/writeup) +
70 pts implementation (50 technical, 20 documentation). Must demonstrate ≥ 3
course concepts — this project demonstrates 4: **multi-agent ADK system, MCP
server, deployability, and agents-cli skills**.

---

## 1. Codebase (GitHub) — DONE except push
- [x] **README.md**: problem, multi-agent design + architecture diagram,
  quickstart (`agents-cli install`, `uv run python -m app.main`), tests
  (`uv run behave`, `uv run pytest tests/unit tests/integration`), evals
  (`agents-cli eval generate` + `agents-cli eval grade`), security notes.
- [x] **Code quality**: `agents-cli lint` passes clean (ruff, format,
  codespell, ty). Design comments in `app/agent.py`, `app/engine.py`,
  `app/mcp_server.py`, `app/tools.py`.
- [x] **No secrets**: ADC-only auth; no API keys or credentials tracked.
- [x] **Public GitHub repository**: https://github.com/luisjfeliu/capstone-rpg
  (pushed and verified publicly accessible).

## 2. Evaluation & testing evidence — DONE
- [x] `uv run behave` → **3 features, 11 scenarios, 59 steps — all passing**.
- [x] `uv run pytest tests/unit tests/integration` → **20 passed** (engine,
  tools, live agent stream, MCP stdio round-trip).
- [x] `agents-cli eval generate` + `agents-cli eval grade` → mean
  **custom_response_quality 4.875/5** over 8 cases, 0 errors
  (`artifacts/grade_results/results_*.html`). First run scored 4.125; two
  instruction fixes driven by judge feedback raised it — include this
  iteration story in the writeup.
- [ ] Screenshot the behave summary and the eval HTML report for the writeup.

## 3. Deployment (adds Implementation Quality points)
- [x] `agents-cli deploy --project kaggle-ai-agents-478322` → Vertex AI Agent
  Runtime; runtime ID recorded in `deployment_metadata.json`.
- [x] Remote smoke test: `uv run python scripts/remote_smoke.py` returns live
  GM narration from the deployed runtime.
- [x] Reproduction documented in `DEPLOYMENT.md` (judges reward reproducible
  deployment docs; a live public endpoint is NOT required).

## 4. Video (≤ 5 minutes, YouTube) — USER ACTION
- [ ] Record per `video_script.md`: problem (30s) → why agents + architecture
  (60s) → live CLI demo with GM-initiated character choice, ASCII combat, and
  the companion's cooperative turn (2m) → build walkthrough: Gherkin specs,
  eval report, deploy (70s) → close (20s).
- [ ] Upload to YouTube (public or unlisted).

## 5. Kaggle Writeup + submission — USER ACTION
- [ ] Create the Writeup from `kaggle_writeup.md` (title, subtitle, ≤ 2,500
  words); **select the Freestyle track** (required to submit).
- [ ] Media Gallery: attach a **cover image** (required) + the video.
- [ ] Attach the **public project link** (GitHub repo URL — includes setup
  instructions, satisfying the "detailed setup instructions" requirement).
- [ ] Click **Submit** (a saved draft does not count) before
  **July 6, 2026, 11:59 PM PT**.
