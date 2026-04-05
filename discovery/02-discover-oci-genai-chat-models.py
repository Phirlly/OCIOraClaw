#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path
from urllib import request, error

CANDIDATES_PATH = Path(
    sys.argv[1] if len(sys.argv) > 1 else "/opt/openclaw/discovery/01-oci-genai-chat-candidates.json"
)
OUTPUT_PATH = Path(
    sys.argv[2] if len(sys.argv) > 2 else "/opt/openclaw/runtime/03-oci-genai-chat-models.json"
)
API_KEY = os.environ.get("OCI_GENAI_API_KEY")

if not API_KEY:
    print("ERROR: OCI_GENAI_API_KEY is not set", file=sys.stderr)
    sys.exit(1)

with CANDIDATES_PATH.open("r", encoding="utf-8") as f:
    candidates = json.load(f)

base_template = candidates["apiKeyOpenAICompatible"]["baseUrlTemplate"]
supported_regions = candidates["apiKeyOpenAICompatible"]["supportedRegions"]
chat_candidates = candidates.get("chatCandidates", {})


def post_json(url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with request.urlopen(req, timeout=45) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body
    except Exception as e:
        return None, str(e)


def classify(status, body):
    body_lower = (body or "").lower()

    if status == 200:
        return "usable"
    if status == 401:
        return "auth_failed"
    if status == 403:
        return "forbidden"
    if status == 404 and "entity with key" in body_lower and "not found" in body_lower:
        return "invalid_model_id"
    if status == 400 and "multi agent requests are not allowed on chat completions" in body_lower:
        return "responses_only"
    if status == 429:
        return "rate_limited"
    if status == 400:
        return "bad_request"
    if status is None:
        return "transport_error"
    return "other"


output = {
    "schemaVersion": 1,
    "purpose": "usable-chat-models",
    "generatedFrom": str(CANDIDATES_PATH.name),
    "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "regions": [],
    "diagnostics": {
        "apiKeyPresent": bool(API_KEY),
        "regionChecks": {}
    }
}

for region in supported_regions:
    models = chat_candidates.get(region, [])
    if not models:
        output["diagnostics"]["regionChecks"][region] = {
            "probeModel": None,
            "probeStatus": None,
            "probeClassification": "no_candidates",
            "probeBodySnippet": "",
            "usableModels": [],
            "invalidModelIds": [],
            "responsesOnlyModels": []
        }
        continue

    base_url = base_template.replace("{region}", region)
    chat_url = f"{base_url}/chat/completions"

    probe_model = models[0]
    probe_payload = {
        "model": probe_model,
        "messages": [
            {
                "role": "user",
                "content": "Reply with exactly the word OK"
            }
        ],
        "max_tokens": 8,
        "temperature": 0
    }

    status, body = post_json(chat_url, probe_payload)
    classification = classify(status, body)

    usable_models = []
    excluded_invalid = []
    excluded_responses_only = []

    if classification in {"usable", "invalid_model_id", "responses_only", "bad_request", "rate_limited"}:
        for model in models:
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Reply with exactly the word OK"
                    }
                ],
                "max_tokens": 8,
                "temperature": 0
            }

            model_status, model_body = post_json(chat_url, payload)
            model_classification = classify(model_status, model_body)

            if model_classification == "usable":
                usable_models.append(model)
            elif model_classification == "invalid_model_id":
                excluded_invalid.append(model)
            elif model_classification == "responses_only":
                excluded_responses_only.append(model)

            time.sleep(0.5)

    output["diagnostics"]["regionChecks"][region] = {
        "probeModel": probe_model,
        "probeStatus": status,
        "probeClassification": classification,
        "probeBodySnippet": (body or "")[:500],
        "usableModels": usable_models,
        "invalidModelIds": excluded_invalid,
        "responsesOnlyModels": excluded_responses_only
    }

    if usable_models:
        output["regions"].append(
            {
                "region": region,
                "baseUrl": base_url,
                "chatCompletions": {
                    "models": usable_models
                },
                "excluded": {
                    "responsesOnlyModels": excluded_responses_only,
                    "invalidModelIds": excluded_invalid
                }
            }
        )

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
    f.write("\n")

print(json.dumps(output, indent=2))

# Exit non-zero if discovery produced no usable regions and we saw real failures.
region_checks = output["diagnostics"]["regionChecks"]
classifications = [
    details.get("probeClassification")
    for details in region_checks.values()
]

retryable_failure_seen = any(
    c in {"transport_error", "auth_failed", "forbidden", "other"}
    for c in classifications
)

if not output["regions"] and retryable_failure_seen:
    sys.exit(2)
