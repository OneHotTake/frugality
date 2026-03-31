#!/usr/bin/env python3
"""
Unit tests for frugality.py certification gate.
"""
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

# We need to import the frugality module
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import frugality


class TestNormalization(unittest.TestCase):
    """Test normalization helper functions."""

    def test_normalize_provider_lowercases(self):
        self.assertEqual(frugality.normalize_provider("NVIDIA"), "nvidia")
        self.assertEqual(frugality.normalize_provider("Groq"), "groq")

    def test_normalize_provider_strips_whitespace(self):
        self.assertEqual(frugality.normalize_provider("  nvidia  "), "nvidia")

    def test_normalize_model_id_strips_whitespace(self):
        self.assertEqual(frugality.normalize_model_id("  model-id  "), "model-id")

    def test_registry_key_format(self):
        key = frugality.registry_key("NVIDIA", "  llama-7b  ")
        self.assertEqual(key, "nvidia,llama-7b")

    def test_registry_key_always_uses_normalization(self):
        key1 = frugality.registry_key("nvidia", "llama")
        key2 = frugality.registry_key("NVIDIA", "llama")
        self.assertEqual(key1, key2)


class TestRegistryHelpers(unittest.TestCase):
    """Test registry loading and saving."""

    def setUp(self):
        """Create temporary directory for test."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cert_registry = frugality.CERT_REGISTRY_FILE
        frugality.CERT_REGISTRY_FILE = os.path.join(self.temp_dir, "cert.json")

    def tearDown(self):
        """Clean up temporary directory."""
        frugality.CERT_REGISTRY_FILE = self.original_cert_registry
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_registry_missing_file(self):
        """Empty registry returned when file doesn't exist."""
        registry = frugality.load_registry()
        self.assertEqual(registry["schema_version"], frugality.CERT_SCHEMA_VERSION)
        self.assertEqual(registry["probe_version"], frugality.PROBE_VERSION)
        self.assertEqual(registry["models"], {})

    def test_load_registry_schema_mismatch(self):
        """Empty registry on schema version mismatch."""
        with open(frugality.CERT_REGISTRY_FILE, "w") as f:
            json.dump({"schema_version": 999, "models": {}}, f)
        registry = frugality.load_registry()
        self.assertEqual(registry["schema_version"], frugality.CERT_SCHEMA_VERSION)
        self.assertEqual(registry["models"], {})

    def test_load_registry_corrupt_json(self):
        """Empty registry on corrupt JSON."""
        with open(frugality.CERT_REGISTRY_FILE, "w") as f:
            f.write("{ invalid json }")
        registry = frugality.load_registry()
        self.assertEqual(registry["schema_version"], frugality.CERT_SCHEMA_VERSION)

    def test_save_registry_creates_file(self):
        """Registry is saved to file."""
        registry = frugality.load_registry()
        registry["models"]["test,model"] = {
            "status": "certified",
            "provider": "test",
            "model_id": "model",
        }
        frugality.save_registry(registry)
        self.assertTrue(os.path.exists(frugality.CERT_REGISTRY_FILE))

    def test_is_cert_stale_old_timestamp(self):
        """Entry is stale if timestamp is old."""
        entry = {
            "last_verified_at": (
                datetime.now() - timedelta(days=frugality.CERT_TTL_DAYS + 1)
            ).isoformat(),
            "probe_version": frugality.PROBE_VERSION,
        }
        self.assertTrue(frugality.is_cert_stale(entry))

    def test_is_cert_fresh_recent_timestamp(self):
        """Entry is fresh if timestamp is recent."""
        entry = {
            "last_verified_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "probe_version": frugality.PROBE_VERSION,
        }
        self.assertFalse(frugality.is_cert_stale(entry))

    def test_is_cert_stale_outdated_probe_version(self):
        """Entry is stale if probe_version is outdated."""
        entry = {
            "last_verified_at": datetime.now().isoformat(),
            "probe_version": frugality.PROBE_VERSION - 1,
        }
        self.assertTrue(frugality.is_cert_stale(entry))

    def test_get_certified_models_filters_status(self):
        """get_certified_models returns only 'certified' entries."""
        registry = {
            "models": {
                "a,b": {
                    "status": "certified",
                    "model_id": "b",
                    "provider": "a",
                    "tier": "S+",
                },
                "c,d": {
                    "status": "failed",
                    "model_id": "d",
                    "provider": "c",
                    "tier": "S+",
                },
                "e,f": {
                    "status": "blocked",
                    "model_id": "f",
                    "provider": "e",
                    "tier": "S+",
                },
            }
        }
        certified = frugality.get_certified_models(registry)
        self.assertEqual(len(certified), 1)
        self.assertEqual(certified[0]["modelId"], "b")

    def test_get_certified_models_has_required_fields(self):
        """Reconstructed certified models have required fields."""
        registry = {
            "models": {
                "provider,model": {
                    "status": "certified",
                    "model_id": "model",
                    "provider": "provider",
                    "tier": "S+",
                    "context": "100k",
                    "sweScore": "95",
                    "uptime": 99.9,
                    "label": "test-model",
                }
            }
        }
        certified = frugality.get_certified_models(registry)
        model = certified[0]
        self.assertIn("modelId", model)
        self.assertIn("provider", model)
        self.assertIn("tier", model)
        self.assertIn("context", model)
        self.assertEqual(model["modelId"], "model")


