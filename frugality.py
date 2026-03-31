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

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROVIDER_PREFIXES = {
    "nvidia": "nvidia_nim",
    "openrouter": "open_router",
    "groq": "groq",
    "cerebras": "cerebras",
    "sambanova": "sambanova",
    "mistral": "mistral",
    "fireworks": "fireworks",
    "together": "together",
    "deepinfra": "deepinfra",
    "huggingface": "huggingface",
    "perplexity": "perplexity",
    "google": "google",
    "zai": "zai",
    "hyperbolic": "hyperbolic",
    "siliconflow": "siliconflow",
    "scaleway": "scaleway",
    "qwen": "qwen",
    "iflow": "iflow",
}

def normalize_model_id(provider, model_id):
    """Normalize model ID with provider prefix."""
    prefix = PROVIDER_PREFIXES.get(provider, provider)
    # Clean up model ID (remove :free, -instruct, etc.)
    model_id = model_id.replace(":free", "")
    model_id = model_id.replace("-instruct", "")

    # Split on / and lowercase the organization part
    parts = model_id.split("/")
    if len(parts) > 1:
        parts[0] = parts[0].lower()  # lowercase org name
        model_id = "/".join(parts)

    if not model_id.startswith(prefix + "/"):
        return f"{prefix}/{model_id}"
    return model_id

def get_model_display_name(model_id):
    """Get clean display name for model."""
    # Remove provider prefix
    for prefix in PROVIDER_PREFIXES.values():
        if model_id.startswith(prefix + "/"):
            model_id = model_id[len(prefix + "/"):]
            break

    # Clean up common naming patterns
    model_id = model_id.replace(":free", "")
    model_id = model_id.replace("-instruct", "")
    model_id = model_id.replace("-chat", "")

    # Split on / and take last part
    return model_id.split("/")[-1]

def classify_call_weight(message_count, has_tools, prompt_length):
    """Classify call weight for smart routing."""
    if message_count <= 2 and not has_tools and prompt_length < 500:
        return "lightweight"
    return "heavy"

def get_existing_keys():
    """Check which API keys are available."""
    keys = {}

    # Check free-coding-models.json
    if os.path.exists(FCM_CONFIG_PATH):
        try:
            with open(FCM_CONFIG_PATH) as f:
                fcm_data = json.load(f)
                # Check both provider names and their variations
                all_providers = set(PROVIDER_PREFIXES.keys())
                # Add common aliases
                all_providers.update(["nvidia", "openrouter", "groq", "cerebras", "mistral"])

                for provider in all_providers:
                    if provider in fcm_data:
                        keys[provider] = True
        except Exception:
            pass

    # Check existing cc-nim config
    if os.path.exists(CC_NIM_ENV_FILE):
        try:
            with open(CC_NIM_ENV_FILE) as f:
                content = f.read()
                # Look for API key patterns
                for provider in PROVIDER_PREFIXES.keys():
                    key_name = f"{provider.upper()}_API_KEY="
                    if key_name in content:
                        keys[provider] = True
        except Exception:
            pass

    return keys

def get_fcm_data():
    """Get model data from free-coding-models."""
    try:
        logger.debug("Running free-coding-models discovery")

        # Use node for reliable JSON parsing
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

            # Clean up model data
            for model in data:
                # Ensure provider exists
                if "provider" not in model:
                    model["provider"] = "unknown"

                # Normalize tier
                tier = model.get("tier", "unknown")
                if tier.startswith(("S+", "S", "A", "B", "C")):
                    model["tier"] = tier
                else:
                    model["tier"] = "unknown"

            return data

        logger.warning("No models found")
        return []

    except Exception as e:
        logger.warning("Model discovery failed: %s" % e)
        return []

def select_best_models(models, available_providers):
    """Select best models for each tier."""
    if not models:
        return {}

    # Clean up model data
    for model in models:
        # Clean model ID
        model["modelId"] = model["modelId"].replace(":free", "")
        model["modelId"] = model["modelId"].replace("-instruct", "")
        model["modelId"] = model["modelId"].lower()

    # Separate models by provider
    provider_models = {}
    for provider in available_providers:
        provider_models[provider] = [m for m in models if m.get("provider") == provider]

    # Sort models within each provider by score
    for provider, models_list in provider_models.items():
        models_list.sort(key=lambda m: (
            -float(m.get("sweScore", "0").rstrip("%").replace(".", "")),
            -len(m.get("context", "0")),
        ))

    # Select best models overall
    selected = {}

    # Find best overall models
    all_sorted = sorted(models, key=lambda m: (
        -float(m.get("sweScore", "0").rstrip("%").replace(".", "")),
        -len(m.get("context", "0")),
    ))

    # Tier-based selection
    s_plus_models = [m for m in all_sorted if m.get("tier") == "S+"]
    s_models = [m for m in all_sorted if m.get("tier") == "S"]
    a_models = [m for m in all_sorted if m.get("tier") in ["A", "A+", "A-"]]
    b_models = [m for m in all_sorted if m.get("tier") in ["B", "B+", "B-"]]

    # Model assignments
    if s_plus_models:
        selected["MODEL_OPUS"] = s_plus_models[0]  # Complex tasks
    elif s_models:
        selected["MODEL_OPUS"] = s_models[0]

    if s_models:
        selected["MODEL_SONNET"] = s_models[0]  # Core coding
    elif s_plus_models:
        selected["MODEL_SONNET"] = s_plus_models[0]

    if a_models:
        selected["MODEL_HAIKU"] = a_models[0]  # Lightweight
    elif s_models:
        selected["MODEL_HAIKU"] = s_models[0]

    # Fallback
    if selected:
        selected["MODEL"] = list(selected.values())[0]

    return selected

