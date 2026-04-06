#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

DISCOVERY_PATH = Path(
    sys.argv[1] if len(sys.argv) > 1 else "/opt/openclaw/runtime/03-oci-genai-chat-models.json"
)
OPENCLAW_BIN = sys.argv[2] if len(sys.argv) > 2 else "/home/opc/.npm-global/bin/openclaw"

with DISCOVERY_PATH.open("r", encoding="utf-8") as f:
    discovery = json.load(f)

regions = discovery.get("regions", [])
if not isinstance(regions, list) or not regions:
    print("ERROR: No usable regions found in discovery output", file=sys.stderr)
    sys.exit(1)

region = regions[0]
chat_completions = region.get("chatCompletions", {})
if not isinstance(chat_completions, dict):
    print("ERROR: chatCompletions section is missing or invalid", file=sys.stderr)
    sys.exit(1)

models = chat_completions.get("models", [])
if not isinstance(models, list) or not models:
    print("ERROR: No chatCompletions models found in discovery output", file=sys.stderr)
    sys.exit(1)

primary_model = models[0]

model_map = {
    model: {"alias": model}
    for model in models
}

batch_payload = [
    {
        "path": "agents.defaults.models",
        "value": model_map
    }
]

subprocess.run(
    [OPENCLAW_BIN, "config", "set", "agents.defaults.model", primary_model],
    check=True,
)

subprocess.run(
    [OPENCLAW_BIN, "config", "set", "--batch-json", json.dumps(batch_payload)],
    check=True,
)

subprocess.run(
    [OPENCLAW_BIN, "config", "validate"],
    check=True,
)

print(json.dumps({
    "ok": True,
    "region": region.get("region"),
    "primary_model": primary_model,
    "models": models,
    "model_map": model_map
}, indent=2))
