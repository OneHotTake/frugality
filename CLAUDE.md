# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Frugality -- Cost-Optimized AI Development

Frugality discovers available free-tier AI models and configures [free-claude-code](https://github.com/Alishahryar1/free-claude-code) to use them automatically.

## Prerequisites

- Python 3.7+
- Node.js 18+
- `uv` (package manager)
- `free-coding-models` (npm)
- `free-claude-code` (uv tool) -- proxy backend that replaces retired CCR

## Architecture

### Model Discovery

Frugality tier maps models to cc-nim slots for intelligent routing.

**Default mode** (no flags):
- Runs `free-coding-models --json --hide-unconfigured` (live discovery)
- Maps discovered models to cc-nim slots: `MODEL_OPUS`, `MODEL_SONNET`, `MODEL_HAIKU`, `MODEL`
- Writes `~/.config/free-claude-code/.env` with model assignments
- Preserves existing user settings, only manages frugality lines

**Core invariant**: `free-coding-models` produces **candidates**; tier mapping produces **slot assignments**; routing uses **cc-nim** proxy.

The flow is: `claude-frugal` wrapper -> `frugality.py` -> writes `~/.config/free-claude-code/.env` -> invokes `fcc` proxy -> Claude Code.

**`frugality.py`** is the core engine:

1. Runs `free-coding-models --json` to discover candidates
2. Maps models to cc-nim slots based on tier:
   - S+/S models -> `MODEL_OPUS` (complex tasks)
   - S/A+ models -> `MODEL_SONNET` (core coding)
   - A/A- models -> `MODEL_HAIKU` (lightweight)
   - Fallback -> `MODEL` (catch-all)
3. Detects available providers from API keys
4. Writes `~/.config/free-claude-code/.env` with provider prefixes:
   - NIM models: `nvidia_nim/model/name`
   - OpenRouter models: `open_router/model/name`
5. Sets `NIM_ENABLE_THINKING=true` for models that support it

### Wrapper Scripts

**`bin/claude-frugal`**: cc-nim launcher that:
- Checks dependencies at startup (python3, node, uv, claude, fcc)
- Runs `frugality.py` for model discovery
- Verifies `~/.config/free-claude-code/.env` was written
- Prints active model routing
- Invokes `fcc` binary which handles proxy + Claude Code

**`bin/frugal-opencode`**: OpenCode launcher that:
- Checks dependencies (python3, node, free-coding-models, opencode)
- Runs `frugality.py` only if cache is older than 60 minutes
- Invokes `opencode` natively (no cc-nim proxy needed)
- OpenCode uses `free-coding-models --opencode` directly

**`scripts/install.sh`**: installs uv and free-claude-code via uv tool, creates `~/.config/free-claude-code/` directory, generates wrapper scripts with hardcoded paths, runs initial model discovery.

## Key Paths

| Path | Purpose |
|------|---------|
| `~/.free-coding-models.json` | API keys (input) |
| `~/.config/free-claude-code/.env` | cc-nim config file (output) |
| `~/.frugality/cache/` | Frugality cache directory |

## Development Commands

```bash
# Model discovery and config write
python3 frugality.py

# Run unit tests
python3 -m unittest discover tests -v

# Inspect cc-nim config
cat ~/.config/free-claude-code/.env

# Re-run install (regenerates wrapper scripts with current path)
bash scripts/install.sh
```

## Model Tier Reference

| Tier | SWE Score | cc-nim Slot | Use Case |
|------|-----------|-------------|----------|
| S+ (>=70%) / S (60-70%) | `MODEL_OPUS` | Complex tasks, planning |
| S/A+ (40-70%) | `MODEL_SONNET` | Core coding work |
| A/A- (20-40%) | `MODEL_HAIKU` | Quota checks, topic detection |
| Fallback | `MODEL` | Any available model |

## Important Implementation Notes

### cc-nim Integration

- **Config format**: `~/.config/free-claude-code/.env` with `MODEL_*` and `NIM_ENABLE_THINKING` keys
- **Provider prefixes**: Models must be prefixed with provider:
  - NIM: `nvidia_nim/model/name`
  - OpenRouter: `open_router/model/name`
  - Invalid prefix causes hard cc-nim startup error
- **Thinking mode**: Auto-detected from model name for kimi, nemotron, deepseek-r1, qwq
- **Atomic writes**: Preserve existing user config when writing new settings

### Provider Handling

- **Priority**: NVIDIA NIM (if API key) > OpenRouter (if API key) > fallback
- **Mixing**: Can use multiple providers in same config (NIM for heavy slots, OpenRouter for haiku)
- **Key detection**: Checks both `~/.free-coding-models.json` and existing cc-nim config

### cc-nim Behavior

- **Proxy server**: `fcc` binary handles proxy startup and lifecycle management
- **Task tool interception**: cc-nim forces `run_in_background=False` on all Task calls
- **Rate limiting**: cc-nim handles proactive rolling-window throttle AND reactive 429 exponential backoff
- **5 request categories**: Intercepted locally (quota probes, titles, prefixes, suggestions, paths) - never hit upstream provider

### free-claude-code Installation

- Install via: `uv tool install git+https://github.com/Alishahryar1/free-claude-code.git`
- Initialize: `fcc-init` (creates template config)
- Verify: `fcc --version`
- Use: `fcc` (starts proxy + launches Claude Code)