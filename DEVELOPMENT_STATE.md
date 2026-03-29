# Frugality Development State — Agent Handoff

## Architecture Overview

**System design:** Frugality orchestrates free-tier AI models (NVIDIA NIM, Groq, Cerebras, etc.) as delegated agents within Claude Code or OpenCode hybrid modes.

**Data flow:**
1. `frug-claude` → init + start --hybrid → launch Claude Code
2. Claude Code main session (subscription, e.g. Haiku 4.5) delegates tasks via SKILL.md rules
3. Sub-agents spawn via claudish, read `~/.frugality/cache/best-model-{taskType}.txt`
4. Sub-agents use cached free-tier model (fast/analysis/reasoning tier)
5. Watchdog daemon pings selected models every 5min, restarts if degraded
6. Idle-watcher daemon applies pending config changes when system idle (≤10sec inactivity)

**Key abstractions:**
- **Model discovery:** `queryFreeModels()` → `free-coding-models --tier S --json` → JSON parse → array of models
- **Model caching:** Atomic write (temp file + rename) to `~/.frugality/cache/best-model-{taskType}.txt`
- **Safe restart:** Idle detection via `ss -tan` + request-in-flight check before applying config
- **Preset manifest:** CCR-compatible JSON with Router slots + Providers array (provider auth via env var interpolation)
- **Daemon lifecycle:** PID files (`watchdog.pid`, `idle-watcher.pid`) + process existence checks

**Execution modes:**
- `proxy` (default): CCR health monitoring only
- `--hybrid`: Subscription main + free-tier agents (Claude Code)
- `--agentic`: Free-tier only
- `--opencode`: OpenCode + free agents
- `--opencode --hybrid`: OpenCode hybrid

## The 'Vibe' & Design Philosophy

**Error handling pattern:**
- `console.error()` for diagnostic output (non-fatal)
- `process.exit(1)` for fatal errors (missing deps, unrecoverable state)
- Graceful fallbacks: if model query fails, return claude-3-haiku; if CCR unresponsive, retry up to 3x
- Fail-open for agent spawning: if frugality init fails, still try to launch claude/opencode

**Naming conventions:**
- Files: kebab-case (`best-model.js`, `safe-restart.js`)
- Functions: camelCase, verb-first (`queryFreeModels`, `writeCache`, `isIdle`)
- Constants: UPPER_SNAKE_CASE in defaults.js (single source of truth)
- State files: CAPS.md for state/docs (CURRENT_TASK.md, HYBRID.md), .json for structured data

**Module design:**
- Export objects with methods, not classes (no `new`)
- Dual-mode support in `bin/frug.js`: `require.main === module` check allows both CLI and require() usage
- Convenience wrappers (`frug-claude.js`) call `frug.run()` module function, not spawn subprocess

**Async patterns:**
- Top-level async in convenience wrappers, run() function
- Promise.catch() wraps async errors in wrappers for graceful fallback
- Daemon lifecycle: setInterval for polling, graceful stop via SIGTERM handling (future)

**UI/UX principles:**
- Status output: checkmark (✓) for success, X (✗) for failure, emoji for warnings (⚠)
- Commands must be non-destructive by default (frug status reads only, frug update stages before applying)
- Error messages include actionable next steps (e.g. "Missing: free-coding-models" → see frug doctor)
- README emphasizes `frug-claude` first, other modes secondary

**Persistence patterns:**
- Atomic writes: write to `.tmp`, then `rename()` to target (prevents corruption on interrupt)
- Flag files not log files for decisions: `pending-restart`, `pending-config` (simple, queryable)
- Size-based log rotation (5MB), not time-based

## Current Progress

**✅ Fully functional:**
- Project structure & package.json (bin entries, zero deps)
- Convenience wrappers (frug-claude, frug-opencode) with init + start
- Main CLI: help, status, init, start, stop, update, doctor, version
- Model discovery via `free-coding-models --tier S --json` CLI
- Model caching with TTL (30min default)
- Task-based model selection (fast→A+ tier, analysis→gemini preference, reasoning→S+)
- Safe restart: idle detection (connection counting via `ss -tan`), request-in-flight check
- Daemon lifecycle: watchdog + idle-watcher with PID file management
- Skill installation to `.claude/skills/frugality-usage/SKILL.md`
- GitHub setup (install.sh, README pointing to repo, package.json)
- Unit tests: best-model (10), safe-restart (6), idle-watcher (4), watchdog (6) = 26 passing

