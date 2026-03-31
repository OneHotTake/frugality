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
CACHE_DIR = os.path.join(HOME, ".frugality", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "last-known-good.json")
CERT_REGISTRY_FILE = os.path.join(CACHE_DIR, "certified_models.json")
SELECTION_CACHE_FILE = os.path.join(CACHE_DIR, "selected_models.json")
ENV_OUTPUT_FILE = os.path.join(HOME, ".frugality", "current_env.sh")

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
    backup_path = "%s.backup_%s" % (path, timestamp)
    import shutil
    shutil.copy2(path, backup_path)
    logger.info("Backed up existing config to %s" % backup_path)


def atomic_write_json(path, data):
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name)

    backup_file(path)

    fd, temp_path = tempfile.mkstemp(dir=dir_name, text=True)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(temp_path, path)


def atomic_write_text(path, text):
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name)

    fd, temp_path = tempfile.mkstemp(dir=dir_name, text=True)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.replace(temp_path, path)


def classify_call_weight(message_count, has_tools, prompt_length):
    """Classify an API call as lightweight or heavy.

    Lightweight calls are quota-check and topic-detection style: short,
    tool-free, low-token. Heavy is everything else.
    """
    if message_count <= 2 and not has_tools and prompt_length < 500:
        return "lightweight"
    return "heavy"


def discover_ollama_hosts(credentials):
    """Discover Ollama hosts from credentials config and check their health."""
    hosts_config = credentials.get("ollama_hosts", {})
    discovered = []

    for host_name, host_url in hosts_config.items():
        provider_name = "ollama-%s" % host_name
        base_url = "http://%s/api" % host_url

        try:
            tags_url = "%s/tags" % base_url
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

                    logger.info("Discovered %d models from Ollama host %s" % (len(models), host_name))
                else:
                    logger.warning("Ollama host %s returned status %d" % (host_name, resp.status))
        except urllib.error.URLError as e:
            logger.warning("Ollama host %s unreachable: %s" % (host_name, e.reason))
        except Exception as e:
            logger.warning("Error checking Ollama host %s: %s" % (host_name, e))

    return discovered


def probe_ollama_model(provider, model_id, credentials):
    """Probe Ollama model to determine capabilities and response characteristics."""
    host_name = provider.replace("ollama-", "")
    host_config = credentials.get("ollama_hosts", {}).get(host_name, "localhost:11434")
    base_url = "http://%s/v1/chat/completions" % host_config

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
        resp = _make_chat_request_with_retry(
            base_url,
            "ollama",
            {
                "model": model_id,
                "messages": [{"role": "user", "content": "Count to 5"}],
                "max_tokens": 50,
            },
        )

        response_time = (time.time() - start_time) * 1000
        base_entry["response_time_ms"] = int(response_time)

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
            base_entry["failure_reason"] = "tool_error:%s" % e

    except Exception as e:
        base_entry["failure_reason"] = "probe_error:%s" % e

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
            logger.info("Using cached config from %s" % cached_at.isoformat())
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
        logger.debug("Saved %d models to cache" % len(models))
    except Exception as e:
        logger.warning("Failed to save cache: %s" % e)


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
        logger.debug("Saved selection cache with %d routes" % len(data['routes']))
    except Exception as e:
        logger.warning("Failed to save selection cache: %s" % e)


def load_selection_cache():
    """Load cached model selections. Returns None if no cache or stale."""
    if not os.path.exists(SELECTION_CACHE_FILE):
        return None

    try:
        with open(SELECTION_CACHE_FILE, "r") as f:
            data = json.load(f)

        selected_at = datetime.fromisoformat(data.get("selected_at", "2000-01-01T00:00:00"))
        cache_age = datetime.now() - selected_at
        if cache_age > timedelta(hours=24):
            logger.debug("Selection cache is stale (>24 hours)")
            return None

        routes = {}
        for role, route_data in data.get("routes", {}).items():
            routes[role] = {
                "modelId": route_data.get("modelId", ""),
                "provider": route_data.get("provider", ""),
                "tier": route_data.get("tier", ""),
                "context": route_data.get("context", ""),
                "sweScore": route_data.get("sweScore", "")
            }

        logger.debug("Loaded selection cache from %s" % selected_at.isoformat())
        return routes
    except Exception as e:
        logger.debug("Failed to load selection cache: %s" % e)
        return None


def is_cloud_provider(provider):
    """Check if provider is a cloud provider (not local/Ollama)."""
    return not provider.startswith("ollama")


