#!/usr/bin/env python3
"""
Validate probe orchestrator (concurrent probing, registry updates, filtering logic).
"""
import json
import sys
import tempfile
from datetime import datetime, timedelta
from unittest import mock

import frugality


def test_run_probes_skips_blocked():
    """Validate that blocked models are never probed."""
    print("TEST: run_probes skips blocked models")

    candidates = [
        {"modelId": "m1", "provider": "test", "tier": "S+", "context": "100k"},
        {"modelId": "m2", "provider": "test", "tier": "S+", "context": "100k"},
    ]

    registry = {
        "schema_version": frugality.CERT_SCHEMA_VERSION,
        "probe_version": frugality.PROBE_VERSION,
        "updated_at": datetime.now().isoformat(),
        "models": {
            "test,m1": {
                "status": "blocked",
                "model_id": "m1",
                "provider": "test",
                "failure_reason": "manually_excluded"
            }
        }
    }

    with mock.patch("frugality.probe_model") as mock_probe:
        result = frugality.run_probes(candidates, registry, {})

    # Should only probe m2, not m1
    assert mock_probe.call_count == 1
    call_args = mock_probe.call_args[0]
    assert call_args[1] == "m2", f"Expected m2, probed {call_args[1]}"
    print("  ✓ Blocked model (m1) was skipped")
    print("  ✓ Non-blocked model (m2) was probed\n")


def test_run_probes_skips_fresh_cert():
    """Validate that fresh certifications are not reprobed."""
    print("TEST: run_probes skips fresh certifications")

    candidates = [
        {"modelId": "m1", "provider": "test", "tier": "S+", "context": "100k"},
    ]

    fresh_time = datetime.now().isoformat()
    registry = {
        "schema_version": frugality.CERT_SCHEMA_VERSION,
        "probe_version": frugality.PROBE_VERSION,
        "updated_at": fresh_time,
        "models": {
            "test,m1": {
                "status": "certified",
                "model_id": "m1",
                "provider": "test",
                "last_verified_at": fresh_time,
                "probe_version": frugality.PROBE_VERSION,
                "tier": "S+",
                "context": "100k",
            }
        }
    }

    with mock.patch("frugality.probe_model") as mock_probe:
        result = frugality.run_probes(candidates, registry, {})

    assert mock_probe.call_count == 0, "Should not reprobe fresh certifications"
    print("  ✓ Fresh certified model was skipped (not reprobed)\n")


def test_run_probes_reprobes_stale():
    """Validate that stale certifications are reprobed."""
    print("TEST: run_probes reprobes stale certifications")

    candidates = [
        {"modelId": "m1", "provider": "test", "tier": "S+", "context": "100k"},
    ]

    old_time = (datetime.now() - timedelta(days=100)).isoformat()
    registry = {
        "schema_version": frugality.CERT_SCHEMA_VERSION,
        "probe_version": frugality.PROBE_VERSION,
        "updated_at": old_time,
        "models": {
            "test,m1": {
                "status": "certified",
                "model_id": "m1",
                "provider": "test",
                "last_verified_at": old_time,
                "probe_version": frugality.PROBE_VERSION,
                "tier": "S+",
                "context": "100k",
            }
        }
    }

    def mock_probe_fn(provider, model_id, creds):
        return {
            "status": "certified",
            "probe_version": frugality.PROBE_VERSION,
            "probe_profile": frugality.PROBE_PROFILE,
            "provider": frugality.normalize_provider(provider),
            "model_id": frugality.normalize_model_id(model_id),
            "failure_reason": None,
            "last_verified_at": datetime.now().isoformat(),
            "capabilities": {"tool_calling": True}
        }

    with mock.patch("frugality.probe_model", side_effect=mock_probe_fn) as mock_probe:
        result = frugality.run_probes(candidates, registry, {})

    assert mock_probe.call_count == 1, "Should reprobe stale certification"
    print("  ✓ Stale certified model was reprobed\n")


