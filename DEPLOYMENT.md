# Deployment — Vertex AI Agent Runtime

The Game Master agent deploys to **Vertex AI Agent Runtime** (Gemini
Enterprise Agent Platform). These steps reproduce the deployment from a fresh
clone. No API keys are involved anywhere — all auth is Application Default
Credentials.

## Prerequisites

- A GCP project with billing enabled (this project used
  `kaggle-ai-agents-478322`, region `us-east1` from
  `agents-cli-manifest.yaml`).
- APIs: Vertex AI (`aiplatform.googleapis.com`) — `agents-cli` enables what it
  needs on first deploy.
- Local tooling: `uv`, `google-agents-cli` (`uv tool install
  google-agents-cli`), gcloud SDK.

```bash
gcloud auth application-default login
gcloud config set project <your-project-id>
agents-cli install
```

> **Python version matters.** The remote build mirrors the interpreter that
> runs the deploy — and that is the **`agents-cli` tool venv**, not just this
> repo's venv. A transitive dependency (`litellm`) does not support Python
> 3.14 yet, so a 3.14 interpreter fails the remote build with
> `No matching distribution found for litellm`. Two pins keep this working:
>
> ```bash
> uv tool install --force --python 3.13 'google-agents-cli==0.5.0'  # the deployer
> # repo side: .python-version pins 3.13 (already committed)
> ```
>
> The `==0.5.0` matters too: this project is scaffolded for agents-cli 0.5.0;
> agents-cli 1.0.0 switched `agent_runtime` deploys to a Dockerfile-based
> flow this project does not use (run `agents-cli scaffold upgrade` if you
> want to migrate instead).
>
> If a deploy fails with the opaque "Build failed ... requirements.txt"
> message, the real error is in Cloud Logging under log name
> `aiplatform.googleapis.com/reasoning_engine_build` (not Cloud Build).

## Deploy

```bash
agents-cli deploy --project <your-project-id>
```

What happens:
- The app is packaged from `app/` (entrypoint `app/agent_runtime_app.py`,
  which wraps the ADK app with Cloud Logging, Cloud Trace/OpenTelemetry, and
  a `register_feedback` operation).
- An Agent Runtime (reasoning engine) is created — takes 5–10 minutes.
- The runtime resource name is written to `deployment_metadata.json`.

## Verify (smoke test)

```bash
uv run python scripts/remote_smoke.py
```

Expected: the deployed Game Master streams back a greeting that asks you to
choose a Wizard or Fighter, proving the agent + tools run remotely.

To check status or list deployments:

```bash
agents-cli deploy --status
agents-cli deploy --list
```

## Observability

Built-in telemetry exports to Cloud Trace and Cloud Logging (see
`app/app_utils/telemetry.py`). Optional BigQuery analytics and log sinks can
be provisioned with the Terraform in `deployment/terraform/single-project`.

## Known limitations (by design, documented honestly)

- **Game state is in-memory per runtime instance.** The engine's
  `global_game_state` singleton lives in the serving process; concurrent
  users or instance restarts do not share a dungeon. Production would move
  state to ADK session state or Firestore keyed by session ID — out of scope
  for this capstone demo.
- The deployed surface is the **Game Master agent** (the `root_agent` of the
  ADK app). The terminal UI and the companion-turn choreography live in the
  local CLI (`app/main.py`).

## Teardown

```bash
# Delete the runtime when done (avoids idle-instance cost - min_instances=1):
uv run python -c "
import json, vertexai
from vertexai import agent_engines
rn = json.load(open('deployment_metadata.json'))['remote_agent_runtime_id']
vertexai.init(project=rn.split('/')[1], location=rn.split('/')[3])
agent_engines.delete(rn)
print('deleted', rn)
"
```
