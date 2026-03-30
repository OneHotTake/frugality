#!/usr/bin/env python3
"""
Comprehensive probe code validation without real API calls.
Tests all code paths, error conditions, and response handling.
"""
import json
import sys
import urllib.error
from unittest import mock

import frugality


def test_probe_successful_happy_path():
    """Validate successful certification path end-to-end."""
    print("TEST: Successful happy path (tool call → roundtrip → certified)")

    tool_call = {
        "id": "call_xyz",
        "function": {"name": "echo_number", "arguments": '{"value": 7}'}
    }

    responses = [
        # Step 1+2: tool call emission
        {
            "choices": [{
                "message": {
                    "tool_calls": [tool_call],
                    "content": None
                }
            }]
        },
        # Step 3: roundtrip response
        {
            "choices": [{
                "message": {
                    "content": "The square of 7 is 49, congratulations!",
                    "tool_calls": None
                }
            }]
        }
    ]

    with mock.patch("frugality._make_chat_request_with_retry", side_effect=responses):
        result = frugality.probe_model(
            "test_provider",
            "test_model_v1",
            {"apiKeys": {"test_provider": "test_key_123"}}
        )

    assert result["status"] == "certified", f"Expected certified, got {result['status']}"
    assert result["capabilities"]["tool_calling"] == True
    assert result["capabilities"]["tool_roundtrip"] == True
    assert result["capabilities"]["valid_json_args"] == True
    assert result["failure_reason"] is None
    print("  ✓ Returned: status=certified, all capabilities=True, no failure_reason\n")


def test_probe_no_credentials():
    """Validate skip when credentials missing."""
    print("TEST: No credentials available")

    with mock.patch("frugality._make_chat_request_with_retry") as mock_req:
        result = frugality.probe_model("test", "model", {})

    assert result["status"] == "skipped"
    assert result["failure_reason"] == "no_credentials"
    assert not mock_req.called, "Should not make HTTP call without credentials"
    print("  ✓ Returned: status=skipped, failure_reason=no_credentials\n")


def test_probe_auth_error_401():
    """Validate skip on 401 unauthorized."""
    print("TEST: HTTP 401 auth error")

    with mock.patch("frugality._make_chat_request_with_retry") as mock_req:
        mock_req.side_effect = urllib.error.HTTPError(
            "url", 401, "Unauthorized", {}, None
        )
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})

    assert result["status"] == "skipped"
    assert "auth_error:401" in result["failure_reason"]
    print("  ✓ Returned: status=skipped, failure_reason=auth_error:401\n")


def test_probe_auth_error_403():
    """Validate skip on 403 forbidden."""
    print("TEST: HTTP 403 forbidden")

    with mock.patch("frugality._make_chat_request_with_retry") as mock_req:
        mock_req.side_effect = urllib.error.HTTPError(
            "url", 403, "Forbidden", {}, None
        )
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})

    assert result["status"] == "skipped"
    assert "auth_error:403" in result["failure_reason"]
    print("  ✓ Returned: status=skipped, failure_reason=auth_error:403\n")


def test_probe_connectivity_error():
    """Validate skip on connectivity error."""
    print("TEST: Connectivity error (URLError)")

    with mock.patch("frugality._make_chat_request_with_retry") as mock_req:
        mock_req.side_effect = urllib.error.URLError("Connection refused")
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})

    assert result["status"] == "skipped"
    assert "connectivity:" in result["failure_reason"]
    print("  ✓ Returned: status=skipped, failure_reason=connectivity:...\n")


def test_probe_http_error_500():
    """Validate failure on 500 server error."""
    print("TEST: HTTP 500 server error (not auth, not transient)")

    with mock.patch("frugality._make_chat_request_with_retry") as mock_req:
        mock_req.side_effect = urllib.error.HTTPError(
            "url", 500, "Internal Error", {}, None
        )
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})

    assert result["status"] == "failed"
    assert "http_error:500" in result["failure_reason"]
    print("  ✓ Returned: status=failed, failure_reason=http_error:500\n")


