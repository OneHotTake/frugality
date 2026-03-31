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
import random
from datetime import datetime, timedelta
from pathlib import Path

HOME = str(Path.home())
FCM_CONFIG_PATH = os.path.join(HOME, ".free-coding-models.json")
CC_NIM_ENV_DIR = os.path.join(HOME, ".config", "free-claude-code")
CC_NIM_ENV_FILE = os.path.join(CC_NIM_ENV_DIR, ".env")
CACHE_DIR = os.path.join(HOME, ".frugality")

# Probe constants
PROBE_VERSION = 1
PROBE_PROFILE = "tool_chat"
CERT_TTL_DAYS = 7
PROBE_TIMEOUT = 15
PROBE_WORKERS = 2
PROBE_MAX_RETRIES = 2
PROBE_RETRY_DELAY = 2.0
PROBE_PROVIDER_DELAY = 0.2

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

def get_provider_display_name(model_id, provider_key=None):
    """Get simplified provider name from model_id or provider_key."""
    # If we have the provider_key, use it to map to friendly names
    if provider_key:
        # Map provider keys to friendly names based on free-coding-models metadata
        provider_map = {
            "nvidia": "NVIDIA NIM",
            "groq": "Groq",
            "cerebras": "Cerebras",
            "sambanova": "SambaNova",
            "openrouter": "OpenRouter",
            "huggingface": "Hugging Face",
            "replicate": "Replicate",
            "deepinfra": "DeepInfra",
            "fireworks": "Fireworks",
            "together": "Together",
            "hyperbolic": "Hyperbolic",
            "siliconflow": "SiliconFlow",
            "scaleway": "Scaleway",
            "google": "Google AI",
            "perplexity": "Perplexity",
            "qwen": "Qwen",
            "iflow": "iFlow",
            "opencode-zen": "OpenCode Zen",
            "mistral": "Mistral",
            "cloudflare": "Cloudflare"
        }
        if provider_key in provider_map:
            return provider_map[provider_key]

    # Extract provider prefix from model_id
    for provider, prefix in PROVIDER_PREFIXES.items():
        if model_id.startswith(prefix + "/"):
            # Map prefixes to friendly names
            prefix_map = {
                "open_router": "OpenRouter",
                "nvidia_nim": "NVIDIA NIM",
                "cerebras": "Cerebras",
                "sambanova": "SambaNova",
                "deepinfra": "DeepInfra",
                "siliconflow": "SiliconFlow",
                "scaleway": "Scaleway",
                "qwen": "Qwen",
                "iflow": "iFlow",
                "groq": "Groq",
                "mistral": "Mistral",
                "fireworks": "Fireworks",
                "together": "Together",
                "huggingface": "Hugging Face",
                "perplexity": "Perplexity",
                "google": "Google AI"
            }
            return prefix_map.get(prefix, provider.title())

    # Fallback - extract from model_id
    parts = model_id.split("/")
    if len(parts) > 1:
        name = parts[0].replace("_", "")
        # Check for common local patterns
        if name in ["ollama", "litellm"]:
            return name.title()
        # Capitalize properly
        return name.title()

    return "Unknown"

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

# ── Probe Functions for Local/Remote Model Testing ───────────────

# Tool definition for probing
ECHO_TOOL = {
    "type": "function",
    "function": {
        "name": "echo_number",
        "description": "Echo the input number",
        "parameters": {"type": "object", "properties": {"value": {"type": "number"}}, "required": ["value"]},
    },
}

PROVIDER_BASE_URLS = {
    "nvidia": "https://integrate.api.nvidia.com/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "cerebras": "https://api.cerebras.ai/v1/chat/completions",
    "sambanova": "https://api.sambanova.ai/v1/chat/completions",
    "mistral": "https://api.mistral.ai/v1/chat/completions",
    "fireworks": "https://api.fireworks.ai/inference/v1/chat/completions",
    "together": "https://api.together.xyz/v1/chat/completions",
    "deepinfra": "https://api.deepinfra.com/v1/openai/chat/completions",
    "huggingface": "https://api-inference.huggingface.co/models",
    "perplexity": "https://api.perplexity.ai/chat/completions",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
}

