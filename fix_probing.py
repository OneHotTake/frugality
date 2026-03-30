#!/usr/bin/env python3
"""Script to apply probing rate limit fixes to frugality.py"""

import re
import sys

FILE = "/home/onehottake/Projects/frugality/frugality.py"

def apply_fixes():
    with open(FILE, "r") as f:
        content = f.read()

    # 1. Update constants
    content = re.sub(
        r"PROBE_VERSION = 1",
        "PROBE_VERSION = 2  # Incremented: forces recertification on next --refresh",
        content
    )
    content = re.sub(
        r"PROBE_WORKERS = 4",
        "PROBE_WORKERS = 2  # Reduced from 4 to reduce request rate",
        content
    )

    # Add new constant after PROBE_RETRY_DELAY
    if "PROBE_PROVIDER_DELAY" not in content:
        content = content.replace(
            "PROBE_RETRY_DELAY = 2.0",
            "PROBE_RETRY_DELAY = 2.0\nPROBE_PROVIDER_DELAY = 0.2  # 200ms delay between requests to same provider"
        )

    # 2. Add random import
    if "import random" not in content:
        content = content.replace(
            "import os\nimport subprocess",
            "import os\nimport random\nimport subprocess"
        )

    # 3. Update retry function
    new_retry = '''def _make_chat_request_with_retry(url: str, api_key: str, payload: dict) -> dict:
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
    raise last_exc'''

    old_retry_pattern = r'def _make_chat_request_with_retry\(url: str, api_key: str, payload: dict\) -> dict:.*?raise last_exc'
    content = re.sub(old_retry_pattern, new_retry, content, flags=re.DOTALL)

    # 4. Update run_probes function
    new_run_probes = '''def run_probes(candidates: list, registry: dict, credentials: dict) -> dict:
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

    return registry'''

    old_run_probes_pattern = r'def run_probes\(candidates: list, registry: dict, credentials: dict\) -> dict:.*?return registry'
    content = re.sub(old_run_probes_pattern, new_run_probes, content, flags=re.DOTALL)

    with open(FILE, "w") as f:
        f.write(content)

    print("Applied fixes to frugality.py")

if __name__ == "__main__":
    apply_fixes()