class TestDefaultMode(unittest.TestCase):
    """Test default mode behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cert_registry = frugality.CERT_REGISTRY_FILE
        frugality.CERT_REGISTRY_FILE = os.path.join(self.temp_dir, "cert.json")

    def tearDown(self):
        """Clean up."""
        frugality.CERT_REGISTRY_FILE = self.original_cert_registry
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @mock.patch("frugality.update_ccr_config")
    def test_default_mode_empty_registry(self, mock_update):
        """Default mode returns False with guidance when registry is empty."""
        result = frugality.run_default_mode({})
        self.assertFalse(result)
        mock_update.assert_not_called()

    @mock.patch("frugality.update_ccr_config")
    def test_default_mode_calls_update_with_certified(self, mock_update):
        """Default mode calls update_ccr_config with certified models."""
        registry = {
            "schema_version": frugality.CERT_SCHEMA_VERSION,
            "probe_version": frugality.PROBE_VERSION,
            "updated_at": datetime.now().isoformat(),
            "models": {
                "test,model": {
                    "status": "certified",
                    "model_id": "model",
                    "provider": "test",
                    "tier": "S+",
                    "context": "100k",
                    "sweScore": "95",
                    "uptime": 100,
                    "label": "test-model",
                }
            },
        }
        with open(frugality.CERT_REGISTRY_FILE, "w") as f:
            json.dump(registry, f)

        mock_update.return_value = True
        result = frugality.run_default_mode({})
        self.assertTrue(result)
        mock_update.assert_called_once()
        # Verify certified model was passed
        args = mock_update.call_args[0]
        self.assertEqual(len(args[0]), 1)
        self.assertEqual(args[0][0]["modelId"], "model")


class TestRefreshMode(unittest.TestCase):
    """Test refresh mode behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cert_registry = frugality.CERT_REGISTRY_FILE
        frugality.CERT_REGISTRY_FILE = os.path.join(self.temp_dir, "cert.json")

    def tearDown(self):
        """Clean up."""
        frugality.CERT_REGISTRY_FILE = self.original_cert_registry
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @mock.patch("frugality.run_probes")
    @mock.patch("frugality.get_fcm_data_with_cache")
    @mock.patch("frugality.update_ccr_config")
    def test_refresh_discovers_and_probes(
        self, mock_update, mock_fcm, mock_probes
    ):
        """Refresh mode discovers, probes, and updates config."""
        candidates = [
            {"modelId": "model1", "provider": "test", "tier": "S+", "context": "100k"}
        ]
        mock_fcm.return_value = candidates
        mock_probes.return_value = {
            "schema_version": frugality.CERT_SCHEMA_VERSION,
            "probe_version": frugality.PROBE_VERSION,
            "updated_at": datetime.now().isoformat(),
            "models": {
                "test,model1": {
                    "status": "certified",
                    "model_id": "model1",
                    "provider": "test",
                    "tier": "S+",
                    "context": "100k",
                    "sweScore": "95",
                    "uptime": 100,
                    "label": "model1",
                }
            },
        }
        mock_update.return_value = True

        result = frugality.run_refresh_mode({})
        self.assertTrue(result)
        mock_fcm.assert_called_once()
        mock_probes.assert_called_once()
        mock_update.assert_called_once()

    @mock.patch("frugality.get_fcm_data_with_cache")
    def test_refresh_returns_false_no_candidates(self, mock_fcm):
        """Refresh returns False if FCM discovery fails."""
        mock_fcm.return_value = None
        result = frugality.run_refresh_mode({})
        self.assertFalse(result)