def normalize_provider(provider):
    """Normalize provider name."""
    return provider.lower().strip()

def get_api_key(credentials, provider):
    """Get API key for provider."""
    provider = normalize_provider(provider)
    return credentials.get("apiKeys", {}).get(provider)

def registry_key(provider, model_id):
    """Generate registry key."""
    return f"{normalize_provider(provider)},{model_id}"

def is_cert_stale(entry):
    """Check if certification is stale."""
    if "last_verified_at" not in entry:
        return True

    last_verified = datetime.fromisoformat(entry["last_verified_at"])
    age = datetime.now() - last_verified
    return age.days > CERT_TTL_DAYS

def _make_chat_request(url: str, api_key: str, payload: dict) -> dict:
    """Make HTTP request to model API."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Frugality/1.0",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=PROBE_TIMEOUT) as response:
        return json.loads(response.read().decode())

def _make_chat_request_with_retry(url: str, api_key: str, payload: dict) -> dict:
    """Retry on transient 429/5xx errors with exponential backoff and jitter."""
    last_exc = None
    for attempt in range(PROBE_MAX_RETRIES + 1):
        try:
            return _make_chat_request(url, api_key, payload)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < PROBE_MAX_RETRIES:
                # Exponential backoff: 2s, 4s, 8s + random jitter 0-0.5s
                base_delay = PROBE_RETRY_DELAY * (2 ** attempt)
                jitter = random.uniform(0, 0.5)
                delay = base_delay + jitter
                if e.code == 429:
                    delay *= 2  # Extra delay for rate limits
                logger.debug(f"Retry attempt {attempt + 1} after {delay:.2f}s (error {e.code})")
                time.sleep(delay)
                last_exc = e
                continue
            raise
    raise last_exc

def probe_model(provider: str, model_id: str, credentials: dict) -> dict:
    """
    Certification probe for profile 'tool_chat'.
    Step 1+2: Send tool-call request → verify echo_number(value=7) emitted
    Step 3:   Send tool result → verify final text answer contains "49"
    Returns a registry entry dict (no tier/context metadata — caller adds those).
    """
    url = PROVIDER_BASE_URLS.get(
        normalize_provider(provider), "https://api.openai.com/v1/chat/completions"
    )
    api_key = get_api_key(credentials, provider)

    base_entry = {
        "status": "failed",
        "probe_version": PROBE_VERSION,
        "probe_profile": PROBE_PROFILE,
        "provider": normalize_provider(provider),
        "model_id": normalize_model_id(provider, model_id),
        "capabilities": {
            "tool_calling": False,
            "tool_roundtrip": False,
            "valid_json_args": False,
        },
        "failure_reason": None,
        "last_verified_at": datetime.now().isoformat(),
    }

    # Skip if no credentials
    if not api_key:
        return {**base_entry, "status": "skipped", "failure_reason": "no_credentials"}

    # Step 1+2: Tool call emission
    try:
        resp = _make_chat_request_with_retry(
            url,
            api_key,
            {
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": "Call echo_number with value 7. Do not answer directly.",
                    }
                ],
                "tools": [ECHO_TOOL],
                "tool_choice": "required",
            },
        )
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return {
                **base_entry,
                "status": "skipped",
                "failure_reason": f"auth_error:{e.code}",
            }
        return {**base_entry, "failure_reason": f"http_error:{e.code}"}
    except urllib.error.URLError as e:
        return {**base_entry, "status": "skipped", "failure_reason": f"connectivity:{e.reason}"}
    except Exception as e:
        return {**base_entry, "failure_reason": f"request_error:{e}"}

    try:
        choice = resp["choices"][0]["message"]
        tool_calls = choice.get("tool_calls") or []
        if not tool_calls:
            return {**base_entry, "failure_reason": "no_tool_call"}
        tc = tool_calls[0]
        if tc["function"]["name"] != "echo_number":
            return {
                **base_entry,
                "failure_reason": f"wrong_tool_name:{tc['function']['name']}",
            }
        args = json.loads(tc["function"]["arguments"])
        if args.get("value") != 7:
            return {**base_entry, "failure_reason": f"bad_args:value={args.get('value')}"}
    except Exception as e:
        return {**base_entry, "failure_reason": f"parse_error:{e}"}

    base_entry["capabilities"]["tool_calling"] = True
    base_entry["capabilities"]["valid_json_args"] = True

    # Step 3: Tool roundtrip
    tool_call_id = tool_calls[0].get("id", "call_test_1")
    try:
        resp2 = _make_chat_request_with_retry(
            url,
            api_key,
            {
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": "Call echo_number with value 7. Do not answer directly.",
                    },
                    {"role": "assistant", "tool_calls": [tool_calls[0]]},
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps({"ok": True, "value": 49}),
                    },
                ],
            },
        )
        final = resp2["choices"][0]["message"]
        if final.get("tool_calls"):
            return {**base_entry, "failure_reason": "tool_loop"}
        content = final.get("content") or ""
        if not content:
            return {**base_entry, "failure_reason": "empty_final_response"}
        # Verify model actually consumed the tool result (must reference "49")
        if "49" not in content:
            return {**base_entry, "failure_reason": "roundtrip_result_ignored"}
    except Exception as e:
        return {**base_entry, "failure_reason": f"roundtrip_error:{e}"}

    base_entry["capabilities"]["tool_roundtrip"] = True
    return {**base_entry, "status": "certified"}

def run_probes(candidates: list, registry: dict, credentials: dict) -> dict:
    """
    Determine which candidates need probing, run with provider-aware concurrency,
    merge results into registry. Returns updated registry.

    Provider-aware concurrency:
    - Groups candidates by provider
    - Processes each provider's models sequentially (max 1 concurrent request per provider)
    - Adds PROBE_PROVIDER_DELAY between requests to same provider
    - Uses PROBE_WORKERS to parallelize across different providers
    - This prevents hammering the same provider with parallel requests
    """
    to_probe = []
    for m in candidates:
        provider = normalize_provider(m.get("provider", ""))
        model_id = normalize_model_id(m.get("provider", ""), m.get("modelId", ""))
        if not provider or not model_id:
            continue
        key = registry_key(provider, model_id)
        existing = registry["models"].get(key, {})
        if existing.get("status") == "blocked":
            continue  # never re-probe blocked models
        if existing.get("status") == "certified" and not is_cert_stale(existing):
            continue  # fresh cert, skip
        to_probe.append(m)

    if not to_probe:
        print(" All candidates have fresh certifications — nothing to probe.")
        return registry

    print(f" Probing {len(to_probe)} candidate(s) (workers={PROBE_WORKERS}, provider-aware)...")

    # Group candidates by provider for provider-aware concurrency
    by_provider = {}
    for m in to_probe:
        provider = normalize_provider(m.get("provider", ""))
        by_provider.setdefault(provider, []).append(m)

    # Process each provider group with delays
    def _process_provider(provider_name: str, models: list) -> list:
        """Process all models for a single provider sequentially with delays."""
        results = []
        for idx, m in enumerate(models):
            if idx > 0:
                time.sleep(PROBE_PROVIDER_DELAY)
            model_id = m.get("modelId", "")
            result = probe_model(provider_name, model_id, credentials)
            # Merge discovery metadata into result
            result["tier"] = m.get("tier", "")
            result["context"] = m.get("context", "0")
            result["context_tokens"] = _parse_context_tokens(m.get("context", "0"))
            result["sweScore"] = m.get("sweScore", "")
            result["uptime"] = m.get("uptime", 100)
            result["label"] = m.get("label", model_id)
            results.append((m, result))
            # Get provider and model display names
            provider_display = get_provider_display_name(f"{provider_name}/{model_id}", provider_name)
            model_display = get_model_display_name(f"{provider_name}/{model_id}")

            status_str = {
                "certified": "OK",
                "skipped": f"SKIPPED ({result.get('failure_reason', '?')})",
            }.get(result["status"], f"FAIL ({result.get('failure_reason', '?')})")
            print(f" {provider_display}/{model_display}: {status_str}")
        return results

    # Use ThreadPoolExecutor to parallelize across providers
    with ThreadPoolExecutor(max_workers=PROBE_WORKERS) as pool:
        futures = {}
        for provider, models in by_provider.items():
            f = pool.submit(_process_provider, provider, models)
            futures[f] = provider

        for f in as_completed(futures):
            provider = futures[f]
            try:
                provider_results = f.result()
                for (m, result) in provider_results:
                    p = normalize_provider(m.get("provider", ""))
                    model_id = normalize_model_id(m.get("provider", ""), m.get("modelId", ""))
                    key = registry_key(p, model_id)
                    registry["models"][key] = result
            except Exception as e:
                logger.error(f"Error processing provider {provider}: {e}")

    return registry

def _parse_context_tokens(context_str: str) -> int:
    try:
        return int(context_str.replace("k", "000").replace("M", "000000") or "0")
    except Exception:
        return 0

def get_certified_models_for_selection():
    """Get certified models for selection UI."""
    # Load existing probe registry
    registry = {"schema_version": 1, "probe_version": PROBE_VERSION, "updated_at": datetime.now().isoformat(), "models": {}}
    if os.path.exists(CACHE_DIR):
        try:
            with open(os.path.join(CACHE_DIR, "certified_models.json"), "r") as f:
                registry = json.load(f)
                if "schema_version" not in registry:
                    registry["schema_version"] = 1
        except Exception:
            pass

    # Get all models and filter to certified
    models = get_fcm_data()
    if not models:
        return []

    certified_models = []
    for model in models:
        provider = normalize_provider(model["provider"])
        model_id = normalize_model_id(model["provider"], model["modelId"])
        key = registry_key(provider, model_id)
        entry = registry["models"].get(key, {})

        if entry.get("status") == "certified":
            certified_models.append(model)
        elif not certified_models:  # If no certified models, include all
            certified_models.append(model)

    return certified_models

# ── Interactive Model Selection ─────────────────────────────

def format_model_display(model_data, full=False):
    """Format model display for UI."""
    if not model_data:
        return "None"

    model_id = model_data.get("modelId", "")
    provider = model_data.get("provider", "")
    tier = model_data.get("tier", "")
    context = model_data.get("context", "")

    # Get simplified provider name using provider key if available
    full_model_id = normalize_model_id(provider, model_id)
    provider_name = get_provider_display_name(full_model_id, provider)
    model_name = get_model_display_name(full_model_id)

    # Add special tier handling for local models
    display_tier = tier
    if provider in ["ollama", "litellm"] or "local" in provider_name.lower():
        # For local models, create a creative tier based on context size
        if context and int(context.replace("k", "")) >= 128:
            display_tier = "S+ (Local)"
        elif context and int(context.replace("k", "")) >= 64:
            display_tier = "S (Local)"
        elif context and int(context.replace("k", "")) >= 32:
            display_tier = "A+ (Local)"
        else:
            display_tier = "A (Local)"
    elif not tier or tier == "unknown":
        # Handle models without tier info
        display_tier = "Unknown"

    if full:
        return f"{provider_name} | {model_name} ({display_tier}, {context})"
    else:
        return f"{provider_name} | {model_name} ({display_tier})"

def save_selection_cache(routes):
    """Save model selections to cache file."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    data = {
        "selected_at": datetime.now().isoformat(),
        "routes": {}
    }

    for role, model_data in routes.items():
        if model_data:
            data["routes"][role] = {
                "provider": model_data.get("provider", ""),
                "modelId": model_data.get("modelId", ""),
                "tier": model_data.get("tier", ""),
                "context": model_data.get("context", ""),
                "sweScore": model_data.get("sweScore", "")
            }

    try:
        with open(os.path.join(CACHE_DIR, "selected_models.json"), "w") as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Saved selection cache with {len(data['routes'])} routes")
    except Exception as e:
        logger.warning(f"Failed to save selection cache: {e}")

