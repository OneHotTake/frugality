# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Frugality -- Cost-Optimized AI Development

Frugality discovers available free-tier AI models and configures [Claudish](https://github.com/MadAppGang/claudish) to use them automatically.

## Prerequisites

- Python 3.7+
- Node.js 18+
- `free-coding-models` (npm)
- `claudish` (npm) -- proxy backend that replaces the retired CCR

## Architecture

### Model Certification Gate

Frugality enforces a **certification gate** to prevent routing through models that don't support tool calling.

**Default mode** (no flags):
- Loads `~/.frugality/cache/certified_models.json`
- Filters to `status == "certified"` only
- If none available -> exit 1 with guidance to run `--refresh`
- Maps certified models to 4 routing tiers
- Writes `~/.frugality/current_env.sh` with model env vars and Claudish invocation

**Refresh mode** (`--refresh`):
- Runs `free-coding-models --json --hide-unconfigured` (live discovery)
- Probes candidates: emits tool call, validates roundtrip behavior
- Persists results to registry with `status: certified|failed|skipped|blocked`
- Maps certified models to routing tiers and writes env file

**Core invariant**: `free-coding-models` produces **candidates**; probing produces **eligibility**; routing uses **certified** models only.

The flow is: `claude-frugal` wrapper -> `frugality.py` -> writes `~/.frugality/current_env.sh` -> sources env -> invokes `claudish --model <model> --interactive`.

**`frugality.py`** is the core engine:

*Default mode:*
1. Loads `~/.frugality/cache/certified_models.json`
2. Filters to `status == "certified"`
3. Maps certified models to 4 routing tiers: `default` (S/S+), `background` (A+/A), `think` (reasoning models), `longContext` (>32K context)
4. Selects best OpenRouter model for Claudish invocation
5. Writes `~/.frugality/current_env.sh` with env vars and `FRUG_CLAUDISH_INVOCATION`

*Refresh mode (`--refresh`):*
1. Runs `free-coding-models --json --hide-unconfigured` to discover candidates
2. Falls back to `~/.frugality/cache/last-known-good.json` (24-hour cache) if discovery fails
3. Loads existing `~/.frugality/cache/certified_models.json`
4. Probes each candidate concurrently (provider-aware, 2 workers):
   - Step 1+2: Emits `echo_number(7)` tool call
   - Step 3: Validates roundtrip (model consumes tool result, final response contains "49")
   - Records `status: certified|failed|skipped` with failure reason
5. Persists updated registry (increments `updated_at`, stamps each entry with `last_verified_at`)
6. Maps certified models to routing tiers (same as default mode)
7. Writes env file and prints summary

### Call Classification

`classify_call_weight(message_count, has_tools, prompt_length)` classifies API calls:
- Returns `"lightweight"` if message_count <= 2 AND no tools AND prompt_length < 500
- Returns `"heavy"` otherwise
- Purpose: detect quota-check/topic-detection calls for cheap routing

### Wrapper Scripts

**`bin/claude-frugal`**: Claudish launcher that:
- Checks dependencies at startup (python3, node, claudish, free-coding-models)
- Runs `frugality.py` for model discovery
- Sources `~/.frugality/current_env.sh`
- Invokes `$FRUG_CLAUDISH_INVOCATION --interactive` with pass-through args
- No restart logic, no daemon management -- Claudish handles protocol compliance

**`scripts/install.sh`**: installs npm deps (`free-coding-models`, `claudish`), creates `~/.frugality/cache/` and `~/.frugality/logs/`, generates `claude-frugal` wrapper in `~/bin/` with the frugality.py path **hardcoded at install time**, and runs initial model discovery.

## Key Paths

| Path | Purpose |
|------|---------|
| `~/.free-coding-models.json` | API keys (input) |
| `~/.frugality/current_env.sh` | Shell env file with model selections (output) |
| `~/.frugality/cache/last-known-good.json` | Model discovery cache (24-hour) |
| `~/.frugality/cache/certified_models.json` | Model certification registry (probed models, metadata) |
| `~/.frugality/cache/selected_models.json` | Model selection cache (24-hour) |

## Development Commands

```bash
# Use certified models (default mode; fails if no registry)
python3 frugality.py

# Discover and certify new models (refresh mode)
python3 frugality.py --refresh

# Run unit tests
python3 -m unittest discover tests -v

# Inspect certification registry
python3 -m json.tool ~/.frugality/cache/certified_models.json

# Check generated env file
cat ~/.frugality/current_env.sh

# Re-run install (regenerates wrapper scripts with current path)
bash scripts/install.sh
```

## Model Tier Reference

| Tier | SWE Score | Routing Use Case |
|------|-----------|------------------|
| S+ (>=70%) / S (60-70%) | `default` | General coding |
| A+ / A (40-60%) | `background` | Lightweight/background tasks |
| Contains "r1", "v3", "reasoning", "think" | `think` | Reasoning tasks |
| >32K context window | `longContext` | Large file/context tasks |

## Important Implementation Notes

### Certification Gate Mechanics

- **Probe version**: Increment `PROBE_VERSION` constant in `frugality.py` when probe logic changes (forces recertification on next `--refresh`)
- **Certification TTL**: Set by `CERT_TTL_DAYS` (default 7). Entries older than TTL are reprobed on `--refresh`
- **Registry schema**: Versioned; mismatch triggers empty registry (safe fallback)
- **Blocked status**: Set manually in registry to prevent a model from ever being probed or routed. Use `status: "blocked"`
- **Skipped status**: Automatic when credentials missing or provider unreachable (not model failure; does not route)
- **Failed status**: Model tested but behaviorally failed (e.g., no tool call, wrong roundtrip); does not route
- **Probe timeout**: 15s per HTTP call; retry on 429/5xx up to 2 times with exponential backoff
- **Concurrency**: 2 workers for probing with provider-aware scheduling; tune `PROBE_WORKERS` if hitting rate limits

### Model Discovery & Routing

- The provider base URLs are hardcoded in `frugality.py`'s `PROVIDER_BASE_URLS` dict. Probing uses this dict -- it is the single source of truth. Add new providers there.
- `free-coding-models` discovers candidates; certification probes validate tool-calling capability through the same provider URLs used in production routing.
- The `claude-frugal` wrapper has the frugality.py path hardcoded (set during `install.sh`). If you move the repo, re-run the installer or update the path manually.
- Cache TTL (discovery): 24 hours; to force fresh discovery, delete `~/.frugality/cache/last-known-good.json`
- Claudish is the proxy backend. It replaces the retired Claude Code Router (CCR). No more daemon management, health checks, or config.json routing.