**🔧 Partially implemented:**
- Cache format validation: files should be single model ID per file, but recent tests show concatenation issues (root cause: free-coding-models output format or property name mismatch)
- Test suite: 57/142 passing; 85 failures in error handling / edge case scenarios (opencode.test.js, failures.test.js too strict)
- CCR preset manifest generation: bridge.js complete but untested against live CCR process
- Model property detection: added fallback to `selected.id` if `modelId` undefined, but untested with actual free-coding-models output
- Agent spawning in Claude Code: SKILL.md installed as delegation guide, but no custom agents auto-created (users must follow claudish pattern in SKILL.md)

**❌ Broken / not started:**
- Cache files currently malformed (concatenated model IDs instead of single ID per file) — pending free-coding-models CLI verification
- End-to-end integration: never tested full flow with real free-coding-models returning models + sub-agent spawning
- OpenCode agent routing: design exists but no live validation
- Preset persistence workflow: presets/ directory exists with examples but untested
- SKILL.md sub-agent failure logging to .ai/FAILURES.ndjson (defined in SKILL.md but no automation)

## Active Task Context

**Current blocker:** Cache files are malformed — all model IDs concatenated into single file instead of separate files per task type.

**Symptom:**
```bash
$ cat ~/.frugality/cache/best-model-*.txt
google/gemini-3-proqwen/qwen3-next-80b-a3b-thinking...
# (all models concatenated, no newlines/separators)
```

**Root cause analysis:**
1. `queryFreeModels()` may not be parsing `free-coding-models --tier S --json` output correctly
2. OR `selected.modelId` is undefined, causing fallback logic to serialize entire object
3. OR free-coding-models CLI not installed/configured (fallback to claude-3-haiku in all caches)

**Recent fixes applied (commit ed86abe):**
- frug-claude and frug-opencode now call `frug init` before `frug start` (ensures .claude setup)
- best-model.js: improved property detection with fallback (`modelId || id || stringify(selected).substring(0,50)`)
- Cleared ~/.frugality/cache/ files for fresh run

**Next concrete action (must be done by user or next agent):**
1. Verify free-coding-models installation: `which free-coding-models && free-coding-models --tier S --json`
2. If empty output or error → user must install free-coding-models + configure ~/.free-coding-models.json with API keys
3. If models return → restart `frug-claude`, verify cache format: `cat ~/.frugality/cache/best-model-fast.txt | head -1` (should be single model ID)
4. Once cache is correct → test agent spawning: create task file, run claudish command from SKILL.md
5. Verify agent uses free-tier model (not Haiku 4.5)

**What blocks release:**
- Cache working correctly (must fix before any public demo)
- Agent spawning validated (manual test of SKILL.md delegation pattern)
- Test suite at >80% passing (currently 57/142, mostly edge cases)
- End-to-end flow verified (discovery → caching → restart → agent spawn → free-tier model used)

## Environment & Dependencies