def load_selection_cache():
    """Load cached model selections. Returns None if no cache or stale."""
    cache_file = os.path.join(CACHE_DIR, "selected_models.json")
    if not os.path.exists(cache_file):
        return None

    try:
        with open(cache_file, "r") as f:
            data = json.load(f)

        # Check if cache is recent (24 hours)
        selected_at = datetime.fromisoformat(data.get("selected_at", "2000-01-01T00:00:00"))
        cache_age = datetime.now() - selected_at
        if cache_age > timedelta(hours=24):
            logger.debug("Selection cache is stale (>24 hours)")
            return None

        # Convert back to format expected by map_tiers
        routes = {}
        for role, route_data in data.get("routes", {}).items():
            routes[role] = {
                "modelId": route_data.get("modelId", ""),
                "provider": route_data.get("provider", ""),
                "tier": route_data.get("tier", ""),
                "context": route_data.get("context", ""),
                "sweScore": route_data.get("sweScore", "")
            }
        return routes
    except Exception as e:
        logger.warning(f"Failed to load selection cache: {e}")
        return None

def map_tiers(models):
    """Map models to roles based on tier and capabilities."""
    routes = {"default": None, "background": None, "think": None, "longContext": None}

    for m in models:
        model_id = m.get("modelId", "")
        tier = m.get("tier", "C")
        context = m.get("context", "0")

        # Parse context size
        try:
            ctx_val = int(context.replace("k", "000").replace("M", "000000").replace("1M", "1000000") or "0")
        except:
            ctx_val = 0

        # Think-capable models (reasoning, r1, etc.)
        if not routes["think"] and (
            "r1" in model_id.lower() or
            "v3" in model_id.lower() or
            "reasoning" in model_id.lower() or
            "think" in model_id.lower()
        ):
            routes["think"] = m

        # Long context models (32k+ tokens)
        if not routes["longContext"] and ctx_val >= 32000:
            routes["longContext"] = m

        # Default models (S+ tier preferred)
        if not routes["default"] and tier in ["S+", "S"]:
            routes["default"] = m

        # Background models (A tier)
        if not routes["background"] and tier in ["A+", "A"]:
            routes["background"] = m

    # Fill empty roles with default
    for role in routes:
        if not routes[role] and routes["default"]:
            routes[role] = routes["default"]

    return routes

