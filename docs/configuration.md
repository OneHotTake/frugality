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

### OpenCode Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCODE_PRESETS_DIR` | ~/.opencode/presets | OpenCode presets directory |

### Claude Code Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CCR_PORT` | 3456 | Port for Claude Code Router |
| `CCR_CONFIG` | ~/.claude-code-router/config.json | CCR configuration file path |
| `CCR_PRESETS_DIR` | ~/.claude-code-router/presets | CCR presets directory |

## State Files

Frugality maintains state in the following files:

- `~/.frugality/watchdog.pid` - Watchdog process ID
- `~/.frugality/idle-watcher.pid` - Idle watcher process ID
- `~/.frugality/state/pending-restart` - Pending restart data
- `~/.frugality/state/pending-config` - Pending configuration
- `~/.frugality/cache/model-cache.json` - Model selection cache

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

### OpenCode

```bash
# Set custom directories
export OPENCODE_PRESETS_DIR="$HOME/.opencode/presets"
export LOG_DIR="$HOME/.frugality/logs"
export STATE_DIR="$HOME/.frugality/state"

# Adjust timing
export WATCHDOG_INTERVAL_MS=60000
export IDLE_POLL_MS=5000

# Start the system
node bin/frug.js start
```

### Claude Code

```bash
# Set custom directories
export CCR_PRESETS_DIR="$HOME/.ccr/presets"
export CCR_CONFIG="$HOME/.ccr/config.json"
export LOG_DIR="$HOME/.frugality/logs"
export STATE_DIR="$HOME/.frugality/state"

# Adjust timing
export WATCHDOG_INTERVAL_MS=60000
export IDLE_POLL_MS=5000

# Start the system
node bin/frug.js start
```