def normalize_provider(provider):
    return provider.strip().lower()


def normalize_model_id(model_id):
    return model_id.strip()


def registry_key(provider, model_id):
    return "%s,%s" % (normalize_provider(provider), normalize_model_id(model_id))


def load_registry():
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
            logger.warning("Registry schema version mismatch -- treating as empty")
            return empty
        return data
    except Exception:
        return empty


def save_registry(registry):
    registry["updated_at"] = datetime.now().isoformat()
    registry["probe_version"] = PROBE_VERSION
    os.makedirs(CACHE_DIR, exist_ok=True)
    atomic_write_json(CERT_REGISTRY_FILE, registry)


def is_cert_stale(entry):
    """Stale if timestamp too old OR probe_version outdated."""
    if entry.get("probe_version", 0) < PROBE_VERSION:
        return True
    try:
        verified = datetime.fromisoformat(entry.get("last_verified_at", "2000-01-01"))
        return datetime.now() - verified > timedelta(days=CERT_TTL_DAYS)
    except Exception:
        return True


def get_certified_models(registry):
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
            logger.debug("FCM stderr: %s" % result.stderr)
            raise Exception("FCM exited with code %d" % result.returncode)

        if not result.stdout:
            raise Exception("FCM returned empty output")

        data = json.loads(result.stdout.strip())
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

        save_cache(data)
        return data

    except json.JSONDecodeError as e:
        logger.debug("JSON decode error: %s" % e)
        raise Exception("Invalid JSON from FCM: %s" % e)
    except Exception as e:
        logger.debug("FCM error: %s" % e)
        raise e


def discover_all_models(credentials):
    """Discover models from both free-coding-models and Ollama hosts."""
    all_models = []

    fcm_models = None
    try:
        fcm_models = get_fcm_data()
        if fcm_models:
            all_models.extend(fcm_models)
    except Exception as e:
        logger.warning("Failed to discover FCM models: %s" % e)

    ollama_models = discover_ollama_hosts(credentials)
    if ollama_models:
        all_models.extend(ollama_models)

    return all_models


def get_fcm_data_with_cache():
    try:
        return get_fcm_data()
    except Exception as e:
        logger.warning("FCM discovery failed: %s. Attempting cache fallback." % e)
        cached = load_cache()
        if cached:
            logger.info("Using cached config from cache file")
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