def interactive_model_selection(models):
    """Interactive model selection menu."""
    selected = map_tiers(models)

    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print("\n" + "="*60)
        print(" 🎯 Edit Model Assignments ")
        print("="*60 + "\n")

        # Show current assignments
        print("Current assignments:\n")
        for i, role in enumerate(["default", "background", "think", "longContext"], 1):
            model_data = selected.get(role)
            display = format_model_display(model_data, full=True)
            role_name = {
                "default": "Default (S)",
                "background": "Background (A)",
                "think": "Thinking (R1)",
                "longContext": "Long Context"
            }[role]
            print(f" [{i}] {role_name:20} → {display}")

        # Get available models by tier
        tier_models = {"S+": [], "S": [], "A+": [], "A": [], "B+": [], "B": [], "": []}
        for m in models:
            tier = m.get("tier", "")
            if tier in tier_models:
                tier_models[tier].append(m)

        # Sort within tiers by model name
        for tier in tier_models:
            tier_models[tier].sort(key=lambda x: x.get("modelId", ""))

        print("\n" + "="*60)
        print("\n [1-4] Change assignment | [5] Save & Launch | [6] Cancel")
        print()

        choice = input("Selection: ").strip()

        try:
            choice_num = int(choice)

            if choice_num == 5:
                # Save and launch
                save_selection_cache(selected)
                return selected
            elif choice_num == 6:
                # Cancel - return None to signal no change
                return None
            elif 1 <= choice_num <= 4:
                # Edit specific tier
                roles = ["default", "background", "think", "longContext"]
                role = roles[choice_num - 1]

                # Show available models for this role
                print(f"\n📋 Available models for '{role}':\n")

                # Determine appropriate tiers for this role
                if role == "think":
                    suitable_tiers = ["S+", "S", "A", "A+", "B", ""]
                elif role == "longContext":
                    suitable_tiers = ["S+", "S", "A", "A+", "B", ""]
                elif role == "default":
                    suitable_tiers = ["S+", "S", "A+"]
                else:  # background
                    suitable_tiers = ["A", "A+", "S", "S+"]

                available_models = []
                for tier in suitable_tiers:
                    available_models.extend(tier_models.get(tier, []))

                # Remove duplicates and sort
                seen = set()
                unique_models = []
                for m in available_models:
                    key = (m.get("provider", ""), m.get("modelId", ""))
                    if key not in seen:
                        seen.add(key)
                        unique_models.append(m)

                if not unique_models:
                    print("No suitable models available for this role.")
                    input("\nPress Enter to continue...")
                    continue

                # Display available models
                for i, m in enumerate(unique_models, 1):
                    current_marker = " ← CURRENT" if selected.get(role) and selected[role].get("modelId") == m.get("modelId") else ""
                    display = format_model_display(m, full=True)
                    print(f" [{i}] {display}{current_marker}")

                print(f"\n [0] Cancel")
                model_choice = input(f"\nSelect model for {role}: ").strip()

                try:
                    model_choice_num = int(model_choice)
                    if model_choice_num == 0:
                        continue
                    elif 1 <= model_choice_num <= len(unique_models):
                        selected[role] = unique_models[model_choice_num - 1]
                        print(f"\n✅ Updated {role} assignment")
                        time.sleep(0.5)
                except ValueError:
                    print("❌ Invalid selection.")
                    time.sleep(0.5)

        except ValueError:
            print("❌ Invalid selection.")

