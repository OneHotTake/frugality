#!/usr/bin/env python3
import argparse
import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

HOME = str(Path.home())
FCM_CONFIG_PATH = os.path.join(HOME, ".free-coding-models.json")
CCR_CONFIG_PATH = os.path.join(HOME, ".claude-code-router", "config.json")
CACHE_DIR = os.path.join(HOME, ".frugality", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "last-known-good.json")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

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


def setup_logging(verbose, quiet):
    if verbose:
        logger.setLevel(logging.DEBUG)
    elif quiet:
        logger.setLevel(logging.WARNING)


def backup_file(path):
    if not os.path.exists(path):
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.backup_{timestamp}"
    import shutil

    shutil.copy2(path, backup_path)
    logger.info(f"Backed up existing config to {backup_path}")


def atomic_write_json(path, data):
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name)

    backup_file(path)

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
    except Exception:
        return {}


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
        cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01T00:00:00"))
        cache_age = datetime.now() - cached_at
        if cache_age < timedelta(hours=24):
            logger.info(f"Using cached config from {cached_at.isoformat()}")
            return data.get("models", [])
        else:
            logger.warning("Cache is stale (>24 hours)")
            return None
    except Exception:
        return None


def save_cache(models):
    os.makedirs(CACHE_DIR, exist_ok=True)
    data = {"cached_at": datetime.now().isoformat(), "models": models}
    try:
        atomic_write_json(CACHE_FILE, data)
        logger.debug(f"Saved {len(models)} models to cache")
    except Exception as e:
        logger.warning(f"Failed to save cache: {e}")


def get_fcm_data():
    try:
        logger.debug("Running free-coding-models discovery")
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
        if result.returncode != 0:
            logger.debug(f"FCM stderr: {result.stderr}")
            raise Exception(f"FCM exited with code {result.returncode}")

        if not result.stdout:
            raise Exception("FCM returned empty output")

        data = json.loads(result.stdout.strip())
        logger.debug(f"FCM returned {len(data)} models")

        if not isinstance(data, list) or len(data) == 0:
            raise Exception("FCM output is not a non-empty JSON array")

        first = data[0]
        if "modelId" not in first or "tier" not in first:
            missing = []
            if "modelId" not in first:
                missing.append("modelId")
            if "tier" not in first:
                missing.append("tier")
            logger.warning(
                f"FCM output schema has changed — missing fields: {missing}. Update frugality.py tier mapping to match new schema."
            )
            raise Exception("FCM output missing required fields")

        save_cache(data)
        return data

    except json.JSONDecodeError as e:
        logger.debug(f"JSON decode error: {e}")
        raise Exception(f"Invalid JSON from FCM: {e}")
    except Exception as e:
        logger.debug(f"FCM error: {e}")
        raise e


def get_fcm_data_with_cache():
    try:
        return get_fcm_data()
    except Exception as e:
        logger.warning(f"FCM discovery failed: {e}. Attempting cache fallback.")
        cached = load_cache()
        if cached:
            logger.info(f"Using cached config from cache file")
            return cached
        else:
            logger.error("No valid cache available. Please check:")
            logger.error("  - Internet connection")
            logger.error("  - API keys configured in ~/.free-coding-models.json")
            logger.error("  - Run 'free-coding-models --json' manually to test")
            return None


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


def print_selection_summary(selected):
    logger.info("Frugality model selection:")
    for role in ["default", "background", "think", "longContext"]:
        model_data = selected.get(role)
        if model_data:
            model_id = model_data.get("modelId", "unknown")
            tier = model_data.get("tier", "unknown")
            uptime = model_data.get("uptime", "unknown")
            logger.info(f"  {role:12} → {model_id} ({tier}-tier, {uptime}% uptime)")
        else:
            logger.info(f"  {role:12} → (none selected)")


def update_ccr_config():
    logger.info("Configuring Claude Code Router")

    credentials = get_fcm_credentials()
    models = get_fcm_data_with_cache()

    if not models:
        return False

    logger.info(f"Discovered {len(models)} models")

    selected = map_tiers(models)

    if not selected["default"]:
        logger.error("No suitable models found")
        return False

    print_selection_summary(selected)

    providers = build_provider_config(models, credentials)

    router_config = {}
    for role, model_data in selected.items():
        if model_data:
            model_id = model_data["modelId"]
            provider = model_data.get("provider", "")
            if provider:
                router_config[role] = f"{provider},{model_id}"
            else:
                router_config[role] = model_id

    ccr_config = {"Providers": providers, "Router": router_config}

    try:
        atomic_write_json(CCR_CONFIG_PATH, ccr_config)
        logger.info(f"Updated CCR config at {CCR_CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Failed to write config: {e}")
        return False

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Frugality - Cost-optimized AI model routing"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug output"
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Only show errors")
    args = parser.parse_args()

    setup_logging(args.verbose, args.quiet)

    success = update_ccr_config()
    if success:
        logger.info("Configuration complete")
        exit(0)
    else:
        exit(1)