def _make_chat_request(url, api_key, payload):
    """POST payload to url. Returns parsed JSON response. Raises on network or HTTP error."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def _make_chat_request_with_retry(url, api_key, payload):
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
                base_delay = PROBE_RETRY_DELAY * (2 ** attempt)
                jitter = random.uniform(0, 0.5)
                delay = base_delay + jitter
                if e.code == 429:
                    delay *= 2
                logger.debug("Retry attempt %d after %.2fs (error %d)" % (attempt + 1, delay, e.code))
                time.sleep(delay)
                last_exc = e
                continue
            raise
    raise last_exc


def probe_model(provider, model_id, credentials):
    """
    Certification probe for profile 'tool_chat'.
    Step 1+2: Send tool-call request -> verify echo_number(value=7) emitted
    Step 3:   Send tool result -> verify final text answer contains "49"
    Returns a registry entry dict (no tier/context metadata -- caller adds those).
    """
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
                "failure_reason": "auth_error:%d" % e.code,
            }
        return {**base_entry, "failure_reason": "http_error:%d" % e.code}
    except urllib.error.URLError as e:
        return {**base_entry, "status": "skipped", "failure_reason": "connectivity:%s" % e.reason}
    except Exception as e:
        return {**base_entry, "failure_reason": "request_error:%s" % e}

    try:
        choice = resp["choices"][0]["message"]
        tool_calls = choice.get("tool_calls") or []
        if not tool_calls:
            return {**base_entry, "failure_reason": "no_tool_call"}
        tc = tool_calls[0]
        if tc["function"]["name"] != "echo_number":
            return {
                **base_entry,
                "failure_reason": "wrong_tool_name:%s" % tc['function']['name'],
            }
        args = json.loads(tc["function"]["arguments"])
        if args.get("value") != 7:
            return {**base_entry, "failure_reason": "bad_args:value=%s" % args.get('value')}
    except Exception as e:
        return {**base_entry, "failure_reason": "parse_error:%s" % e}

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
        if "49" not in content:
            return {**base_entry, "failure_reason": "roundtrip_result_ignored"}
    except Exception as e:
        return {**base_entry, "failure_reason": "roundtrip_error:%s" % e}

    base_entry["capabilities"]["tool_roundtrip"] = True
    return {**base_entry, "status": "certified"}


def _parse_context_tokens(context_str):
    try:
        return int(context_str.replace("k", "000").replace("M", "000000") or "0")
    except Exception:
        return 0


def run_probes(candidates, registry, credentials):
    """
    Determine which candidates need probing, run with provider-aware concurrency,
    merge results into registry. Returns updated registry.
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
            continue
        if existing.get("status") == "certified" and not is_cert_stale(existing):
            continue
        to_probe.append(m)

    if not to_probe:
        print(" All candidates have fresh certifications -- nothing to probe.")
        return registry

    print(" Probing %d candidate(s) (workers=%d, provider-aware)..." % (len(to_probe), PROBE_WORKERS))

    by_provider = {}
    for m in to_probe:
        provider = normalize_provider(m.get("provider", ""))
        by_provider.setdefault(provider, []).append(m)

    def _process_provider(provider_name, models):
        """Process all models for a single provider sequentially with delays."""
        results = []
        for idx, m in enumerate(models):
            if idx > 0:
                time.sleep(PROBE_PROVIDER_DELAY)
            model_id = m.get("modelId", "")
            result = probe_model(provider_name, model_id, credentials)
            result["tier"] = m.get("tier", "")
            result["context"] = m.get("context", "0")
            result["context_tokens"] = _parse_context_tokens(m.get("context", "0"))
            result["sweScore"] = m.get("sweScore", "")
            result["uptime"] = m.get("uptime", 100)
            result["label"] = m.get("label", model_id)
            results.append((m, result))
            status_str = {
                "certified": "OK",
                "skipped": "SKIPPED (%s)" % result.get('failure_reason', '?'),
            }.get(result["status"], "FAIL (%s)" % result.get('failure_reason', '?'))
            print(" %s/%s: %s" % (provider_name, model_id, status_str))
        return results

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
                logger.error("Error processing provider %s: %s" % (provider, e))

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
            for other_role, other_route in routes.items():
                if other_route and not is_cloud_provider(other_route.get("provider", "")):
                    role_priority = ["default", "background", "think", "longContext"]
                    if role_priority.index(role) <= role_priority.index(other_role):
                        routes[other_role] = route

    for role in routes:
        if not routes[role] and routes["default"]:
            routes[role] = routes["default"]

    return routes


def _select_best_openrouter_model(certified):
    """Select the best S-tier model available via OpenRouter for claudish invocation.

    Claudish routes through OpenRouter, so we prefer openrouter-provider models.
    Falls back to any S-tier model if no openrouter model is found.
    """
    # Prefer openrouter S-tier
    for m in certified:
        if m.get("provider") == "openrouter" and m.get("tier") in ["S+", "S"]:
            return m

    # Fall back to any S-tier
    for m in certified:
        if m.get("tier") in ["S+", "S"]:
            return m

    # Fall back to first available
    if certified:
        return certified[0]

    return None


def write_env_file(selected, best_model):
    """Write shell-sourceable env file to ~/.frugality/current_env.sh."""
    default_model = selected.get("default") or {}
    background_model = selected.get("background") or {}
    think_model = selected.get("think") or {}
    longctx_model = selected.get("longContext") or {}

    default_id = default_model.get("modelId", "")
    background_id = background_model.get("modelId", "")
    think_id = think_model.get("modelId", "")
    longctx_id = longctx_model.get("modelId", "")

    active_provider = best_model.get("provider", "openrouter") if best_model else "openrouter"
    best_model_id = best_model.get("modelId", "") if best_model else ""

    # Build claudish invocation string
    # Use openrouter@ prefix if the model is from openrouter
    if active_provider == "openrouter" and best_model_id:
        claudish_model_ref = "openrouter@%s" % best_model_id
    elif best_model_id:
        claudish_model_ref = "%s@%s" % (active_provider, best_model_id)
    else:
        claudish_model_ref = ""

    lines = [
        "#!/usr/bin/env bash",
        "# Auto-generated by frugality.py -- do not edit manually",
        "# Generated at: %s" % datetime.now().isoformat(),
        "",
        "export FRUG_DEFAULT_MODEL=\"%s\"" % default_id,
        "export FRUG_BACKGROUND_MODEL=\"%s\"" % background_id,
        "export FRUG_THINK_MODEL=\"%s\"" % think_id,
        "export FRUG_LONGCTX_MODEL=\"%s\"" % longctx_id,
        "export FRUG_ACTIVE_PROVIDER=\"%s\"" % active_provider,
        "export FRUG_CLAUDISH_INVOCATION=\"claudish --model %s\"" % claudish_model_ref,
        "",
    ]

    env_content = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(ENV_OUTPUT_FILE), exist_ok=True)
    atomic_write_text(ENV_OUTPUT_FILE, env_content)
    logger.info("Wrote env file to %s" % ENV_OUTPUT_FILE)