class TestProbeModel(unittest.TestCase):
    """Test model probing logic."""

    @mock.patch("frugality._make_chat_request_with_retry")
    def test_probe_successful_certification(self, mock_request):
        """Probe returns 'certified' on successful tool roundtrip."""
        # Step 1+2: tool call response
        tool_call = {
            "id": "call_123",
            "function": {"name": "echo_number", "arguments": '{"value": 7}'},
        }
        mock_request.side_effect = [
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [tool_call],
                            "content": None,
                        }
                    }
                ]
            },
            # Step 3: roundtrip response
            {
                "choices": [
                    {
                        "message": {
                            "content": "The answer is 49",
                            "tool_calls": None,
                        }
                    }
                ]
            },
        ]

        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})
        self.assertEqual(result["status"], "certified")
        self.assertTrue(result["capabilities"]["tool_calling"])
        self.assertTrue(result["capabilities"]["tool_roundtrip"])

    @mock.patch("frugality._make_chat_request_with_retry")
    def test_probe_no_credentials(self, mock_request):
        """Probe skips if no credentials available."""
        result = frugality.probe_model("test", "model", {})
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["failure_reason"], "unconfigured_provider")
        mock_request.assert_not_called()

    @mock.patch("frugality._make_chat_request_with_retry")
    def test_probe_auth_error_skipped(self, mock_request):
        """Probe skips on 401/403 auth errors."""
        mock_request.side_effect = frugality.urllib.error.HTTPError(
            "url", 401, "Unauthorized", {}, None
        )
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})
        self.assertEqual(result["status"], "skipped")
        self.assertIn("auth_error", result["failure_reason"])

    @mock.patch("frugality._make_chat_request_with_retry")
    def test_probe_connectivity_error_skipped(self, mock_request):
        """Probe skips on connectivity errors."""
        mock_request.side_effect = frugality.urllib.error.URLError("Connection failed")
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})
        self.assertEqual(result["status"], "skipped")
        self.assertIn("connectivity", result["failure_reason"])

    @mock.patch("frugality._make_chat_request_with_retry")
    def test_probe_no_tool_call(self, mock_request):
        """Probe fails if model doesn't emit tool call."""
        mock_request.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "I can't call that function",
                        "tool_calls": None,
                    }
                }
            ]
        }
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_reason"], "no_tool_call")

    @mock.patch("frugality._make_chat_request_with_retry")
    def test_probe_wrong_tool_name(self, mock_request):
        """Probe fails if model calls wrong tool."""
        mock_request.return_value = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "other_tool",
                                    "arguments": '{"value": 7}',
                                }
                            }
                        ]
                    }
                }
            ]
        }
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})
        self.assertEqual(result["status"], "failed")
        self.assertIn("wrong_tool_name", result["failure_reason"])

    @mock.patch("frugality._make_chat_request_with_retry")
    def test_probe_bad_argument_value(self, mock_request):
        """Probe fails if argument value is wrong."""
        mock_request.return_value = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "echo_number",
                                    "arguments": '{"value": 999}',
                                }
                            }
                        ]
                    }
                }
            ]
        }
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})
        self.assertEqual(result["status"], "failed")
        self.assertIn("bad_args", result["failure_reason"])

    @mock.patch("frugality._make_chat_request_with_retry")
    def test_probe_tool_loop(self, mock_request):
        """Probe fails if model keeps looping on tool calls."""
        tool_call = {
            "id": "call_123",
            "function": {"name": "echo_number", "arguments": '{"value": 7}'},
        }
        mock_request.side_effect = [
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [tool_call],
                            "content": None,
                        }
                    }
                ]
            },
            # Roundtrip: model makes another tool call (loop)
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [tool_call],
                            "content": None,
                        }
                    }
                ]
            },
        ]
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_reason"], "tool_loop")

    @mock.patch("frugality._make_chat_request_with_retry")
    def test_probe_ignores_roundtrip_result(self, mock_request):
        """Probe fails if model doesn't use tool result."""
        tool_call = {
            "id": "call_123",
            "function": {"name": "echo_number", "arguments": '{"value": 7}'},
        }
        mock_request.side_effect = [
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [tool_call],
                            "content": None,
                        }
                    }
                ]
            },
            # Roundtrip: model ignores result (no "49" in response)
            {
                "choices": [
                    {
                        "message": {
                            "content": "I received the result",
                            "tool_calls": None,
                        }
                    }
                ]
            },
        ]
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_reason"], "roundtrip_result_ignored")

    @mock.patch("frugality._make_chat_request_with_retry")
    def test_probe_empty_final_response(self, mock_request):
        """Probe fails if final response is empty."""
        tool_call = {
            "id": "call_123",
            "function": {"name": "echo_number", "arguments": '{"value": 7}'},
        }
        mock_request.side_effect = [
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [tool_call],
                            "content": None,
                        }
                    }
                ]
            },
            # Roundtrip: empty response
            {"choices": [{"message": {"content": None, "tool_calls": None}}]},
        ]
        result = frugality.probe_model("test", "model", {"apiKeys": {"test": "key"}})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_reason"], "empty_final_response")


if __name__ == "__main__":
    unittest.main()
