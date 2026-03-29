#!/bin/bash

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "FRUGALITY STRESS TEST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PASS=0
FAIL=0
START=$(date +%s)

test_case() {
  local name="$1"
  local cmd="$2"
  printf "TEST %d: %s\n" $((PASS + FAIL + 1)) "$name"
  
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  ✓ PASS"
    ((PASS++))
    return 0
  else
    echo "  ✗ FAIL: $cmd"
    ((FAIL++))
    return 1
  fi
}

# Run all tests
test_case "free-coding-models installed" "which free-coding-models" || true
test_case "ccr installed" "which ccr" || true
test_case "jq installed" "which jq" || true
test_case "curl installed" "which curl" || true
test_case "FCM config exists" "test -f ~/.free-coding-models.json" || true
test_case "FCM config valid JSON" "jq . ~/.free-coding-models.json" || true
test_case "best-model.js syntax" "node --check packages/core/src/best-model.js" || true
test_case "bridge.js syntax" "node --check packages/core/src/bridge.js" || true
test_case "safe-restart.js syntax" "node --check packages/core/src/safe-restart.js" || true
test_case "idle-watcher.js syntax" "node --check packages/core/src/idle-watcher.js" || true
test_case "watchdog.js syntax" "node --check packages/watchdog/src/watchdog.js" || true
test_case "frug.js syntax" "node --check bin/frug.js" || true
test_case "frug --help works" "node bin/frug.js --help" || true
test_case "frug --version works" "node bin/frug.js --version" || true
test_case "presets valid JSON" "jq . presets/free-tier-max/manifest.json" || true

END=$(date +%s)
ELAPSED=$((END - START))

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "RESULTS: $PASS/$((PASS + FAIL)) passed in ${ELAPSED}s"
if [ $FAIL -gt 0 ]; then
  echo "⚠ FAILED: $FAIL tests"
  exit 1
else
  echo "✓ ALL $PASS TESTS PASSED"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