def test_probe_no_tool_call():
    """Validate failure when model doesn't emit tool call."""
    print("TEST: Model refuses tool call (no tool_calls in response)")

    with mock.patch("frugality._make_chat_request_with_retry") as mock_req:
        mock_req.return_value = {
            "choices": [{
                "message": {
                    "content": "I can't call that function, I'm just a text model",
                    "tool_calls": None
                }
            }]
        }
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})

    assert result["status"] == "failed"
    assert result["failure_reason"] == "no_tool_call"
    assert result["capabilities"]["tool_calling"] == False
    print("  ✓ Returned: status=failed, failure_reason=no_tool_call\n")


def test_probe_wrong_tool_name():
    """Validate failure when model calls wrong tool."""
    print("TEST: Model calls wrong tool name")

    with mock.patch("frugality._make_chat_request_with_retry") as mock_req:
        mock_req.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {
                            "name": "some_other_function",
                            "arguments": '{"x": 1}'
                        }
                    }]
                }
            }]
        }
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})

    assert result["status"] == "failed"
    assert "wrong_tool_name:some_other_function" in result["failure_reason"]
    print("  ✓ Returned: status=failed, failure_reason=wrong_tool_name:...\n")


def test_probe_bad_argument_value():
    """Validate failure when argument value is wrong."""
    print("TEST: Model calls with wrong argument value")

    with mock.patch("frugality._make_chat_request_with_retry") as mock_req:
        mock_req.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {
                            "name": "echo_number",
                            "arguments": '{"value": 999}'  # Wrong value!
                        }
                    }]
                }
            }]
        }
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})

    assert result["status"] == "failed"
    assert "bad_args:value=999" in result["failure_reason"]
    print("  ✓ Returned: status=failed, failure_reason=bad_args:value=999\n")


def test_probe_malformed_json_args():
    """Validate failure when tool arguments are invalid JSON."""
    print("TEST: Model returns invalid JSON in tool arguments")

    with mock.patch("frugality._make_chat_request_with_retry") as mock_req:
        mock_req.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {
                            "name": "echo_number",
                            "arguments": '{broken json}'  # Invalid!
                        }
                    }]
                }
            }]
        }
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})

    assert result["status"] == "failed"
    assert "parse_error:" in result["failure_reason"]
    print("  ✓ Returned: status=failed, failure_reason=parse_error:...\n")


def test_probe_tool_loop():
    """Validate failure when model keeps emitting tool calls (infinite loop)."""
    print("TEST: Model loops on tool calls (emits tool call after roundtrip)")

    tool_call = {
        "id": "call_1",
        "function": {"name": "echo_number", "arguments": '{"value": 7}'}
    }

    with mock.patch("frugality._make_chat_request_with_retry") as mock_req:
        mock_req.side_effect = [
            # Step 1+2: tool call emission
            {"choices": [{"message": {"tool_calls": [tool_call]}}]},
            # Step 3: model loops (emits another tool call instead of text)
            {"choices": [{"message": {"tool_calls": [tool_call]}}]}
        ]
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})

    assert result["status"] == "failed"
    assert result["failure_reason"] == "tool_loop"
    print("  ✓ Returned: status=failed, failure_reason=tool_loop\n")


def test_probe_empty_final_response():
    """Validate failure when roundtrip produces empty response."""
    print("TEST: Model returns empty content after roundtrip")

    tool_call = {
        "id": "call_1",
        "function": {"name": "echo_number", "arguments": '{"value": 7}'}
    }

    with mock.patch("frugality._make_chat_request_with_retry") as mock_req:
        mock_req.side_effect = [
            # Step 1+2: tool call emission
            {"choices": [{"message": {"tool_calls": [tool_call]}}]},
            # Step 3: empty response
            {"choices": [{"message": {"content": None}}]}
        ]
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})

    assert result["status"] == "failed"
    assert result["failure_reason"] == "empty_final_response"
    print("  ✓ Returned: status=failed, failure_reason=empty_final_response\n")


