# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Frugality — Cost-Optimized AI Development

Frugality discovers available free-tier AI models and configures Claude Code Router (CCR) and OpenCode to use them automatically.

## Architecture

### Model Certification Gate

Frugality now enforces a **certification gate** to prevent routing through models that don't support tool calling.

**Default mode** (no flags):
- Loads `~/.frugality/cache/certified_models.json`
- Filters to `status == "certified"` only
- If none available → exit 1 with guidance to run `--refresh`
- Routes through certified models only

**Refresh mode** (`--refresh`):
- Runs `free-coding-models --json --hide-unconfigured` (live discovery)
- Probes candidates: emits tool call, validates roundtrip behavior
- Persists results to registry with `status: certified|failed|skipped|blocked`
- Routes through newly certified models

**Core invariant**: `free-coding-models` produces **candidates**; probing produces **eligibility**; routing uses **certified** models only.

The flow is: `frugal-claude` / `frugal-opencode` wrapper scripts → `frugality.py` → writes CCR config → launches the tool.

**`frugality.py`** is the core engine:

*Default mode:*
1. Loads `~/.frugality/cache/certified_models.json`
2. Filters to `status == "certified"`
3. Maps certified models to 4 CCR routing tiers: `default` (S/S+), `background` (A+/A), `think` (reasoning models), `longContext` (>32K context)
4. Builds provider configs using API keys from `~/.free-coding-models.json`
5. Atomically writes `~/.claude-code-router/config.json`

*Refresh mode (`--refresh`):*
1. Runs `free-coding-models --json --hide-unconfigured` to discover candidates
2. Falls back to `~/.frugality/cache/last-known-good.json` (24-hour cache) if discovery fails
3. Loads existing `~/.frugality/cache/certified_models.json`
4. Probes each candidate concurrently (4 workers):
   - Step 1+2: Emits `echo_number(7)` tool call
   - Step 3: Validates roundtrip (model consumes tool result, final response contains "49")
   - Records `status: certified|failed|skipped` with failure reason
5. Persists updated registry (increments `updated_at`, stamps each entry with `last_verified_at`)
6. Maps certified models to routing tiers (same as default mode)
7. Writes CCR config

**`bin/frugal-claude`**: Smart CCR wrapper that:
- Accepts `--connect` to skip config generation and connect to existing instance
- Accepts `--restart` / `--force` to update config and restart CCR
- Accepts `--refresh` to trigger live discovery + probing (can combine with `--restart`)
- When CCR is already running with no flags, shows interactive prompt recommending action based on config age (<5 min = connect; >5 min = restart with 5s timeout, defaults to recommendation)
- When CCR is not running, runs config generation and starts CCR
- Polls `localhost:3456` health check (8 retries × 2s) before launching claude
- Sets `ANTHROPIC_BASE_URL="http://127.0.0.1:3456"` and execs `claude`

**`bin/frugal-opencode`**: calls `frugality.py --opencode`, then `exec opencode`.

**`scripts/install.sh`**: installs npm deps (`free-coding-models`, `@musistudio/claude-code-router`), creates `~/.frugality/cache/` and `~/.frugality/logs/`, generates wrapper scripts in `~/bin/` with the frugality.py path **hardcoded at install time**, and runs initial `--refresh` to populate cert registry.

## Key Paths

| Path | Purpose |
|------|---------|
| `~/.free-coding-models.json` | API keys (input) |
| `~/.claude-code-router/config.json` | CCR config (output) |
| `~/.frugality/cache/last-known-good.json` | Model discovery cache (24-hour) |
| `~/.frugality/cache/certified_models.json` | Model certification registry (probed models, metadata) |

## Development Commands

```bash
# Use certified models (default mode; fails if no registry)
python3 frugality.py

# Discover and certify new models (refresh mode)
python3 frugality.py --refresh

# Test OpenCode config path (not yet implemented)
python3 frugality.py --opencode

# Run unit tests
python3 -m unittest discover tests -v

# Inspect certification registry
python3 -m json.tool ~/.frugality/cache/certified_models.json

# Check CCR health
ccr status

# View CCR routing logs
tail -f ~/.claude-code-router/logs/ccr-*.log

# Re-run install (regenerates wrapper scripts with current path, runs --refresh)
bash scripts/install.sh

# Frugal-Claude usage
frugal-claude                       # Interactive prompt if CCR running, otherwise normal startup
frugal-claude --connect             # Connect to existing instance without restart
frugal-claude --restart             # Update config and restart CCR (skip prompt)
frugal-claude --refresh             # Trigger live discovery + probing
frugal-claude --restart --refresh   # Combine: probe, then restart CCR
frugal-claude --force               # Alias for --restart
```

## Model Tier Reference

| Tier | SWE Score | CCR Route Use Case |
|------|-----------|--------------------|
| S+ (≥70%) / S (60-70%) | `default` | General coding |
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
- **Concurrency**: 4 workers for probing; tune `PROBE_WORKERS` if hitting rate limits

### Model Discovery & Routing

- The 16 provider base URLs are hardcoded in `frugality.py`'s `PROVIDER_BASE_URLS` dict. **Probing and CCR config generation both use this dict** — it is the single source of truth. Add new providers there.
- `free-coding-models` discovers candidates; certification probes validate tool-calling capability through the same provider URLs used in production routing.
- Wrapper scripts in `bin/` have the frugality.py path hardcoded (set during `install.sh`). If you move the repo, re-run the installer or update the path manually.
- Cache TTL (discovery): 24 hours; to force fresh discovery, delete `~/.frugality/cache/last-known-good.json`
- `frugality.py --opencode` flag is referenced by `frugal-opencode` but the OpenCode config path handling is not yet implemented.
