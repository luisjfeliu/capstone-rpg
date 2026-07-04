"""Smoke test for the deployed Agent Runtime instance.

Reads the runtime ID written by `agents-cli deploy` into
deployment_metadata.json, sends one Game Master prompt, and prints the
streamed response. Exits non-zero if no narrated text comes back.

Run with: uv run python scripts/remote_smoke.py
"""

import json
import sys
from pathlib import Path

import vertexai
from vertexai import agent_engines

PROMPT = (
    "A new adventurer has arrived at the dungeon entrance. "
    "Greet them and ask them to choose their character."
)


def main() -> int:
    metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
    metadata = json.loads(metadata_path.read_text())
    resource_name = metadata.get("remote_agent_runtime_id")
    if not resource_name or resource_name == "None":
        print(
            "No deployment found in deployment_metadata.json - run `agents-cli deploy` first."
        )
        return 1

    project = resource_name.split("/")[1]
    location = resource_name.split("/")[3]
    vertexai.init(project=project, location=location)

    print(f"Querying deployed agent: {resource_name}\n")
    agent = agent_engines.get(resource_name)

    got_text = False
    for event in agent.stream_query(user_id="smoke_test_user", message=PROMPT):
        parts = (
            (event.get("content") or {}).get("parts", [])
            if isinstance(event, dict)
            else []
        )
        for part in parts:
            text = part.get("text")
            if text:
                got_text = True
                print(text)

    if not got_text:
        print("FAIL: no narrated text returned from the deployed agent.")
        return 1
    print("\nSmoke test PASSED - the deployed Game Master responded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