def print_human_summary(selected, best_model):
    """Print human-readable summary of selected models."""
    print("")
    print("=" * 50)
    print(" Frugality Model Selection (Claudish backend)")
    print("=" * 50)
    print("")

    role_labels = {
        "default": ("default (S)", "General coding"),
        "background": ("background (A)", "Lightweight/background tasks"),
        "think": ("think", "Reasoning tasks"),
        "longContext": ("longContext", "Large file/context tasks"),
    }

    for role, (label, desc) in role_labels.items():
        model_data = selected.get(role)
        if model_data:
            model_id = model_data.get("modelId", "?")
            provider = model_data.get("provider", "?")
            tier = model_data.get("tier", "?")
            context = model_data.get("context", "?")
            print("  %-22s -> %s/%s [%s] %s" % (label, provider, model_id, tier, context))
            print("    (%s)" % desc)
        else:
            print("  %-22s -> (none selected)" % label)
        print("")

    if best_model:
        print("  Claudish invocation: claudish --model %s@%s" % (
            best_model.get("provider", "openrouter"),
            best_model.get("modelId", "")
        ))
    print("")
    print("=" * 50)


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
            logger.info("  %12s -> %15s / %s" % (role, provider, model_id))
            logger.info("                 %3s-tier | %8s context | %s%% uptime" % (tier, context, uptime))
        else:
            logger.info("  %12s -> (none selected)" % role)


def print_provider_details(credentials):
    """Print configured provider endpoints."""
    logger.info("Provider endpoints:")
    for provider, base_url in sorted(PROVIDER_BASE_URLS.items()):
        api_key = get_api_key(credentials, provider)
        status = "configured" if api_key else "unconfigured"
        logger.info("  %15s %20s %s" % (provider, status, base_url))


def run_default_mode(credentials):
    print("Using certified model registry")
    registry = load_registry()
    certified = get_certified_models(registry)
    if not certified:
        print("ERROR: No certified models found.")
        print("Run 'frugal-claude --refresh' to discover and certify models.")
        return False
    print("  %d certified model(s) available" % len(certified))
    print()
    print_provider_details(credentials)
    print()

    selected = map_tiers(certified)
    if not selected.get("default"):
        logger.error("No suitable models found for default route")
        return False

    best_model = _select_best_openrouter_model(certified)
    write_env_file(selected, best_model)
    print_selection_summary(selected)
    print_human_summary(selected, best_model)
    save_selection_cache(selected, "auto")
    return True


def run_refresh_mode(credentials):
    print("Refresh requested -- discovering candidates from free-coding-models")
    candidates = get_fcm_data_with_cache()
    if not candidates:
        return False
    print("  Discovered %d candidate(s)" % len(candidates))
    registry = load_registry()
    registry = run_probes(candidates, registry, credentials)
    save_registry(registry)
    certified = get_certified_models(registry)
    print("  Certified %d/%d models" % (len(certified), len(candidates)))
    if not certified:
        print("ERROR: No models passed certification.")
        print("Check API keys and provider availability.")
        return False

    selected = map_tiers(certified)
    best_model = _select_best_openrouter_model(certified)
    write_env_file(selected, best_model)
    print_selection_summary(selected)
    print_human_summary(selected, best_model)
    save_selection_cache(selected, "auto")
    return True


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
        help="Discover and certify candidate models, then write env config",
    )
    parser.add_argument(
        "--opencode", action="store_true", help="Write OpenCode config (not yet implemented)"
    )
    args = parser.parse_args()
    setup_logging(args.verbose, args.quiet)
    credentials = get_fcm_credentials()

    if args.refresh:
        success = run_refresh_mode(credentials)
    else:
        success = run_default_mode(credentials)

    if success:
        logger.info("Configuration complete")
    sys.exit(0 if success else 1)


# --- Inline assertions for classify_call_weight ---
assert classify_call_weight(1, False, 100) == "lightweight", "Short tool-free call should be lightweight"
assert classify_call_weight(5, True, 2000) == "heavy", "Multi-message tool call should be heavy"
assert classify_call_weight(2, False, 499) == "lightweight", "Edge case: max params for lightweight"
