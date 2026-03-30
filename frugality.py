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
CCR_CONFIG_PATH = os.path.join(HOME, ".claude-code-router", "config.json")
CACHE_DIR = os.path.join(HOME, ".frugality", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "last-known-good.json")
CERT_REGISTRY_FILE = os.path.join(CACHE_DIR, "certified_models.json")
SELECTION_CACHE_FILE = os.path.join(CACHE_DIR, "selected_models.json")

CERT_SCHEMA_VERSION = 1
PROBE_VERSION = 2  # Incremented: forces recertification on next --refresh
PROBE_PROFILE = "tool_chat"
CERT_TTL_DAYS = 7
PROBE_TIMEOUT = 15
PROBE_WORKERS = 2  # Reduced from 4 to reduce request rate
PROBE_MAX_RETRIES = 2
PROBE_RETRY_DELAY = 2.0
PROBE_PROVIDER_DELAY = 0.2  # 200ms delay between requests to same provider

ECHO_TOOL = {
    "type": "function",
    "function": {
        "name": "echo_number",
        "description": "Echo a number back",
        "parameters": {
            "type": "object",
            "properties": {"value": {"type": "integer"}},
            "required": ["value"],
        },
    },
}

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
    "together": "https://api.together.xyz/v1/chat/completions",
    "cloudflare": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions",
    "perplexity": "https://api.perplexity.ai/chat/completions",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    "ollama": "http://localhost:11434/v1/chat/completions",
    "zai": "https://api.z.ai/api/coding/paas/v4/chat/completions",
    "hyperbolic": "https://api.hyperbolic.xyz/v1/chat/completions",
    "siliconflow": "https://api.siliconflow.com/v1/chat/completions",
    "scaleway": "https://api.scaleway.ai/v1/chat/completions",
    "qwen": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
    "iflow": "https://apis.iflow.cn/v1/chat/completions",
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


