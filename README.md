# Frugality

Cost-optimized AI development using free-tier models for Claude Code or OpenCode.

## Overview

Frugality orchestrates free-tier AI models for AI-assisted development. It automatically selects the best available free models, handles caching, and manages routing based on task type. It supports both Claude Code and OpenCode.

## Features

- **Automatic Model Selection**: Intelligently selects the best free-tier model based on task type
- **Health Monitoring**: Watchdog monitors model health and triggers restarts when needed
- **Idle Detection**: Automatically handles pending restarts when the system is idle
- **Preset Management**: Easy configuration management for different model sets
- **Caching**: Reduces API calls by caching model selections
- **CLI Interface**: Simple command-line interface for all operations

## Choose Your Integration

| Integration | Best For | Requirements |
|------------|----------|--------------|
| **Claude Code** | Direct Claude CLI usage with CCR routing | CCR (Claude Code Router), claudish |
| **OpenCode** | Spawning AI agents for coding tasks | OpenCode CLI, native agent system |

---

## For OpenCode Users

The OpenCode integration lets you spawn AI agents that help with coding tasks using free-tier models. OpenCode handles agent spawning natively—no CCR or claudish needed.

### Requirements

- Node.js >= 18
- OpenCode CLI installed
- Home directory for state storage (~/.frugality)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/frugality.git
cd frugality

# Install dependencies
npm install

# Initialize the system
node bin/frug.js doctor
```

### Quick Start

```bash
# Start the Frugality system for OpenCode
node bin/frug.js start

# Check status
node bin/frug.js status

# Stop the system
node bin/frug.js stop
```

### How It Works

OpenCode can spawn agents to handle coding tasks. Frugality optimizes which free-tier model each agent uses:

1. Frugality maintains a cache of available free models
2. When OpenCode spawns an agent, Frugality routes it to the best available model
3. The watchdog monitors model health and updates routing when needed

### Example: Spawning Agents

With OpenCode, you can spawn agents for specific tasks:

```bash
# Have opencode delegate a task to an agent
opencode --agent "fix the bug in auth.js"

# Or use opencode's task command
opencode task "write tests for utils.js"
```

Frugality ensures these agents use cost-effective free-tier models.

---

## For Claude Code Users

The Claude Code integration uses CCR (Claude Code Router) for model routing. Ideal if you use Claude CLI directly.

### Requirements

- Node.js >= 18
- Claude Code Router (CCR) installed
- claudish for sub-agent spawning
- Home directory for state storage (~/.frugality)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/frugality.git
cd frugality

# Install dependencies
npm install

# Initialize the system
node bin/frug.js doctor
```

### Quick Start

```bash
# Start in proxy mode (CCR as router)
node bin/frug.js start

# OR start in agentic mode (Claude as primary router)
node bin/frug.js start --agentic

# Check status
node bin/frug.js status

# Stop the system
node bin/frug.js stop
```

### Operating Modes

#### Proxy Mode (Default)
CCR acts as the persistent routing daemon. Sub-agents use claudish. Rock-solid, transparent routing with minimal configuration.

#### Agentic Mode (Recommended)
Claude Code becomes the intelligent orchestrator. You decide which model to use for each task based on:
- Task type (boilerplate, tests, docs, analysis, reasoning)
- Token count
- Latency requirements

Claude reads the model cache and spawns sub-agents with the optimal model.

## Commands

### OpenCode Commands

| Command | Description |
|---------|-------------|
| `start` | Start Frugality for OpenCode |
| `stop` | Stop the Frugality system |
| `status` | Show system status and health |
| `update` | Update model cache |
| `doctor` | Diagnose and fix system issues |
| `version` | Show version information |
| `help` | Show help message |

### Claude Code Commands

| Command | Description |
|---------|-------------|
| `start` | Start in proxy mode (CCR as router) |
| `start --agentic` | Start in agentic mode (Claude as router) |
| `agent status` | Show agentic mode status |
| `agent models` | List cached models |
| `agent refresh` | Refresh model cache |
| `stop` | Stop the Frugality system |
| `status` | Show system status and health |
| `update` | Update model configurations |
| `update --agentic` | Update agentic mode cache |
| `doctor` | Diagnose and fix system issues |
| `version` | Show version information |
| `help` | Show help message |

## Configuration

Frugality uses environment variables for configuration:

### Common Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HOME` | - | User home directory |
| `LOG_DIR` | ~/.frugality/logs | Log directory |
| `STATE_DIR` | ~/.frugality/state | State directory |
| `CACHE_DIR` | ~/.frugality/cache | Cache directory |
| `WATCHDOG_INTERVAL_MS` | 300000 | Health check interval (5 min) |
| `PING_TIMEOUT_MS` | 8000 | Health check timeout |
| `CACHE_TTL_MS` | 1800000 | Cache TTL (30 min) |

### OpenCode Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCODE_PRESETS_DIR` | ~/.opencode/presets | OpenCode presets directory |

### Claude Code Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CCR_PORT` | 3456 | Claude Code Router port |
| `CCR_PRESETS_DIR` | ~/.claude-code-router/presets | CCR presets directory |
| `CCR_CONFIG` | ~/.claude-code-router/config.json | CCR configuration file |

## Architecture

```
frugality/
├── packages/
│   ├── core/           # Core functionality
│   │   ├── src/
│   │   │   ├── bridge.js      # Model preset management
│   │   │   ├── best-model.js  # Model selection & caching
│   │   │   ├── idle-watcher.js # Idle detection & pending actions
│   │   │   └── safe-restart.js # Safe restart logic
│   │   └── test/
│   ├── watchdog/      # Health monitoring
│   │   ├── src/
│   │   │   └── watchdog.js   # Health checks & restarts
│   │   └── test/
│   └── cli/           # CLI commands
│       └── src/
│           └── commands/
├── bin/
│   └── frug.js        # Main CLI entry point
└── config/
    └── defaults.js    # Default configuration
```

## Development

```bash
# Run tests
npm run test

# Run lint
npm run lint

# Run doctor
npm run doctor

# Start system
npm run start
```

## Testing

The project includes comprehensive unit and E2E tests:

```bash
# Run all tests
npm test

# Tests are located in:
# - packages/core/test/
# - packages/watchdog/test/
```

## Presets

### OpenCode Presets

Create presets in `~/.opencode/presets/<preset-name>/manifest.json`:

```json
{
  "version": "1.0",
  "models": [
    {
      "id": "claude-3-haiku",
      "provider": "anthropic",
      "tier": "S"
    }
  ]
}
```

### Claude Code Presets

Create presets in `~/.claude-code-router/presets/<preset-name>/manifest.json`:

```json
{
  "version": "1.0",
  "models": [
    {
      "id": "claude-3-haiku",
      "provider": "anthropic",
      "tier": "S"
    }
  ]
}
```

## License

MIT