def test_probe_ignores_roundtrip_result():
    """Validate failure when model doesn't reference tool result (ignores it)."""
    print("TEST: Model ignores tool result (no '49' in final response)")

    tool_call = {
        "id": "call_1",
        "function": {"name": "echo_number", "arguments": '{"value": 7}'}
    }

    with mock.patch("frugality._make_chat_request_with_retry") as mock_req:
        mock_req.side_effect = [
            # Step 1+2: tool call emission
            {"choices": [{"message": {"tool_calls": [tool_call]}}]},
            # Step 3: response that doesn't use the result
            {"choices": [{"message": {"content": "I got your tool call"}}]}  # Missing "49"!
        ]
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})

    assert result["status"] == "failed"
    assert result["failure_reason"] == "roundtrip_result_ignored"
    print("  ✓ Returned: status=failed, failure_reason=roundtrip_result_ignored\n")


def test_probe_metadata_merge():
    """Validate that discovered metadata gets merged into probe result."""
    print("TEST: Probe result preserves discovery metadata")

    tool_call = {
        "id": "call_1",
        "function": {"name": "echo_number", "arguments": '{"value": 7}'}
    }

    with mock.patch("frugality._make_chat_request_with_retry") as mock_req:
        mock_req.side_effect = [
            {"choices": [{"message": {"tool_calls": [tool_call]}}]},
            {"choices": [{"message": {"content": "The answer is 49"}}]}
        ]
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})

    # Check all required fields exist
    required_fields = [
        "status", "probe_version", "probe_profile", "provider", "model_id",
        "capabilities", "failure_reason", "last_verified_at"
    ]
    for field in required_fields:
        assert field in result, f"Missing required field: {field}"

    assert result["probe_version"] == frugality.PROBE_VERSION
    assert result["probe_profile"] == frugality.PROBE_PROFILE
    print("  ✓ Result has all required fields with correct versions\n")


def test_normalization_consistency():
    """Validate normalization helpers work correctly."""
    print("TEST: Normalization consistency")

    assert frugality.normalize_provider("NVIDIA") == "nvidia"
    assert frugality.normalize_provider("  Groq  ") == "groq"
    assert frugality.normalize_model_id("  llama-7b  ") == "llama-7b"

    key1 = frugality.registry_key("NVIDIA", "llama")
    key2 = frugality.registry_key("nvidia", "llama")
    assert key1 == key2 == "nvidia,llama"

    print("  ✓ Provider normalizes to lowercase with whitespace strip")
    print("  ✓ Model ID strips whitespace (preserves case)")
    print("  ✓ Registry keys are consistent\n")


def test_is_cert_stale():
    """Validate staleness detection."""
    print("TEST: Certification staleness detection")
    from datetime import datetime, timedelta

    # Fresh entry
    fresh = {
        "last_verified_at": datetime.now().isoformat(),
        "probe_version": frugality.PROBE_VERSION
    }
    assert not frugality.is_cert_stale(fresh), "Fresh entry should not be stale"

    # Old entry
    old = {
        "last_verified_at": (datetime.now() - timedelta(days=100)).isoformat(),
        "probe_version": frugality.PROBE_VERSION
    }
    assert frugality.is_cert_stale(old), "Old entry should be stale"

    # Outdated probe version
    outdated = {
        "last_verified_at": datetime.now().isoformat(),
        "probe_version": frugality.PROBE_VERSION - 1
    }
    assert frugality.is_cert_stale(outdated), "Outdated probe version should be stale"

    print("  ✓ Fresh entry (recent + current probe_version) = not stale")
    print("  ✓ Old entry (>7 days) = stale")
    print("  ✓ Outdated probe_version = stale\n")


def main():
    """Run all validation tests."""
    print("=" * 70)
    print("PROBE CODE VALIDATION (No Real API Calls)")
    print("=" * 70)
    print()

    tests = [
        test_probe_successful_happy_path,
        test_probe_no_credentials,
        test_probe_auth_error_401,
        test_probe_auth_error_403,
        test_probe_connectivity_error,
        test_probe_http_error_500,
        test_probe_no_tool_call,
        test_probe_wrong_tool_name,
        test_probe_bad_argument_value,
        test_probe_malformed_json_args,
        test_probe_tool_loop,
        test_probe_empty_final_response,
        test_probe_ignores_roundtrip_result,
        test_probe_metadata_merge,
        test_normalization_consistency,
        test_is_cert_stale,
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
