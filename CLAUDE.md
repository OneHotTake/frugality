# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Frugality — Cost-Optimized AI Development

Frugality discovers available free-tier AI models and configures Claude Code Router (CCR) and OpenCode to use them automatically.

## Architecture

The flow is: `frugal-claude` / `frugal-opencode` wrapper scripts → `frugality.py` → writes CCR config → launches the tool.

**`frugality.py`** is the core engine:
1. Runs `free-coding-models --json --hide-unconfigured` (Node.js subprocess) to discover models
2. Falls back to `~/.frugality/cache/last-known-good.json` (24-hour cache) if discovery fails
3. Maps discovered models to 4 CCR routing tiers: `default` (S/S+), `background` (A+/A), `think` (reasoning models), `longContext` (>32K context)
4. Builds provider configs using API keys from `~/.free-coding-models.json`
5. Atomically writes `~/.claude-code-router/config.json` (temp file + rename)

**`bin/frugal-claude`**: Smart CCR wrapper that:
- Accepts `--connect` to skip config generation and connect to existing instance
- Accepts `--restart` / `--force` to update config and restart CCR
- When CCR is already running with no flags, shows interactive prompt recommending action based on config age (<5 min = connect; >5 min = restart with 5s timeout, defaults to recommendation)
- When CCR is not running, runs config generation and starts CCR
- Polls `localhost:3456` health check (8 retries × 2s) before launching claude
- Sets `ANTHROPIC_BASE_URL="http://127.0.0.1:3456"` and execs `claude`

**`bin/frugal-opencode`**: calls `frugality.py --opencode`, then `exec opencode`.

**`scripts/install.sh`**: installs npm deps (`free-coding-models`, `@musistudio/claude-code-router`), creates `~/.frugality/cache/` and `~/.frugality/logs/`, and generates wrapper scripts in `~/bin/` with the frugality.py path **hardcoded at install time**.

## Key Paths

| Path | Purpose |
|------|---------|
| `~/.free-coding-models.json` | API keys (input) |
| `~/.claude-code-router/config.json` | CCR config (output) |
| `~/.frugality/cache/last-known-good.json` | Model discovery cache |

## Development Commands

```bash
# Test config generation (dry run against live models)
python3 frugality.py

# Test OpenCode config path
python3 frugality.py --opencode

# Check CCR health
ccr status

# View CCR routing logs
tail -f ~/.claude-code-router/logs/ccr-*.log

# Re-run install (regenerates wrapper scripts with current path)
bash scripts/install.sh

# Frugal-Claude usage
frugal-claude                 # Interactive prompt if CCR running, otherwise normal startup
frugal-claude --connect       # Connect to existing instance without restart
frugal-claude --restart       # Update config and restart CCR (skip prompt)
frugal-claude --force         # Alias for --restart
```

## Model Tier Reference

| Tier | SWE Score | CCR Route Use Case |
|------|-----------|--------------------|
| S+ (≥70%) / S (60-70%) | `default` | General coding |
| A+ / A (40-60%) | `background` | Lightweight/background tasks |
| Contains "r1", "v3", "reasoning", "think" | `think` | Reasoning tasks |
| >32K context window | `longContext` | Large file/context tasks |

## Important Implementation Notes

- The 16 provider base URLs are hardcoded in `frugality.py`'s `PROVIDER_BASE_URLS` dict. Add new providers there.
- `frugality.py --opencode` flag is referenced by `frugal-opencode` but the OpenCode config path handling lives in `update_ccr_config()` — the flag currently triggers a separate code path.
- Wrapper scripts in `bin/` have the frugality.py path hardcoded (set during `install.sh`). If you move the repo, re-run the installer or update the path in the scripts manually.
- Cache TTL is 24 hours; to force fresh discovery, delete `~/.frugality/cache/last-known-good.json`.