def show_model_selection_prompt(models, timeout=3):
    """Show interactive prompt with model selection. Returns action code."""
    os.system('clear' if os.name == 'posix' else 'cls')

    print("\n" + "="*60)
    print(" 🚀 Current Model Selection ")
    print("="*60 + "\n")

    selected = map_tiers(models)

    # Display model assignments
    for i, role in enumerate(["default", "background", "think", "longContext"], 1):
        model_data = selected.get(role)
        display = format_model_display(model_data)
        role_name = {
            "default": "Default (S)",
            "background": "Background (A)",
            "think": "Thinking (R1)",
            "longContext": "Long Context"
        }[role]
        print(f" {role_name:20} → {display}")

    print("\n" + "="*60)
    print("\n Options:")
    print(f" [1] ✅ Accept & Launch (timeout in {timeout}s)")
    print(" [2] 🔄 Refresh from providers")
    print(" [3] ✏️  Edit model assignments")
    print()

    # Set up timeout using threading instead of signal (more portable)
    import threading
    import queue

    q = queue.Queue()
    timeout_occurred = [False]

    def input_thread():
        try:
            choice = input("Selection [1-3]: ").strip()
            q.put(choice)
        except:
            q.put(None)

    def timeout_thread():
        timeout_occurred[0] = True
        q.put(None)

    # Start input thread
    input_t = threading.Thread(target=input_thread)
    input_t.daemon = True
    input_t.start()

    # Start timeout thread
    if timeout > 0:
        timeout_t = threading.Thread(target=timeout_thread)
        timeout_t.daemon = True
        timeout_t.start()
        timeout_t.join(timeout)

    # Wait for input or timeout
    try:
        choice = q.get_nowait()
        timeout_occurred[0] = False
    except queue.Empty:
        choice = None

    if timeout_occurred[0]:
        print(f"\n⏰ Timeout! Accepting current selection.")
        return 0

    if not choice:
        return 0  # Accept (timeout)

    try:
        choice_num = int(choice)
        if 1 <= choice_num <= 3:
            return choice_num - 1  # Convert to 0-based
    except ValueError:
        pass

    print("❌ Invalid choice. Accepting current selection.")
    time.sleep(1)
    return 0

