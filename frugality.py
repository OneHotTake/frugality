#!/usr/bin/env python3
import argparse
import json
import logging
import os
import random
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

HOME = str(Path.home())
FCM_CONFIG_PATH = os.path.join(HOME, ".free-coding-models.json")
CC_NIM_ENV_DIR = os.path.join(HOME, ".config", "free-claude-code")
CC_NIM_ENV_FILE = os.path.join(CC_NIM_ENV_DIR, ".env")

CERT_SCHEMA_VERSION = 1
PROBE_VERSION = 1
PROBE_TIMEOUT = 15
PROBE_WORKERS = 2
PROBE_MAX_RETRIES = 2
PROBE_RETRY_DELAY = 2.0

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _nim_prefix(model_id):
    """Add nvidia_nim/ prefix to model ID."""
    if model_id.startswith("nvidia_nim/"):
        return model_id
    return f"nvidia_nim/{model_id}"


def _openrouter_prefix(model_id):
    """Add open_router/ prefix to model ID."""
    if model_id.startswith("open_router/"):
        return model_id
    return f"open_router/{model_id}"


def _needs_thinking(model_id):
    """Check if model needs NIM thinking mode enabled."""
    thinking_keywords = ["kimi", "nemotron", "deepseek-r1", "qwq"]
    return any(keyword in model_id.lower() for keyword in thinking_keywords)


def _normalize_provider(provider):
    """Normalize provider name to lowercase."""
    return provider.strip().lower()


def _registry_key(provider, model_id):
    """Generate registry key for model."""
    return f"{_normalize_provider(provider)},{model_id}"


def atomic_write(path, content):
    """Write content to path atomically."""
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    temp_path = path + ".tmp"
    with open(temp_path, "w") as f:
        f.write(content)

    # Preserve existing user settings by merging if file exists
    if os.path.exists(path):
        with open(path, "r") as existing:
            existing_content = existing.read()

        # Extract only frugality-managed lines
        lines = content.splitlines()
        frugality_lines = []
        for line in lines:
            if line.startswith(("NVIDIA_NIM_API_KEY", "OPENROUTER_API_KEY", "MODEL_OPUS",
                              "MODEL_SONNET", "MODEL_HAIKU", "MODEL", "NIM_ENABLE_THINKING")):
                frugality_lines.append(line)

        # Write merged content
        with open(path, "w") as f:
            f.write(existing_content)
            if existing_content and not existing_content.endswith("\n"):
                f.write("\n")
            f.write("\n")
            f.write("# Managed by Frugality\n")
            f.write("# Last updated: " + datetime.now().isoformat() + "\n")
            for line in frugality_lines:
                f.write(line + "\n")
    else:
        os.rename(temp_path, path)


def get_fcm_data():
    """Get model data from free-coding-models."""
    try:
        logger.debug("Running free-coding-models discovery")

        # Use a more reliable method to get JSON data
        import subprocess
        try:
            # Use node to parse the JSON properly
            result = subprocess.run(
                """
node -e "
const { execSync } = require('child_process');
try {
  const output = execSync('free-coding-models --json --hide-unconfigured 2>/dev/null', {encoding: 'utf8'});
  const startIdx = output.indexOf('[');
  if (startIdx === -1) {
    console.log('[]');
    process.exit(0);
  }
  const jsonStr = output.slice(startIdx);
  const data = JSON.parse(jsonStr);
  console.log(JSON.stringify(data));
} catch (e) {
  console.log('[]');
}
"
""",
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.stdout:
                data = json.loads(result.stdout.strip())
                logger.debug("FCM returned %d models" % len(data))
                return data
        except Exception:
            pass

        # Final fallback: return empty list
        logger.warning("Could not get FCM data, using empty list")
        return []

    except Exception as e:
        logger.warning("Model discovery failed: %s" % e)
        return None
        logger.debug("FCM returned %d models" % len(data))

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
                "FCM output schema has changed -- missing fields: %s. Update frugality.py tier mapping to match new schema."
                % missing
            )
            raise Exception("FCM output missing required fields")

        return data
    except Exception as e:
        logger.warning("Model discovery failed: %s" % e)
        return None


def get_existing_keys():
    """Check which API keys already exist."""
    keys = {}

    # Check free-coding-models.json
    if os.path.exists(FCM_CONFIG_PATH):
        try:
            with open(FCM_CONFIG_PATH) as f:
                fcm_data = json.load(f)
                for provider in ["nvidia", "openrouter"]:
                    if provider in fcm_data:
                        keys[provider] = True
        except Exception:
            pass

    # Check existing cc-nim config
    if os.path.exists(CC_NIM_ENV_FILE):
        try:
            with open(CC_NIM_ENV_FILE) as f:
                content = f.read()
                if "NVIDIA_NIM_API_KEY=" in content:
                    keys["nvidia"] = True
                if "OPENROUTER_API_KEY=" in content:
                    keys["openrouter"] = True
        except Exception:
            pass

    return keys


def _map_to_slots(models, preferred_provider=None):
    """Map models to cc-nim slots based on tier and provider."""
    slots = {}

    # Sort models by tier and provider preference
    sorted_models = sorted(models, key=lambda m: (
        -int(m.get("sweScore", "0").rstrip("%").replace(".", "")),
        1 if preferred_provider and m.get("provider") == preferred_provider else 0,
        -len(m.get("context", "0"))
    ))

    # Assign best model to each slot
    s_plus_s_models = [m for m in sorted_models if m.get("tier") in ["S+", "S"]]

    if s_plus_s_models:
        # Best for OPUS (complex tasks)
        slots["MODEL_OPUS"] = s_plus_s_models[0]["modelId"]

        # Best for SONNET (core coding)
        if len(s_plus_s_models) > 1:
            slots["MODEL_SONNET"] = s_plus_s_models[1]["modelId"]
        else:
            slots["MODEL_SONNET"] = s_plus_s_models[0]["modelId"]

        # Best for HAIKU (lightweight)
        a_models = [m for m in sorted_models if m.get("tier") in ["A", "A+", "A-"]]
        if a_models:
            slots["MODEL_HAIKU"] = a_models[0]["modelId"]
        else:
            slots["MODEL_HAIKU"] = s_plus_s_models[0]["modelId"]

        # Fallback MODEL
        slots["MODEL"] = s_plus_s_models[0]["modelId"]

    return slots