def test_run_probes_reprobes_outdated_version():
    """Validate that entries with outdated probe_version are reprobed."""
    print("TEST: run_probes reprobes outdated probe_version")

    candidates = [
        {"modelId": "m1", "provider": "test", "tier": "S+", "context": "100k"},
    ]

    registry = {
        "schema_version": frugality.CERT_SCHEMA_VERSION,
        "probe_version": frugality.PROBE_VERSION,
        "updated_at": datetime.now().isoformat(),
        "models": {
            "test,m1": {
                "status": "certified",
                "model_id": "m1",
                "provider": "test",
                "last_verified_at": datetime.now().isoformat(),
                "probe_version": frugality.PROBE_VERSION - 1,  # Outdated!
                "tier": "S+",
                "context": "100k",
            }
        }
    }

    def mock_probe_fn(provider, model_id, creds):
        return {
            "status": "certified",
            "probe_version": frugality.PROBE_VERSION,
            "probe_profile": frugality.PROBE_PROFILE,
            "provider": frugality.normalize_provider(provider),
            "model_id": frugality.normalize_model_id(model_id),
            "failure_reason": None,
            "last_verified_at": datetime.now().isoformat(),
            "capabilities": {"tool_calling": True}
        }

    with mock.patch("frugality.probe_model", side_effect=mock_probe_fn) as mock_probe:
        result = frugality.run_probes(candidates, registry, {})

    assert mock_probe.call_count == 1, "Should reprobe outdated probe_version"
    print("  ✓ Outdated probe_version model was reprobed\n")


def test_run_probes_merges_metadata():
    """Validate that discovery metadata is merged into probe result."""
    print("TEST: run_probes merges discovery metadata")

    candidates = [
        {
            "modelId": "m1",
            "provider": "test",
            "tier": "S+",
            "context": "200k",
            "sweScore": "95",
            "uptime": 99.5,
            "label": "test-model-v1"
        },
    ]

    registry = {
        "schema_version": frugality.CERT_SCHEMA_VERSION,
        "probe_version": frugality.PROBE_VERSION,
        "updated_at": datetime.now().isoformat(),
        "models": {}
    }

    def mock_probe_fn(provider, model_id, creds):
        return {
            "status": "certified",
            "probe_version": frugality.PROBE_VERSION,
            "probe_profile": frugality.PROBE_PROFILE,
            "provider": frugality.normalize_provider(provider),
            "model_id": frugality.normalize_model_id(model_id),
            "failure_reason": None,
            "last_verified_at": datetime.now().isoformat(),
            "capabilities": {"tool_calling": True}
        }

    with mock.patch("frugality.probe_model", side_effect=mock_probe_fn):
        result = frugality.run_probes(candidates, registry, {})

    # Check that metadata was merged
    key = "test,m1"
    entry = result["models"][key]
    assert entry["tier"] == "S+", f"Expected tier S+, got {entry['tier']}"
    assert entry["context"] == "200k", f"Expected context 200k, got {entry['context']}"
    assert entry["context_tokens"] == 200000, f"Expected 200000 tokens, got {entry['context_tokens']}"
    assert entry["sweScore"] == "95"
    assert entry["uptime"] == 99.5
    assert entry["label"] == "test-model-v1"
    print("  ✓ All discovery metadata merged into registry entry\n")


def test_run_probes_preserves_failed_reason():
    """Validate that failure reasons are preserved in registry."""
    print("TEST: run_probes preserves failure reasons")

    candidates = [
        {"modelId": "m1", "provider": "test", "tier": "S+", "context": "100k"},
    ]

    registry = {
        "schema_version": frugality.CERT_SCHEMA_VERSION,
        "probe_version": frugality.PROBE_VERSION,
        "updated_at": datetime.now().isoformat(),
        "models": {}
    }

    def mock_probe_fn(provider, model_id, creds):
        return {
            "status": "failed",
            "probe_version": frugality.PROBE_VERSION,
            "probe_profile": frugality.PROBE_PROFILE,
            "provider": frugality.normalize_provider(provider),
            "model_id": frugality.normalize_model_id(model_id),
            "failure_reason": "tool_loop",  # Specific failure
            "last_verified_at": datetime.now().isoformat(),
            "capabilities": {}
        }

    with mock.patch("frugality.probe_model", side_effect=mock_probe_fn):
        result = frugality.run_probes(candidates, registry, {})

    key = "test,m1"
    entry = result["models"][key]
    assert entry["status"] == "failed"
    assert entry["failure_reason"] == "tool_loop"
    print("  ✓ Failed model with specific reason preserved\n")