def write_env_file(selected_models, available_providers):
    """Write cc-nim config."""
    lines = []

    # Add API key placeholders for available providers
    for provider in available_providers:
        prefix = PROVIDER_PREFIXES[provider]
        key_name = f"{prefix.upper()}_API_KEY"
        lines.append(f'{key_name}="sk-or-..."')

    lines.append("")  # Empty line

    # Add model assignments
    for slot, model in selected_models.items():
        model_id = normalize_model_id(model["provider"], model["modelId"])
        lines.append(f'{slot}="{model_id}"')

    # Add thinking mode detection
    thinking_enabled = False
    for slot, model in selected_models.items():
        model_id = model["modelId"].lower()
        if any(keyword in model_id for keyword in ["kimi", "nemotron", "deepseek-r1", "qwq", "reasoning"]):
            thinking_enabled = True
            break

    lines.append("")
    lines.append(f'NIM_ENABLE_THINKING={"true" if thinking_enabled else "false"}')

    # Write atomically
    atomic_write(CC_NIM_ENV_FILE, "\n".join(lines))

def atomic_write(path, content):
    """Write content atomically with backup."""
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    # Backup existing file
    if os.path.exists(path):
        backup_path = path + ".backup"
        with open(path, "r") as src, open(backup_path, "w") as dst:
            dst.write(src.read())

        # Read existing content
        with open(path, "r") as f:
            existing = f.read()

        # Find start and end of frugality-managed section
        start_marker = "# Managed by Frugality\n"
        end_marker = "# End of Frugality config\n"

        # Prepare new content
        new_content = existing
        if start_marker in existing:
            start_idx = existing.find(start_marker)
            end_idx = existing.find(end_marker, start_idx)
            if end_idx != -1:
                new_content = existing[:start_idx] + start_marker + content + end_marker + "\n"

        # Write if changed
        if new_content != existing:
            temp_path = path + ".tmp"
            with open(temp_path, "w") as f:
                f.write(new_content)
            os.replace(temp_path, path)
    else:
        # New file
        temp_path = path + ".tmp"
        with open(temp_path, "w") as f:
            f.write("# Managed by Frugality\n")
            f.write(content)
            f.write("# End of Frugality config\n")
        os.replace(temp_path, path)

    logger.info("Wrote config to %s" % path)

def print_summary(selected_models, available_providers):
    """Print beautiful summary."""
    print("\n🚀 Frugality - Model Routing")
    print("=" * 50)

    # Print active providers
    if available_providers:
        print("✅ Providers available: %s" % ", ".join(available_providers))
    else:
        print("❌ No providers configured")

    # Print model assignments
    for slot in ["MODEL_OPUS", "MODEL_SONNET", "MODEL_HAIKU", "MODEL"]:
        if slot in selected_models:
            model = selected_models[slot]
            model_id = normalize_model_id(model["provider"], model["modelId"])
            display_name = get_model_display_name(model_id)

            # Get tier
            tier = model.get("tier", "unknown")
            tier_emoji = {"S+": "⭐", "S": "🌟", "A": "💪", "B": "🔧", "C": "🔰"}.get(tier, "❓")

            # Get thinking status
            thinking = ""
            model_lower = model["modelId"].lower()
            if any(keyword in model_lower for keyword in ["kimi", "nemotron", "deepseek-r1", "qwq"]):
                thinking = " 🧠"

            print(f"{slot:<12} → {display_name:<25} {tier_emoji} {thinking}")

    print("=" * 50)
    print("💡 Tip: Run 'claude-frugal' to start coding with free models!")

def main():
    parser = argparse.ArgumentParser(description="Frugality - Free model routing")
    parser.add_argument("--refresh", action="store_true", help="Force fresh model discovery")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--check-keys", action="store_true", help="Check API keys only")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Special handling for check-keys
    if args.check_keys:
        available_providers = get_existing_keys()
        if available_providers:
            print("✅ Found API keys for: %s" % ", ".join(available_providers.keys()))
        else:
            print("❌ No API keys found")
            print("💡 Run: free-coding-models (interactive setup)")
        return

    logger.info("Discovering free models...")

    # Get available providers
    available_providers = get_existing_keys()
    logger.debug("Available providers: %s" % list(available_providers.keys()))

    # Get model data
    models = get_fcm_data()
    if not models:
        print("❌ No models found. Check your API keys and network.")
        print("💡 Tip: Run 'free-coding-models' to configure providers")
        sys.exit(1)

    # Select best models
    selected = select_best_models(models, available_providers)

    if not selected:
        print("❌ No suitable models found.")
        print("💡 Tip: Check your API keys or try --refresh")
        sys.exit(1)

    # Write config
    write_env_file(selected, available_providers)

    # Print summary
    print_summary(selected, available_providers)

    logger.info("✅ Configuration complete")

if __name__ == "__main__":
    main()