#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
from pathlib import Path

HOME = str(Path.home())
FCM_CONFIG_PATH = os.path.join(HOME, ".free-coding-models.json")
CCR_CONFIG_PATH = os.path.join(HOME, ".claude-code-router", "config.json")

PROVIDER_BASE_URLS = {
    "nvidia": "https://integrate.api.nvidia.com/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "cerebras": "https://api.cerebras.ai/v1/chat/completions",
    "sambanova": "https://api.sambanova.ai/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "huggingface": "https://router.huggingface.co/v1/chat/completions",
    "deepinfra": "https://api.deepinfra.com/v1/openai/chat/completions",
    "fireworks": "https://api.fireworks.ai/inference/v1/chat/completions",
    "mistral": "https://api.mistral.ai/v1/chat/completions",
    "cohere": "https://api.cohere.ai/v1/chat/completions",
    "ai21": "https://api.ai21.com/v1/chat/completions",
    "together": "https://api.together.ai/v1/chat/completions",
    "cloudflare": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions",
    "perplexity": "https://api.perplexity.ai/chat/completions",
    "google": "https://generativelanguage.googleapis.com/v1beta/models/",
    "ollama": "http://localhost:11434/v1/chat/completions",
}


def atomic_write_json(path, data):
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name)

    fd, temp_path = tempfile.mkstemp(dir=dir_name, text=True)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(temp_path, path)


def get_fcm_credentials():
    if not os.path.exists(FCM_CONFIG_PATH):
        return {}
    try:
        with open(FCM_CONFIG_PATH, "r") as f:
            return json.load(f)
    except:
        return {}


def get_fcm_data():
    try:
        result = subprocess.run(
            [
                "node",
                "-e",
                """
const { execSync } = require('child_process');
const output = execSync('free-coding-models --json --hide-unconfigured', {encoding: 'utf8', timeout: 30000});
const startIdx = output.indexOf('[');
if (startIdx === -1) { console.log('[]'); process.exit(0); }
const jsonStr = output.slice(startIdx);
const data = JSON.parse(jsonStr);
console.log(JSON.stringify(data));
""",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.stdout:
            return json.loads(result.stdout.strip())
        return []
    except Exception as e:
        print(f"Error getting fcm data: {e}")
        return []


def get_api_key(credentials, provider):
    if not credentials:
        return ""
    api_keys = credentials.get("apiKeys", {})
    key = api_keys.get(provider, "")
    if key:
        return key

    for p in [provider, provider.upper(), provider.lower()]:
        if p in api_keys:
            return api_keys[p]

    providers_config = credentials.get("providers", {})
    if provider in providers_config:
        return providers_config[provider].get("apiKey", "")

    return ""


def map_tiers(models):
    routes = {"default": None, "background": None, "think": None, "longContext": None}

    for m in models:
        model_id = m.get("modelId", "")
        tier = m.get("tier", "C")

        if not routes["think"] and (
            "r1" in model_id.lower()
            or "v3" in model_id.lower()
            or "reasoning" in model_id.lower()
            or "think" in model_id.lower()
        ):
            routes["think"] = m

        context = m.get("context", "0")
        ctx_val = int(
            context.replace("k", "000").replace("M", "000000").replace("1M", "1000000")
            or "0"
        )
        if not routes["longContext"] and ctx_val >= 32000:
            routes["longContext"] = m

        if not routes["default"] and tier in ["S+", "S"]:
            routes["default"] = m

        if not routes["background"] and tier in ["A+", "A"]:
            routes["background"] = m

    for role in routes:
        if not routes[role] and routes["default"]:
            routes[role] = routes["default"]

    return routes


def build_provider_config(models, credentials):
    providers_map = {}

    for m in models:
        provider_key = m.get("provider", "")
        if not provider_key:
            continue

        if provider_key not in providers_map:
            base_url = PROVIDER_BASE_URLS.get(
                provider_key, "https://api.openai.com/v1/chat/completions"
            )
            api_key = get_api_key(credentials, provider_key)

            providers_map[provider_key] = {
                "name": provider_key,
                "api_base_url": base_url,
                "api_key": api_key,
                "models": [],
            }

        model_id = m.get("modelId", "")
        if model_id:
            providers_map[provider_key]["models"].append(model_id)

    return list(providers_map.values())


def update_ccr_config():
    print("--- Frugality: Configuring Claude Code Router ---")

    credentials = get_fcm_credentials()
    models = get_fcm_data()

    if not models:
        print("No models found. Check your Internet/API keys.")
        return False

    print(f"✓ Discovered {len(models)} models")

    selected = map_tiers(models)

    if not selected["default"]:
        print("Error: No suitable models found")
        return False

    providers = build_provider_config(models, credentials)

    router_config = {}
    for role, model_data in selected.items():
        if model_data:
            model_id = model_data["modelId"]
            provider = model_data.get("provider", "")
            if provider:
                router_config[role] = f"{provider},{model_id.split('/')[-1]}"
            else:
                router_config[role] = model_id.split("/")[-1]

    ccr_config = {"Providers": providers, "Router": router_config}

    atomic_write_json(CCR_CONFIG_PATH, ccr_config)
    print(f"✓ Updated CCR config at {CCR_CONFIG_PATH}")
    return True


if __name__ == "__main__":
    success = update_ccr_config()
    if success:
        print("--- Configuration Complete ---")