def print_summary(selected_models, available_providers):
    """Print beautiful summary."""
    print("\n🚀 Frugality - Model Routing")
    print("=" * 50)

    # Print active providers
    if available_providers:
        print("✅ Providers available: %s" % ", ".join(available_providers))
    else:
        print("❌ No providers configured")

    # Print model assignments with provider info
    for slot in ["MODEL_OPUS", "MODEL_SONNET", "MODEL_HAIKU", "MODEL"]:
        if slot in selected_models:
            model = selected_models[slot]
            model_id = normalize_model_id(model["provider"], model["modelId"])

            # Get provider and model display names
            provider_name = get_provider_display_name(model_id, model["provider"])
            model_name = get_model_display_name(model_id)

            # Format as provider | model to show location
            display = f"{provider_name} | {model_name}"

            # Get tier with special handling for local models
            tier = model.get("tier", "unknown")
            if model["provider"] in ["ollama", "litellm"] or "local" in provider_name.lower():
                # For local models, create creative tier based on context
                context = model.get("context", "32k")
                if context and int(context.replace("k", "")) >= 128:
                    tier = "S+ (Local)"
                elif context and int(context.replace("k", "")) >= 64:
                    tier = "S (Local)"
                elif context and int(context.replace("k", "")) >= 32:
                    tier = "A+ (Local)"
                else:
                    tier = "A (Local)"

            tier_emoji = {"S+": "⭐", "S": "🌟", "A": "💪", "B": "🔧", "C": "🔰"}.get(tier.split(" ")[0], "❓")

            # Get thinking status
            thinking = ""
            model_lower = model["modelId"].lower()
            if any(keyword in model_lower for keyword in ["kimi", "nemotron", "deepseek-r1", "qwq"]):
                thinking = " 🧠"

            print(f"{slot:<12} → {display:<35} {tier_emoji} {thinking}")

    print("=" * 50)
    print("💡 Tip: Run 'claude-frugal' to start coding with free models!")