**Required binaries (frug doctor checks these):**
- `free-coding-models` ([install](https://github.com/anthropics/free-coding-models))
- `ccr` (Claude Code Router)
- `jq` (JSON processor, usually pre-installed)
- `curl` (HTTP client, usually pre-installed)
- `node` >= 18 (required in package.json)

**Required config files:**
- `~/.free-coding-models.json`: FCM config with API keys per provider
  ```json
  {
    "apiKeys": {
      "nvidia": "key_here",
      "groq": "key_here",
      "cerebras": "key_here"
    }
  }
  ```
- `~/.claude-code-router/config.json`: CCR setup (created by CCR installer)
- `~/.claude/skills/frugality-usage/SKILL.md`: Installed by `frug init`

**Required env vars:**
- `HOME` (defaults to `/home/user`, used for all state paths)
- Provider API keys embedded in ~/.free-coding-models.json (not env vars, but FCM reads from there)

**Non-standard dependencies:**
- **None.** Zero npm dependencies. Uses only Node.js stdlib (fs, path, child_process, execSync).

**Setup steps NOT in README (must be done before frug works):**
1. Install free-coding-models: `git clone https://github.com/anthropics/free-coding-models && npm install -g ./free-coding-models`
2. Configure ~/.free-coding-models.json with actual API keys for NVIDIA, Groq, Cerebras, etc.
3. Install/configure CCR (Claude Code Router)
4. Run `bash install.sh` in this repo (or `npm link` for development)
5. Start with `frug-claude` or `frug-opencode`

## File Map

```
frugal-opencode/
│
├── bin/
│   ├── frug.js                  Main CLI (exports module + CLI handler, dual-mode via require.main)
│   ├── frug-claude.js           Wrapper: init → start --hybrid → spawn claude
│   └── frug-opencode.js         Wrapper: init → start --opencode --hybrid → spawn opencode
│
├── config/
│   └── defaults.js              Single source of truth: paths, timeouts, limits, version
│
├── packages/
│   │
│   ├── core/
│   │   ├── src/
│   │   │   ├── best-model.js            Model discovery, caching, task-based selection
│   │   │   ├── bridge.js                CCR preset manifest generation
│   │   │   ├── safe-restart.js          Idle detection, connection count, safe restart logic
│   │   │   └── idle-watcher.js          Daemon: poll idle, apply pending, rotate logs
│   │   └── test/
│   │       ├── best-model.test.js       10 tests: queryFreeModels, selectByTaskType, cache ops
│   │       ├── bridge.test.js           6 tests: buildManifest, presetManagement
│   │       ├── safe-restart.test.js     6 tests: isIdle, getActiveConnections, isRequestInFlight
│   │       └── idle-watcher.test.js     4 tests: daemon lifecycle, checkAndApplyPending
│   │
│   ├── watchdog/
│   │   ├── src/
│   │   │   └── watchdog.js              Daemon: ping models, detect degradation, restart CCR
│   │   └── test/
│   │       └── watchdog.test.js         6 tests: health checks, CCR restart, mainLoop
│   │
│   ├── skill/
│   │   └── SKILL.md                     Delegation guide: when/how to spawn free-tier agents
│   │
│   └── cli/
│       └── (commands defined inline in bin/frug.js)
│
├── presets/
│   ├── free-tier-max/
│   │   └── manifest.json                Example CCR preset (NVIDIA, Groq, Cerebras, SambaNova)
│   └── nvidia-focus/
│       └── manifest.json                NVIDIA NIM only
│
├── scripts/
│   └── stress-test.sh                   15 diagnostic tests: binary check, syntax, JSON validity
│
├── .github/workflows/
│   ├── ci.yml                           GitHub Actions: npm test on push/PR
│   └── preset-validation.yml            Validates presets/*.json syntax
│
├── .claude/
│   ├── agents/                          (empty, user creates custom agents here)
│   └── skills/frugality-usage/
│       └── SKILL.md                     (auto-installed by frug init)
│
├── .ai/ (project state, auto-created)
│   ├── CURRENT_TASK.md                  Current work status
│   ├── REPO_MAP.md                      Repository structure overview
│   ├── SESSION_SUMMARY.md               Build phase completion notes
│   ├── MODEL_STATE.json                 Runtime routing config (auto-generated)
│   └── FAILURES.ndjson                  Sub-agent failure log (manual or auto via script)
│
├── package.json                         Bin entries, scripts, zero dependencies
├── README.md                            Quick start, commands table, modes (GitHub-first)
├── CLAUDE.md                            Operations guide (when working on frugality itself)
├── CONTRIBUTING.md                      Contribution guide, preset submission template
├── HYBRID.md                            Hybrid mode deep dive
├── install.sh                           Install script: npm link (dev) or system-wide
├── DEVELOPMENT_STATE.md                 (this handoff document)
│
└── ~/.frugality/ (runtime state, auto-created)
    ├── state/
    │   ├── pending-restart              Flag file: deferred restart reason
    │   └── pending-config               Flag file: manifest to apply on idle
    ├── cache/
    │   └── best-model-{taskType}.txt    Model IDs for default/fast/analysis/reasoning
    ├── logs/
    │   └── bridge.log                   Operation log (rotated at 5MB)
    ├── watchdog.pid                     PID file for watchdog daemon
    └── idle-watcher.pid                 PID file for idle-watcher daemon
```

## Critical Implementation Notes for Next Agent

1. **Cache file format bug:** If cache is still malformed after free-coding-models fix, check `best-model.js:76` — may need to split writeCache into separate calls per file
2. **Test suite:** 85 failures are mostly error-case tests in opencode.test.js + failures.test.js that expect specific error messages. These are low priority; focus on 26 core tests passing first
3. **CCR integration:** watchdog.js and bridge.js reference CCR paths/ports but never validated against live CCR. May need stubs/mocks for full testing
4. **Model property name:** free-coding-models may return `id` or `modelId`; current code tries both. If still failing, log the actual object: `console.log(JSON.stringify(selected))` in selectByTaskType
5. **No external dependencies:** This is intentional. Do not add npm packages without explicit approval (complicates install.sh)
6. **Daemon safety:** Watchdog and idle-watcher use `setInterval` without `clearInterval` cleanup on stop. Future improvement: add SIGTERM handler

---

**Last commit:** ed86abe (fix: Add init step to convenience wrappers and improve model caching)
**Last test run:** 57/142 passing (core functionality OK, edge cases pending)
**Blocker:** Cache format validation pending free-coding-models CLI check
**Next milestone:** End-to-end validation with real model discovery + agent spawning