def write_env_file(selected, provider_keys):
    """Write cc-nim config to ~/.config/free-claude-code/.env."""
    lines = []

    # Determine provider prefixes
    nim_available = provider_keys.get("nvidia", False)
    openrouter_available = provider_keys.get("openrouter", False)

    # Build model assignments with provider prefixes
    if nim_available:
        lines.append('NVIDIA_NIM_API_KEY="nvapi-..."')
        lines.append("")
    if openrouter_available:
        lines.append('OPENROUTER_API_KEY="sk-or-..."')
        lines.append("")

    # Model assignments
    for slot, model_id in selected.items():
        prefix = ""
        if nim_available and "nvidia" in model_id:
            prefix = _nim_prefix(model_id)
        elif openrouter_available and "openrouter" in model_id:
            prefix = _openrouter_prefix(model_id)
        else:
            # Default to NIM prefix
            prefix = _nim_prefix(model_id)

        lines.append(f'{slot}="{prefix}"')

    # Determine if thinking mode should be enabled
    thinking_enabled = False
    if "MODEL_SONNET" in selected:
        sonnet_model = selected["MODEL_SONNET"]
        if any(keyword in sonnet_model.lower() for keyword in ["kimi", "nemotron", "deepseek-r1", "qwq"]):
            thinking_enabled = True

    lines.append("")
    lines.append(f'NIM_ENABLE_THINKING={"true" if thinking_enabled else "false"}')

    # Write atomically
    content = "\n".join(lines)
    atomic_write(CC_NIM_ENV_FILE, content)
    logger.info("Wrote cc-nim config to %s" % CC_NIM_ENV_FILE)


def print_summary(selected, provider_keys):
    """Print summary of model selections."""
    print("\nfrugal-claude: model routing summary:")
    print("=" * 50)

    nim_available = provider_keys.get("nvidia", False)
    openrouter_available = provider_keys.get("openrouter", False)

    for slot in ["MODEL_OPUS", "MODEL_SONNET", "MODEL_HAIKU", "MODEL"]:
        if slot in selected:
            model_id = selected[slot]
            provider = "unknown"

            if nim_available and "nvidia" in model_id:
                provider = "NVIDIA NIM"
            elif openrouter_available and "openrouter" in model_id:
                provider = "OpenRouter"
            else:
                provider = "NVIDIA NIM"

            # Get tier from model ID mapping
            tier = "unknown"
            if "S+" in model_id or "S" in model_id:
                tier = "S+/S"
            elif "A" in model_id or "A+" in model_id:
                tier = "A"

            print(f"{slot:<12} → {model_id:<35} ({provider}, {tier})")

    print("=" * 50)
    print("Providers available: %s" % (
        ", ".join(k for k, v in provider_keys.items() if v)
    ))


def main():
    parser = argparse.ArgumentParser(description="Frugality - Free model routing for cc-nim")
    parser.add_argument("--refresh", action="store_true", help="Force fresh model discovery")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    logger.info("frugal-claude: discovering models for cc-nim...")

    # Get existing keys
    provider_keys = get_existing_keys()
    logger.debug("Available providers: %s" % list(provider_keys.keys()))

    # Get model data
    models = get_fcm_data()
    if not models:
        logger.error("Model discovery failed")
        print("frugal-claude: error - no models discovered. Check your API keys and network.")
        sys.exit(1)

    # Map models to slots
    preferred_provider = "nvidia" if provider_keys.get("nvidia") else None
    selected = _map_to_slots(models, preferred_provider)

    if not selected:
        logger.error("No suitable models found")
        print("frugal-claude: error - no models selected. Try --refresh to discover more.")
        sys.exit(1)

    # Write config
    write_env_file(selected, provider_keys)

    # Print summary
    print_summary(selected, provider_keys)

    logger.info("Configuration complete")


if __name__ == "__main__":
    main()

# Inline tests
assert _nim_prefix("moonshotai/kimi-k2.5") == "nvidia_nim/moonshotai/kimi-k2.5"
assert _openrouter_prefix("deepseek/deepseek-r1-0528:free") == "open_router/deepseek/deepseek-r1-0528:free"

assert _needs_thinking("nvidia_nim/moonshotai/kimi-k2.5") == True
assert _needs_thinking("nvidia_nim/stepfun-ai/step-3.5-flash") == False
assert _needs_thinking("nvidia_nim/mistralai/devstral-2-123b") == False

mock_models = [
    {"modelId": "kimi-k2.5", "tier": "S+", "provider": "nvidia", "sweScore": "71.3%"},
    {"modelId": "glm4.7", "tier": "S", "provider": "nvidia", "sweScore": "65.0%"},
    {"modelId": "step-3.5-flash", "tier": "A", "provider": "nvidia", "sweScore": "58.2%"},
]
slots = _map_to_slots(mock_models, preferred_provider="nvidia")
assert "MODEL_OPUS" in slots
assert "MODEL_HAIKU" in slots
assert slots["MODEL_HAIKU"] != slots["MODEL_OPUS"]

print("All inline tests passed.")