def main():
    parser = argparse.ArgumentParser(description="Frugality - Free model routing")
    parser.add_argument("--refresh", action="store_true", help="Force fresh model discovery")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--check-keys", action="store_true", help="Check API keys only")
    parser.add_argument("--skip-probe", action="store_true", help="Skip model probing (use all models)")
    parser.add_argument("--prompt", action="store_true", help="Show interactive model selection")
    parser.add_argument("--edit", action="store_true", help="Edit model assignments")
    parser.add_argument("--timeout", type=int, default=3, help="Timeout for prompt mode (seconds)")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Handle special modes
    if args.check_keys:
        available_providers = get_existing_keys()
        if available_providers:
            print("✅ Found API keys for: %s" % ", ".join(available_providers.keys()))
        else:
            print("❌ No API keys found")
            print("💡 Run: free-coding-models (interactive setup)")
        return

    if args.edit:
        # Load certified models and run editor
        models = get_certified_models_for_selection()
        if not models:
            print("❌ No certified models found.")
            print("💡 Run: claude-frugal --refresh first")
            return

        selected = interactive_model_selection(models)
        if selected is None:
            print("\n❌ Edit cancelled")
            return

        # Build config from selected models
        selected_list = []
        for role in ["default", "background", "think", "longContext"]:
            if selected.get(role):
                selected_list.append(selected[role])

        if selected_list:
            available_providers = get_existing_keys()
            write_env_file({"default": selected.get("default"),
                          "background": selected.get("background"),
                          "think": selected.get("think"),
                          "longContext": selected.get("longContext")},
                         available_providers)
            print("\n✅ Model assignments updated!")
        return

    if args.prompt:
        # Load certified models and show prompt
        models = get_certified_models_for_selection()
        if not models:
            print("❌ No certified models found.")
            print("💡 Run: claude-frugal --refresh first")
            return

        # Show the prompt and get user choice
        action = show_model_selection_prompt(models, args.timeout)

        if action == 1:  # Refresh
            print("\n🔄 Refreshing models...")
            main()  # Restart with --refresh
            return
        elif action == 2:  # Edit
            args.edit = True
            main()  # Restart in edit mode
            return

        # action == 0 means accept, continue below
        # Use cached selection if available
        cached = load_selection_cache()
        if cached:
            models = []
            for role in ["default", "background", "think", "longContext"]:
                if cached.get(role):
                    models.append(cached[role])
            if models:
                selected = {"default": cached.get("default"),
                           "background": cached.get("background"),
                           "think": cached.get("think"),
                           "longContext": cached.get("longContext")}
                # Build config from cached selection
                available_providers = get_existing_keys()
                write_env_file(selected, available_providers)
                print_summary(selected, available_providers)
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

    # If skipping probe, use all models directly
    if args.skip_probe:
        certified_models = models
        print("\n⏩ Skipping model probe - using all available models")
    else:
        # Build credentials from API keys
        credentials = {"apiKeys": {}}
        for provider in available_providers:
            if provider in PROVIDER_PREFIXES:
                prefix = PROVIDER_PREFIXES[provider]
                credentials["apiKeys"][provider] = f"sk-or-{prefix}-placeholder"

        # Create cache directory if it doesn't exist
        os.makedirs(CACHE_DIR, exist_ok=True)

        # Load existing probe registry or create new one
        registry = {"schema_version": 1, "probe_version": PROBE_VERSION, "updated_at": datetime.now().isoformat(), "models": {}}
        if os.path.exists(os.path.join(CACHE_DIR, "certified_models.json")):
            try:
                with open(os.path.join(CACHE_DIR, "certified_models.json"), "r") as f:
                    registry = json.load(f)
                    # Update schema version if needed
                    if "schema_version" not in registry:
                        registry["schema_version"] = 1
            except Exception:
                pass

        # Run probes to verify models work
        print("\n🔍 Testing models with tool calls...")
        registry = run_probes(models, registry, credentials)

        # Save updated registry
        try:
            with open(os.path.join(CACHE_DIR, "certified_models.json"), "w") as f:
                json.dump(registry, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save probe registry: {e}")

        # Filter to only certified models for selection
        certified_models = []
        for model in models:
            provider = normalize_provider(model["provider"])
            model_id = normalize_model_id(model["provider"], model["modelId"])
            key = registry_key(provider, model_id)
            entry = registry["models"].get(key, {})

            # Only include certified models, unless no models are certified
            if entry.get("status") == "certified":
                certified_models.append(model)
            elif not certified_models:  # If no certified models yet, include all
                certified_models.append(model)

        if not certified_models:
            print("❌ No models responded correctly to tool calls.")
            print("💡 Try --skip-probe to use all models without testing")
            print("💡 Or check your API keys and try again")
            sys.exit(1)

        print(f"\n✅ {len(certified_models)} model(s) certified for tool use")

    # Select best models from certified ones
    selected = select_best_models(certified_models, available_providers)

    if not selected:
        print("❌ No suitable models found.")
        print("💡 Tip: Check your API keys or try --refresh")
        sys.exit(1)

    # Convert to tier format for saving
    tier_selected = {}
    for slot, model in selected.items():
        if slot in ["MODEL_OPUS", "MODEL_SONNET", "MODEL_HAIKU"]:
            tier_name = {"MODEL_OPUS": "default", "MODEL_SONNET": "background", "MODEL_HAIKU": "think"}[slot]
            tier_selected[tier_name] = model

    # Save selection cache
    save_selection_cache(tier_selected)

    # Write config
    write_env_file(selected, available_providers)

    # Print summary
    print_summary(selected, available_providers)

    logger.info("✅ Configuration complete")

if __name__ == "__main__":
    main()