# Configuration Guide

Frugality supports two integrations: OpenCode and Claude Code. Choose the configuration that matches your setup.

## Environment Variables

Frugality can be configured using environment variables. The following variables are supported:

### Common Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HOME` | Required | User home directory for state storage |
| `LOG_DIR` | ~/.frugality/logs | Log directory |
| `STATE_DIR` | ~/.frugality/state | State directory |
| `CACHE_DIR` | ~/.frugality/cache | Cache directory |

### Watchdog Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WATCHDOG_INTERVAL_MS` | 300000 | Health check interval (5 minutes) |
| `PROACTIVE_UPDATE_MS` | 1800000 | Proactive update interval (30 minutes) |
| `PING_TIMEOUT_MS` | 8000 | Health check timeout |
| `MAX_RESTART_ATTEMPTS` | 3 | Maximum restart attempts |

### Model Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_TIER` | S | Default model tier |
| `MODEL_SORT` | fiable | Model sort order (fiable/fast) |
| `FCM_JSON` | ~/.free-coding-models.json | Free models configuration |

### Idle Watcher Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `IDLE_POLL_MS` | 10000 | Idle check poll interval |
| `ACTIVE_REQUEST_TIMEOUT_S` | 30 | Request timeout in seconds |
| `MAX_DEFER_WAIT_MS` | 3600000 | Maximum defer wait (1 hour) |

### Cache Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_TTL_MS` | 1800000 | Cache TTL (30 minutes) |

### Logging Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_MAX_SIZE_BYTES` | 5242880 | Max log file size (5MB) |

### Hybrid Mode Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FRUGALITY_MAIN_MODEL` | `claude-sonnet-4-6` | Orchestrator model in hybrid mode |
| `FRUGALITY_MODE` | `free` | Operating mode: `free`, `agentic`, `hybrid` |

### OpenCode Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCODE_PRESETS_DIR` | ~/.opencode/presets | OpenCode presets directory |

### Claude Code Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CCR_PORT` | 3456 | Port for Claude Code Router (proxy mode only) |
| `CCR_CONFIG` | ~/.claude-code-router/config.json | CCR configuration file path |
| `CCR_PRESETS_DIR` | ~/.claude-code-router/presets | CCR presets directory |

## State Files

Frugality maintains state in the following files:

- `~/.frugality/watchdog.pid` — Watchdog process ID
- `~/.frugality/idle-watcher.pid` — Idle watcher process ID
- `~/.frugality/state/pending-restart` — Pending restart (one-shot; consumed on read)
- `~/.frugality/state/pending-config` — Pending config (one-shot; consumed on read)
- `~/.frugality/state/agentic-mode` — Active agentic mode config
- `~/.frugality/state/opencode-mode` — Active OpenCode mode config
- `~/.frugality/state/hybrid-mode` — **Active hybrid mode config** ← new
- `~/.frugality/cache/model-cache.json` — Structured model selection cache
- `~/.frugality/cache/best-model-fast.txt` — Best fast model ID
- `~/.frugality/cache/best-model-analysis.txt` — Best analysis model ID
- `~/.frugality/cache/best-model-reasoning.txt` — Best reasoning model ID
- `~/.frugality/cache/best-model-default.txt` — Default model ID
- `~/.frugality/cache/best-model-fallback.txt` — Permanent fallback model ID

## Preset Format

### OpenCode Presets

Presets are stored in `~/.opencode/presets/<name>/manifest.json`:

```json
{
  "version": "1.0",
  "models": [
    {
      "id": "claude-3-haiku",
      "name": "Claude 3 Haiku",
      "provider": "anthropic",
      "tier": "S",
      "capabilities": ["chat"],
      "metadata": {}
    }
  ],
  "createdAt": "2024-01-01T00:00:00.000Z"
}
```

### Claude Code Presets

Presets are stored in `~/.claude-code-router/presets/<name>/manifest.json`:

```json
{
  "version": "1.0",
  "models": [
    {
      "id": "claude-3-haiku",
      "name": "Claude 3 Haiku",
      "provider": "anthropic",
      "tier": "S",
      "capabilities": ["chat"],
      "metadata": {}
    }
  ],
  "createdAt": "2024-01-01T00:00:00.000Z"
}
```

## Example Configuration

### Hybrid Mode (Claude Code)

```bash
# Optional: override which Anthropic model is used as orchestrator
export FRUGALITY_MAIN_MODEL="claude-opus-4-6"

# Start — free-model cache refreshes automatically
node bin/frug.js start --hybrid

# Write HYBRID.md to project root
node bin/frug.js init --hybrid

# Check what models are being used
node bin/frug.js hybrid config
```

### Hybrid Mode (OpenCode)

```bash
export FRUGALITY_MAIN_MODEL="claude-sonnet-4-6"
node bin/frug.js start --opencode --hybrid
node bin/frug.js init --hybrid
```

### Fully-Free OpenCode

```bash
export OPENCODE_PRESETS_DIR="$HOME/.opencode/presets"
node bin/frug.js start --opencode
```

### Fully-Free Claude Code

```bash
export LOG_DIR="$HOME/.frugality/logs"
export WATCHDOG_INTERVAL_MS=60000
node bin/frug.js start --agentic
```

### Claude Code Proxy (requires CCR)

```bash
export CCR_PRESETS_DIR="$HOME/.ccr/presets"
export CCR_CONFIG="$HOME/.ccr/config.json"
node bin/frug.js start
```
