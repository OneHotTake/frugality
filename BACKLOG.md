# Frugality Backlog

## Project Vision

Cost-optimized AI development using free-tier models. The primary program (either OpenCode or Claude Code) handles thinking and orchestrating, while subtasks/agents use the best available free models.

---

## Operating Modes

### Mode 1: Fully Free Mode (`--agentic` / default)
- Uses only free-tier models for all agents
- No paid models ever
- For Claude Code: start with `frug start --agentic`
- For OpenCode: start with `frug start --opencode`

### Mode 2: Hybrid Mode (`--hybrid`) ✅ Implemented
- Main program (Claude Code or OpenCode) uses Anthropic subscription for thinking/planning
- Subtasks/agents use free models where appropriate
- Best of both worlds: powerful reasoning + zero agent cost
- Flag: `--hybrid` (or `--opencode --hybrid`)

---

## Completed ✅

- [x] CLI with `start`, `stop`, `status`, `update`, `doctor`, `config` commands
- [x] `start --agentic` — fully-free Claude Code agentic mode
- [x] `start --opencode` — fully-free OpenCode mode
- [x] **`start --hybrid`** — hybrid mode (subscription main + free agents)
- [x] **`start --opencode --hybrid`** — hybrid OpenCode mode
- [x] **`frug init --hybrid`** — write `HYBRID.md` to project root
- [x] **`frug init --opencode`** — write `OPENCODE.md` to project root
- [x] `hybrid status` and `hybrid config` sub-commands
- [x] Hybrid state file (`~/.frugality/state/hybrid-mode`)
- [x] `HYBRID.md` template auto-written on `start --hybrid`
- [x] `packages/skill/HYBRID.md` — canonical hybrid routing reference
- [x] `packages/core/src/hybrid.js` — hybrid module
- [x] `stop` clears all mode state files (agentic, opencode, hybrid)
- [x] `status` detects and reports hybrid mode
- [x] Fixed `selectByTaskType` — actually routes by task type (fast/analysis/reasoning)
- [x] Fixed `refreshAll` — writes different models per task type
- [x] Fixed `bridge.promoteStaged` — staging dir is now a sibling (`.staging-<name>`), not inside the preset dir (prevented rename corruption)
- [x] Fixed `idle-watcher.checkAndApplyPending` — consumes pending files after reading (one-shot semantics)
- [x] Fixed `watchdog.mainLoop` — removed leading space in `'CCR not running'` status
- [x] Fixed silent error swallowing in `startAgentic`, `startOpenCode`, `update`, `agentRefresh`, `opencodeRefresh`
- [x] `config.js` deep-merge on load — new default keys are always present after upgrades
- [x] `hybrid` config section in `defaultConfig`
- [x] `doctor` auto-fixes stale PID files and missing directories
- [x] Status `--verbose` flag shows cached model list
- [x] `config set` without value returns error instead of silently doing nothing
- [x] Model cache: `best-model-fast.txt`, `best-model-analysis.txt`, `best-model-reasoning.txt`, `best-model-default.txt`
- [x] Test harness for `hybrid.js` (`packages/core/test/hybrid.test.js`)
- [x] CLI integration tests including hybrid mode (`packages/core/test/cli.test.js`)
- [x] Updated `failures.test.js` for new staging path format
- [x] Updated `SKILL.md`, `OPENCODE.md`, `README.md`, `BACKLOG.md` for hybrid mode

---

## In Progress / Near-Term

### Model Source: Replace Mock Data with Real API
The `best-model.js` module currently uses hardcoded mock models. Replace `queryFreeModels()` with a real HTTP call to the free-coding-models source.

```javascript
// Target implementation:
queryFreeModels: async (tier, sort, timeout) => {
  const url = process.env.FREE_MODELS_URL || 'https://api.free-coding-models.dev/v1/models';
  // GET with tier/sort query params, cache result, return parsed models
}
```

### Watchdog: Hybrid-Mode Health Check
The watchdog currently pings CCR (`localhost:3456`). In hybrid and agentic modes there's no CCR. Add a mode-aware health check:
- Hybrid/agentic: ping free-model cache freshness instead of CCR port
- Proxy: keep existing CCR health check

### `packages/cli/src/commands/` — Remove or Implement Stubs
All six stub files (`doctor.js`, `init.js`, `preset.js`, `start.js`, `status.js`, `update.js`) are dead code. Either delegate to `bin/frug.js` functions or remove the directory.

---

## Future Considerations

- [ ] Web UI for mode selection and live status
- [ ] Model performance analytics (latency, quality scores over time)
- [ ] Automatic model switching based on live health metrics
- [ ] Preset sharing community
- [ ] `frug benchmark` — test free models on a sample task and rank results
- [ ] Auto-select hybrid vs free mode based on task complexity score
- [ ] GitHub Actions integration: run `frug doctor` in CI to verify config

---

## State Files

| File | Purpose |
|------|---------|
| `~/.frugality/state/opencode-mode` | OpenCode mode config |
| `~/.frugality/state/agentic-mode` | Claude Code agentic mode |
| `~/.frugality/state/hybrid-mode` | **Hybrid mode config** ← new |
| `~/.frugality/cache/best-model-fast.txt` | Cached fast model |
| `~/.frugality/cache/best-model-analysis.txt` | Cached analysis model |
| `~/.frugality/cache/best-model-reasoning.txt` | Cached reasoning model |
| `~/.frugality/cache/best-model-default.txt` | Cached default model |
| `~/.frugality/cache/best-model-fallback.txt` | Permanent fallback |

---

## Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FRUGALITY_MODE` | free | Operating mode: free, agentic, hybrid |
| `FRUGALITY_MAIN_MODEL` | claude-sonnet-4-6 | Main model for hybrid mode |
| `FRUGALITY_AGENT_MODEL` | (from cache) | Override agent model for all task types |
| `OPENCODE_PRESETS_DIR` | ~/.opencode/presets | OpenCode presets |
| `CCR_PRESETS_DIR` | ~/.claude-code-router/presets | CCR presets |
| `FREE_MODELS_URL` | (future) | API endpoint for free-coding-models |

---

## Acceptance Criteria

- [x] `frug start` (no flags) starts without error
- [x] `frug start --opencode` works seamlessly with free models
- [x] `frug start --agentic` works with free models
- [x] `frug start --hybrid` enables hybrid mode
- [x] `frug start --opencode --hybrid` enables OpenCode hybrid mode
- [x] `frug init --hybrid` creates `HYBRID.md` in project root
- [x] `frug stop` clears all mode state files
- [x] `frug status` shows current mode (including hybrid)
- [x] Cache updates work for all modes
- [x] Each task type gets a different free model (fast ≠ analysis ≠ reasoning)
- [x] Documentation updated for all modes
- [x] Test coverage for hybrid module and CLI integration
