#!/usr/bin/env python3
import argparse
import json
import logging
import os
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

CERT_SCHEMA_VERSION = 1
PROBE_VERSION = 1
PROBE_PROFILE = "tool_chat"
CERT_TTL_DAYS = 7
PROBE_TIMEOUT = 15
PROBE_WORKERS = 4
PROBE_MAX_RETRIES = 2
PROBE_RETRY_DELAY = 2.0

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
    """Retry on transient 429/5xx up to PROBE_MAX_RETRIES times."""
    last_exc = None
    for attempt in range(PROBE_MAX_RETRIES + 1):
        try:
            return _make_chat_request(url, api_key, payload)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < PROBE_MAX_RETRIES:
                time.sleep(PROBE_RETRY_DELAY * (attempt + 1))
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


def _parse_context_tokens(context_str: str) -> int:
    try:
        return int(context_str.replace("k", "000").replace("M", "000000") or "0")
    except Exception:
        return 0


def run_probes(candidates: list, registry: dict, credentials: dict) -> dict:
    """
    Determine which candidates need probing, run concurrently,
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
            continue  # never re-probe blocked models
        if existing.get("status") == "certified" and not is_cert_stale(existing):
            continue  # fresh cert, skip
        to_probe.append(m)

    if not to_probe:
        print("  All candidates have fresh certifications — nothing to probe.")
        return registry

    print(f"  Probing {len(to_probe)} candidate(s) (workers={PROBE_WORKERS})...")

    futures = {}
    with ThreadPoolExecutor(max_workers=PROBE_WORKERS) as pool:
        for m in to_probe:
            provider = m.get("provider", "")
            model_id = m.get("modelId", "")
            f = pool.submit(probe_model, provider, model_id, credentials)
            futures[f] = m

        for f in as_completed(futures):
            m = futures[f]
            provider = normalize_provider(m.get("provider", ""))
            model_id = normalize_model_id(m.get("modelId", ""))
            key = registry_key(provider, model_id)
            result = f.result()
            # Merge discovery metadata into result
            result["tier"] = m.get("tier", "")
            result["context"] = m.get("context", "0")
            result["context_tokens"] = _parse_context_tokens(m.get("context", "0"))
            result["sweScore"] = m.get("sweScore", "")
            result["uptime"] = m.get("uptime", 100)
            result["label"] = m.get("label", model_id)
            registry["models"][key] = result

            status_str = {
                "certified": "OK",
                "skipped": f"SKIPPED ({result.get('failure_reason', '?')})",
            }.get(result["status"], f"FAIL ({result.get('failure_reason', '?')})")
            print(f"  {provider}/{model_id}: {status_str}")

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


def update_ccr_config(models: list, credentials: dict) -> bool:
    logger.info("Configuring Claude Code Router")
    selected = map_tiers(models)
    if not selected["default"]:
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
    args = parser.parse_args()
    setup_logging(args.verbose, args.quiet)
    credentials = get_fcm_credentials()
    success = run_refresh_mode(credentials) if args.refresh else run_default_mode(credentials)
    if success:
        logger.info("Configuration complete")
    sys.exit(0 if success else 1)