def discover_ollama_hosts(credentials: dict) -> list:
    """Discover Ollama hosts from credentials config and check their health."""
    hosts_config = credentials.get("ollama_hosts", {})
    discovered = []

    for host_name, host_url in hosts_config.items():
        provider_name = f"ollama-{host_name}"
        base_url = f"http://{host_url}/api"

        # Check if host is reachable
        try:
            tags_url = f"{base_url}/tags"
            req = urllib.request.Request(tags_url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    models = data.get("models", [])

                    for model in models:
                        model_name = model.get("name", "")
                        discovered.append({
                            "modelId": model_name,
                            "provider": provider_name,
                            "host_url": host_url,
                            "status": "online",
                        })

                    logger.info(f"Discovered {len(models)} models from Ollama host {host_name}")
                else:
                    logger.warning(f"Ollama host {host_name} returned status {resp.status}")
        except urllib.error.URLError as e:
            logger.warning(f"Ollama host {host_name} unreachable: {e.reason}")
        except Exception as e:
            logger.warning(f"Error checking Ollama host {host_name}: {e}")

    return discovered


def probe_ollama_model(provider: str, model_id: str, credentials: dict) -> dict:
    """Probe Ollama model to determine capabilities and response characteristics."""
    base_url = PROVIDER_BASE_URLS.get(provider, "http://localhost:11434/v1/chat/completions")

    # Extract host from provider name (ollama-{host})
    host_name = provider.replace("ollama-", "")
    host_config = credentials.get("ollama_hosts", {}).get(host_name, "localhost:11434")
    base_url = f"http://{host_config}/v1/chat/completions"

    start_time = time.time()
    base_entry = {
        "status": "failed",
        "probe_version": PROBE_VERSION,
        "probe_profile": PROBE_PROFILE,
        "provider": normalize_provider(provider),
        "model_id": normalize_model_id(model_id),
        "capabilities": {
            "tool_calling": False,
            "tool_roundtrip": False,
            "valid_json_args": False,
        },
        "failure_reason": None,
        "last_verified_at": datetime.now().isoformat(),
        "response_time_ms": 0,
        "model_type": "unknown",
    }

    try:
        # Test with a simple completion to gauge response time
        resp = _make_chat_request_with_retry(
            base_url,
            "ollama",  # Ollama doesn't need API key for local
            {
                "model": model_id,
                "messages": [{"role": "user", "content": "Count to 5"}],
                "max_tokens": 50,
            },
        )

        response_time = (time.time() - start_time) * 1000
        base_entry["response_time_ms"] = int(response_time)

        # Determine model type based on response time and name
        model_lower = model_id.lower()
        if "coder" in model_lower or "code" in model_lower:
            base_entry["model_type"] = "coder"
        elif "think" in model_lower or "reasoning" in model_lower:
            base_entry["model_type"] = "thinking"
        elif response_time < 100:
            base_entry["model_type"] = "fast"
        elif response_time < 500:
            base_entry["model_type"] = "general"
        else:
            base_entry["model_type"] = "thinking"

        # Try tool calling test
        try:
            tool_resp = _make_chat_request_with_retry(
                base_url,
                "ollama",
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

            choice = tool_resp["choices"][0]["message"]
            tool_calls = choice.get("tool_calls", [])

            if tool_calls and tool_calls[0]["function"]["name"] == "echo_number":
                base_entry["capabilities"]["tool_calling"] = True
                base_entry["capabilities"]["valid_json_args"] = True

                # Try roundtrip
                tool_call_id = tool_calls[0].get("id", "call_test_1")
                round_resp = _make_chat_request_with_retry(
                    base_url,
                    "ollama",
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

                final_content = round_resp["choices"][0]["message"].get("content", "")
                if "49" in final_content:
                    base_entry["capabilities"]["tool_roundtrip"] = True
                    base_entry["status"] = "certified"
                else:
                    base_entry["status"] = "certified"
                    base_entry["failure_reason"] = "roundtrip_incomplete"
            else:
                base_entry["status"] = "certified"
                base_entry["failure_reason"] = "no_tool_call"
        except Exception as e:
            base_entry["status"] = "certified"
            base_entry["failure_reason"] = f"tool_error:{e}"
            # Still certify if basic completion works

    except Exception as e:
        base_entry["failure_reason"] = f"probe_error:{e}"

    return base_entry


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


def save_selection_cache(routes, selected_by="auto"):
    """Save model selections to cache file."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    data = {
        "selected_at": datetime.now().isoformat(),
        "selected_by": selected_by,
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
        atomic_write_json(SELECTION_CACHE_FILE, data)
        logger.debug(f"Saved selection cache with {len(data['routes'])} routes")
    except Exception as e:
        logger.warning(f"Failed to save selection cache: {e}")


def load_selection_cache():
    """Load cached model selections. Returns None if no cache or stale."""
    if not os.path.exists(SELECTION_CACHE_FILE):
        return None

    try:
        with open(SELECTION_CACHE_FILE, "r") as f:
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

        logger.debug(f"Loaded selection cache from {selected_at.isoformat()}")
        return routes
    except Exception as e:
        logger.debug(f"Failed to load selection cache: {e}")
        return None


def is_cloud_provider(provider: str) -> bool:
    """Check if provider is a cloud provider (not local/Ollama)."""
    return not provider.startswith("ollama")


def normalize_provider(provider: str) -> str:

    return provider.strip().lower()


def normalize_model_id(model_id: str) -> str:
    return model_id.strip()


def registry_key(provider: str, model_id: str) -> str:
    return f"{normalize_provider(provider)},{normalize_model_id(model_id)}"


def load_registry() -> dict:
    """Load cert registry. Returns empty registry on missing/corrupt/version-mismatch."""
    empty = {
        "schema_version": CERT_SCHEMA_VERSION,
        "probe_version": PROBE_VERSION,
        "updated_at": "",
        "models": {},
    }
    if not os.path.exists(CERT_REGISTRY_FILE):
        return empty
    try:
        with open(CERT_REGISTRY_FILE) as f:
            data = json.load(f)
        if data.get("schema_version") != CERT_SCHEMA_VERSION:
            logger.warning("Registry schema version mismatch — treating as empty")
            return empty
        return data
    except Exception:
        return empty


def save_registry(registry: dict) -> None:
    registry["updated_at"] = datetime.now().isoformat()
    registry["probe_version"] = PROBE_VERSION
    os.makedirs(CACHE_DIR, exist_ok=True)
    atomic_write_json(CERT_REGISTRY_FILE, registry)


def is_cert_stale(entry: dict) -> bool:
    """Stale if timestamp too old OR probe_version outdated."""
    if entry.get("probe_version", 0) < PROBE_VERSION:
        return True
    try:
        verified = datetime.fromisoformat(entry.get("last_verified_at", "2000-01-01"))
        return datetime.now() - verified > timedelta(days=CERT_TTL_DAYS)
    except Exception:
        return True


def get_certified_models(registry: dict) -> list:
    """Return FCM-shaped model dicts for all certified entries."""
    result = []
    for entry in registry.get("models", {}).values():
        if entry.get("status") != "certified":
            continue
        result.append(
            {
                "modelId": entry["model_id"],
                "provider": entry["provider"],
                "tier": entry.get("tier", "S"),
                "context": entry.get("context", "0"),
                "sweScore": entry.get("sweScore", ""),
                "uptime": entry.get("uptime", 100),
                "label": entry.get("label", entry["model_id"]),
            }
        )
    return result


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


def discover_all_models(credentials: dict):
    """Discover models from both free-coding-models and Ollama hosts."""
    all_models = []

    # Get FCM models
    fcm_models = None
    try:
        fcm_models = get_fcm_data()
        if fcm_models:
            all_models.extend(fcm_models)
    except Exception as e:
        logger.warning(f"Failed to discover FCM models: {e}")

    # Get Ollama models
    ollama_models = discover_ollama_hosts(credentials)
    if ollama_models:
        all_models.extend(ollama_models)

    return all_models


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


def _make_chat_request(url: str, api_key: str, payload: dict) -> dict:
    """POST payload to url. Returns parsed JSON response. Raises on network or HTTP error."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def _make_chat_request_with_retry(url: str, api_key: str, payload: dict) -> dict:
    """
    Retry on transient 429/5xx errors with exponential backoff and jitter.
    For 429 (rate limit), use longer backoffs: 2s, 4s, 8s + jitter.
    """
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
    # Use Ollama-specific probe for Ollama providers
    if normalize_provider(provider).startswith("ollama"):
        return probe_ollama_model(provider, model_id, credentials)

    url = PROVIDER_BASE_URLS.get(
        normalize_provider(provider), "https://api.openai.com/v1/chat/completions"
    )
    api_key = get_api_key(credentials, provider)

    base_entry = {
        "status": "failed",
        "probe_version": PROBE_VERSION,
        "probe_profile": PROBE_PROFILE,
        "provider": normalize_provider(provider),
        "model_id": normalize_model_id(model_id),
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
        return {**base_entry, "status": "skipped", "failure_reason": "unconfigured_provider"}

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


def _parse_context_tokens(context_str: str) -> int:
    try:
        return int(context_str.replace("k", "000").replace("M", "000000") or "0")
    except Exception:
        return 0


# MARKER_START_RUN_PROBES
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
        model_id = normalize_model_id(m.get("modelId", ""))
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
            status_str = {
                "certified": "OK",
                "skipped": f"SKIPPED ({result.get('failure_reason', '?')})",
            }.get(result["status"], f"FAIL ({result.get('failure_reason', '?')})")
            print(f" {provider_name}/{model_id}: {status_str}")
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
                    model_id = normalize_model_id(m.get("modelId", ""))
                    key = registry_key(p, model_id)
                    registry["models"][key] = result
            except Exception as e:
                logger.error(f"Error processing provider {provider}: {e}")

    return registry

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

    # Prefer cloud providers over Ollama when both available
    for role, route in routes.items():
        if route and is_cloud_provider(route.get("provider", "")):
            # If this is a cloud provider, check if we could replace an Ollama route
            for other_role, other_route in routes.items():
                if other_route and not is_cloud_provider(other_route.get("provider", "")):
                    # If role is more important/earlier, prefer cloud
                    role_priority = ["default", "background", "think", "longContext"]
                    if role_priority.index(role) <= role_priority.index(other_role):
                        routes[other_role] = route

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


def format_model_display(model_data, full=False):
    """Format model data for display."""
    if not model_data:
        return "(none selected)"

    model_id = model_data.get("modelId", "unknown")
    provider = model_data.get("provider", "unknown")
    tier = model_data.get("tier", "")
    context = model_data.get("context", "")
    swe_score = model_data.get("sweScore", "")

    if full:
        return f"{provider}/{model_id} [{tier}] {context} {swe_score}"
    else:
        # Abbreviated display for prompt mode
        parts = [f"{provider}/{model_id}"]
        if tier:
            parts.append(f"[{tier}]")
        if context and context != "0":
            if "M" in context:
                parts.append(f"[{context}]")
            else:
                parts.append(f"[{context}]")
        return " ".join(parts)


def show_model_selection_prompt(models, timeout=3):
    """Show interactive prompt with model selection. Returns action code."""
    os.system('clear' if os.name == 'posix' else 'cls')

    print("\n" + "="*50)
    print(" Current Model Selection ")
    print("="*50 + "\n")

    selected = map_tiers(models)

    # Display model assignments
    for i, role in enumerate(["default", "background", "think", "longContext"], 1):
        model_data = selected.get(role)
        display = format_model_display(model_data)
        role_name = role.replace("default", "default (S)")
        print(f" {role_name:20} → {display}")

    print("\n" + "="*50)
    print("\n Options:")
    print(f" [1] ✓ Accept & Launch (timeout in {timeout}s)")
    print(" [2] ♻️  Refresh from providers")
    print(" [3] ✎ Edit model assignments")
    print()

    # Set up timeout
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError()

    # Configure timeout
    if hasattr(signal, 'SIGALRM'):
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

    try:
        choice = input("Selection [1-3]: ").strip()
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)  # Cancel alarm

        if not choice:
            return 0  # Accept (timeout)

        try:
            choice_num = int(choice)
            if 1 <= choice_num <= 3:
                return choice_num - 1  # Convert to 0-based
        except ValueError:
            pass

        print("Invalid choice. Accepting current selection.")
        return 0

    except (TimeoutError, KeyboardInterrupt):
        print("\nTime's up! Accepting current selection...")
        return 0

    return 0


def interactive_model_selection(models):
    """Interactive model selection menu."""
    selected = map_tiers(models)

    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print("\n" + "="*50)
        print(" Edit Model Assignments ")
        print("="*50 + "\n")

        # Show current assignments
        print("Current assignments:\n")
        for i, role in enumerate(["default", "background", "think", "longContext"], 1):
            model_data = selected.get(role)
            display = format_model_display(model_data, full=True)
            print(f" [{i}] {role:15} → {display}")

        # Get available models by tier
        tier_models = {"S+": [], "S": [], "A+": [], "A": [], "B+": [], "B": [], "": []}
        for m in models:
            tier = m.get("tier", "")
            if tier in tier_models:
                tier_models[tier].append(m)

        # Sort within tiers by model name
        for tier in tier_models:
            tier_models[tier].sort(key=lambda x: x.get("modelId", ""))

        print("\n" + "="*50)
        print("\n [1-4] Change assignment | [5] Save & Exit | [6] Cancel")
        print()

        choice = input("Selection: ").strip()

        try:
            choice_num = int(choice)

            if choice_num == 5:
                # Save and exit
                return selected
            elif choice_num == 6:
                # Cancel - return None to signal no change
                return None
            elif 1 <= choice_num <= 4:
                # Edit specific tier
                roles = ["default", "background", "think", "longContext"]
                role = roles[choice_num - 1]

                # Show available models for this role
                print(f"\nAvailable models for '{role}':\n")

                # Determine appropriate tiers for this role
                if role == "think":
                    suitable_tiers = ["", "B", "B+", "A", "A+", "S", "S+"]
                elif role == "longContext":
                    suitable_tiers = ["", "B", "B+", "A", "A+", "S", "S+"]
                elif role == "default":
                    suitable_tiers = ["S", "S+", "A+", "A"]
                else:  # background
                    suitable_tiers = ["A+", "A", "S", "S+"]

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
                    print(f" [{i}] {format_model_display(m, full=True)}{current_marker}")

                print(f"\n [0] Cancel")
                model_choice = input(f"\nSelect model for {role}: ").strip()

                try:
                    model_choice_num = int(model_choice)
                    if model_choice_num == 0:
                        continue
                    elif 1 <= model_choice_num <= len(unique_models):
                        selected[role] = unique_models[model_choice_num - 1]
                        print(f"\n✓ Updated {role} assignment")
                        time.sleep(0.5)
                except ValueError:
                    print("Invalid selection.")
                    time.sleep(0.5)

        except ValueError:
            print("Invalid selection.")
            time.sleep(0.5)


def print_selection_summary(selected):
    logger.info("Frugality model selection:")
    for role in ["default", "background", "think", "longContext"]:
        model_data = selected.get(role)
        if model_data:
            model_id = model_data.get("modelId", "unknown")
            provider = model_data.get("provider", "unknown")
            tier = model_data.get("tier", "unknown")
            context = model_data.get("context", "unknown")
            uptime = model_data.get("uptime", "unknown")
            logger.info(f"  {role:12} → {provider:15} / {model_id}")
            logger.info(f"                 {tier:3}-tier | {context:>8} context | {uptime}% uptime")
        else:
            logger.info(f"  {role:12} → (none selected)")

def print_provider_details(credentials):
    """Print configured provider endpoints."""
    logger.info("Provider endpoints:")
    for provider, base_url in sorted(PROVIDER_BASE_URLS.items()):
        api_key = get_api_key(credentials, provider)
        status = "✓ configured" if api_key else "⊘ unconfigured"
        logger.info(f"  {provider:15} {status:20} {base_url}")


def update_ccr_config(models: list, credentials: dict, use_cache: bool = False) -> bool:
    """Update CCR config, optionally using cached selections."""
    logger.info("Configuring Claude Code Router")

    # Try to use cached selections if requested
    if use_cache:
        cached = load_selection_cache()
        if cached:
            logger.info("Using cached model selections")
            selected = cached
        else:
            selected = map_tiers(models)
    else:
        selected = map_tiers(models)

    if not selected.get("default"):
        logger.error("No suitable models found for default route")
        return False

    print_selection_summary(selected)
    providers = build_provider_config(models, credentials)
    router_config = {}
    for role, model_data in selected.items():
        if model_data:
            model_id = model_data["modelId"]
            provider = model_data.get("provider", "")
            router_config[role] = f"{provider},{model_id}" if provider else model_id
    ccr_config = {"Providers": providers, "Router": router_config}
    try:
        atomic_write_json(CCR_CONFIG_PATH, ccr_config)
        logger.info(f"Updated CCR config at {CCR_CONFIG_PATH}")
        # Save to selection cache if we mapped tiers
        if not use_cache or not cached:
            save_selection_cache(selected, "auto")
        return True
    except Exception as e:
        logger.error(f"Failed to write config: {e}")
        return False


def run_default_mode(credentials: dict) -> bool:
    print("Using certified model registry")
    registry = load_registry()
    certified = get_certified_models(registry)
    if not certified:
        print("ERROR: No certified models found.")
        print("Run 'frugal-claude --refresh' to discover and certify models.")
        return False
    print(f"  {len(certified)} certified model(s) available")
    print()
    print_provider_details(credentials)
    print()
    return update_ccr_config(certified, credentials)


def run_refresh_mode(credentials: dict) -> bool:
    print("Refresh requested — discovering candidates from free-coding-models")
    candidates = get_fcm_data_with_cache()
    if not candidates:
        return False
    print(f"  Discovered {len(candidates)} candidate(s)")
    registry = load_registry()
    registry = run_probes(candidates, registry, credentials)
    save_registry(registry)
    certified = get_certified_models(registry)
    print(f"  Certified {len(certified)}/{len(candidates)} models")
    if not certified:
        print("ERROR: No models passed certification.")
        print("Check API keys and provider availability.")
        return False
    return update_ccr_config(certified, credentials)



def run_prompt_mode(credentials: dict, timeout: int = 3) -> int:
    """Run interactive prompt mode, returns action code."""
    print("Using certified model registry")
    registry = load_registry()
    certified = get_certified_models(registry)

    if not certified:
        print("ERROR: No certified models found.")
        print("Run 'frugal-claude --refresh' to discover and certify models.")
        return -1

    print(f" {len(certified)} certified model(s) available")
    print()

    # Show the prompt and get user choice
    action = show_model_selection_prompt(certified, timeout)
    return action


def run_edit_mode(credentials: dict) -> bool:
    """Run interactive model selection editor."""
    print("Using certified model registry")
    registry = load_registry()
    certified = get_certified_models(registry)

    if not certified:
        print("ERROR: No certified models found.")
        print("Run 'frugal-claude --refresh' to discover and certify models.")
        return False

    # Run interactive selection
    selected = interactive_model_selection(certified)

    if selected is None:
        print("\nEdit cancelled, no changes made.")
        return True  # Not an error, just cancelled

    # Update config with new selection
    success = update_ccr_config([selected[k] for k in selected if selected[k]], credentials)
    if success:
        save_selection_cache(selected, "edit")
    return success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Frugality - Cost-optimized AI model routing"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug output"
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Only show errors")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Discover and certify candidate models, then update CCR config",
    )
    parser.add_argument(
        "--opencode", action="store_true", help="Write OpenCode config (not yet implemented)"
    )
    parser.add_argument(
        "--prompt", action="store_true", help="Show interactive model selection prompt"
    )
    parser.add_argument(
        "--edit", action="store_true", help="Open interactive model assignment editor"
    )
    parser.add_argument(
        "--timeout", type=int, default=3, help="Timeout for prompt mode (default: 3s)"
    )
    args = parser.parse_args()
    setup_logging(args.verbose, args.quiet)
    credentials = get_fcm_credentials()
    
    # Determine mode
    if args.prompt:
        # Return action code directly for wrapper script
        sys.exit(run_prompt_mode(credentials, args.timeout))
    elif args.edit:
        success = run_edit_mode(credentials)
    elif args.refresh:
        success = run_refresh_mode(credentials)
    else:
        success = run_default_mode(credentials)
    
    if success:
        logger.info("Configuration complete")
    sys.exit(0 if success else 1)