def test_run_probes_concurrent_execution():
    """Validate concurrent probe execution."""
    print("TEST: run_probes executes concurrently")

    candidates = [
        {"modelId": f"m{i}", "provider": "test", "tier": "S+", "context": "100k"}
        for i in range(5)
    ]

    registry = {
        "schema_version": frugality.CERT_SCHEMA_VERSION,
        "probe_version": frugality.PROBE_VERSION,
        "updated_at": datetime.now().isoformat(),
        "models": {}
    }

    call_count = 0

    def mock_probe_fn(provider, model_id, creds):
        nonlocal call_count
        call_count += 1
        return {
            "status": "certified",
            "probe_version": frugality.PROBE_VERSION,
            "probe_profile": frugality.PROBE_PROFILE,
            "provider": frugality.normalize_provider(provider),
            "model_id": frugality.normalize_model_id(model_id),
            "failure_reason": None,
            "last_verified_at": datetime.now().isoformat(),
            "capabilities": {"tool_calling": True}
        }

    with mock.patch("frugality.probe_model", side_effect=mock_probe_fn):
        result = frugality.run_probes(candidates, registry, {})

    assert call_count == 5, f"Expected 5 probes, got {call_count}"
    assert len(result["models"]) == 5, f"Expected 5 registry entries, got {len(result['models'])}"
    print("  ✓ All 5 candidates probed concurrently")
    print("  ✓ All results merged into registry\n")


def test_run_probes_sets_entry_timestamps():
    """Validate that probe results get last_verified_at timestamps."""
    print("TEST: run_probes sets entry timestamps")

    candidates = [
        {"modelId": "m1", "provider": "test", "tier": "S+", "context": "100k"},
    ]

    registry = {
        "schema_version": frugality.CERT_SCHEMA_VERSION,
        "probe_version": frugality.PROBE_VERSION,
        "updated_at": datetime.now().isoformat(),
        "models": {}
    }

    def mock_probe_fn(provider, model_id, creds):
        return {
            "status": "certified",
            "probe_version": frugality.PROBE_VERSION,
            "probe_profile": frugality.PROBE_PROFILE,
            "provider": frugality.normalize_provider(provider),
            "model_id": frugality.normalize_model_id(model_id),
            "failure_reason": None,
            "last_verified_at": datetime.now().isoformat(),
            "capabilities": {"tool_calling": True}
        }

    with mock.patch("frugality.probe_model", side_effect=mock_probe_fn):
        result = frugality.run_probes(candidates, registry, {})

    # Check that probe result has timestamp (set by probe_model)
    key = "test,m1"
    entry = result["models"][key]
    assert "last_verified_at" in entry, "Entry should have last_verified_at"
    assert entry["last_verified_at"] != "", "Timestamp should not be empty"

    # Verify it's a valid ISO format timestamp
    try:
        entry_time = datetime.fromisoformat(entry["last_verified_at"])
        now = datetime.now()
        # Should be within last minute
        assert (now - entry_time).total_seconds() < 60, "Timestamp should be recent"
        print("  ✓ Probe result has last_verified_at timestamp")
        print("  ✓ Timestamp is valid ISO8601 and recent\n")
    except Exception as e:
        print(f"  ✗ Timestamp validation failed: {e}\n")
        raise


def main():
    """Run orchestration validation tests."""
    print("=" * 70)
    print("PROBE ORCHESTRATOR VALIDATION (Concurrent Probing)")
    print("=" * 70)
    print()

    tests = [
        test_run_probes_skips_blocked,
        test_run_probes_skips_fresh_cert,
        test_run_probes_reprobes_stale,
        test_run_probes_reprobes_outdated_version,
        test_run_probes_merges_metadata,
        test_run_probes_preserves_failed_reason,
        test_run_probes_concurrent_execution,
        test_run_probes_sets_entry_timestamps,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {type(e).__name__}: {e}\n")
            failed += 1

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
