# Frugality Test Reference

## Quick Test Commands

```bash
# Run all unit tests (28 tests)
python3 -m unittest discover tests -v

# Run probe logic validation (16 tests, mocked)
python3 test_probe_validation.py

# Run probe orchestrator validation (8 tests, mocked)
python3 test_probe_orchestration.py

# Run all tests (52 total)
python3 -m unittest discover tests -v && \
python3 test_probe_validation.py && \
python3 test_probe_orchestration.py
```

## Test Files Overview

| File | Tests | Purpose | Scope |
|------|-------|---------|-------|
| `tests/test_frugality.py` | 28 | Unit tests (unittest framework) | Registry I/O, modes, normalization, stale detection |
| `test_probe_validation.py` | 16 | Probe logic (mocked HTTP) | All error paths, roundtrip behavior, edge cases |
| `test_probe_orchestration.py` | 8 | Orchestrator (mocked probes) | Filtering, concurrency, metadata, timestamps |

## What's Tested

### Registry & Normalization
- ✓ Load/save operations (missing file, corrupt JSON, schema mismatch)
- ✓ Provider normalization (lowercasing, whitespace)
- ✓ Model ID normalization (whitespace only)
- ✓ Registry key format consistency
- ✓ Certification staleness (age, probe_version)

### Mode Selection
- ✓ Default mode: uses certified models only
- ✓ Default mode failure: empty registry with guidance
- ✓ Refresh mode: discovers + probes + saves registry
- ✓ Refresh mode failure: no candidates

### Probe Logic (Tool Calling)
- ✓ Step 1+2: Valid tool call emission
- ✓ Step 3: Valid roundtrip with result consumption
- ✓ Tool call validation: name, arguments, JSON parsing
- ✓ Roundtrip validation: response has content, references result ("49")
- ✓ Error handling: skipped (no creds, auth, connectivity), failed (behavioral)

### Probe Orchestration
- ✓ Blocked model filtering (never reprobed)
- ✓ Fresh cert skipping (certification fresh = skip)
- ✓ Stale cert reprobing (age > 7 days = reprobe)
- ✓ Version-based reprobing (outdated probe_version = reprobe)
- ✓ Concurrent execution (ThreadPoolExecutor, 4 workers)
- ✓ Metadata merging (discovery → registry entry)
- ✓ Timestamp handling (last_verified_at, updated_at)

## Safety: No Real API Calls

All tests use `unittest.mock` to avoid:
- ✓ Real HTTP requests
- ✓ API key exposure
- ✓ Rate limiting
- ✓ CCR interruption
- ✓ Side effects

## Test Scenarios Covered

### Error Conditions (Skipped vs. Failed)
- No credentials → **skipped**
- HTTP 401/403 (auth) → **skipped**
- Connectivity failure → **skipped**
- HTTP 500 (server error) → **failed** (model issue)
- No tool call → **failed**
- Wrong tool name → **failed**
- Bad argument value → **failed**
- Invalid JSON args → **failed**
- Tool loop (post-roundtrip) → **failed**
- Empty final response → **failed**
- Ignored tool result → **failed**

### Edge Cases
- Malformed JSON in arguments
- Missing required fields in responses
- Models that refuse tool use
- Models that don't consume tool results
- Concurrent probing with mixed outcomes

## Running Tests During Development

```bash
# Quick smoke test
python3 test_probe_validation.py

# Full validation before commit
python3 -m unittest discover tests -v && \
python3 test_probe_validation.py && \
python3 test_probe_orchestration.py

# Watch for changes and rerun
while true; do clear; python3 test_probe_validation.py; inotifywait -e modify frugality.py; done
```

## Interpreting Results

✓ All tests pass → code is safe to use  
✗ Test failure → investigate failure_reason and fix code  
⚠ Timeout → increase PROBE_TIMEOUT if legitimate slow providers  

## Adding New Tests

1. For new probe logic: add to `tests/test_frugality.py` (unittest)
2. For edge cases: add to `test_probe_validation.py` (mocked)
3. For orchestration: add to `test_probe_orchestration.py` (mocked)

Mock template:
```python
with mock.patch("frugality.probe_model", return_value={...}):
    result = frugality.run_probes(...)
    assert result["..."] == "..."
```
