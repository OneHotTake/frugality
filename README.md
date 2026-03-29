# Frugality

Cost-optimized AI development using free-tier models for Claude Code.

## Overview

Frugality orchestrates free-tier AI models for Claude Code, providing a cost-effective solution for AI-assisted development. It automatically selects the best available free models, handles caching, and manages routing based on task type.

## Features

- **Automatic Model Selection**: Intelligently selects the best free-tier model based on task type
- **Health Monitoring**: Watchdog monitors model health and triggers restarts when needed
- **Idle Detection**: Automatically handles pending restarts when the system is idle
- **Preset Management**: Easy configuration management for different model sets
- **Caching**: Reduces API calls by caching model selections
- **CLI Interface**: Simple command-line interface for all operations

## Requirements

- Node.js >= 18
- Home directory for state storage (~/.frugality)
- Claude Code Router (CCR) for model routing

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/frugality.git
cd frugality

# Install dependencies (if any)
npm install

# Initialize the system
node bin/frug.js doctor
```

## Quick Start

```bash
# Start the Frugality system
node bin/frug.js start

# Check status
node bin/frug.js status

# Stop the system
node bin/frug.js stop
```

## Commands

| Command | Description |
|---------|-------------|
| `start` | Start the Frugality system (watchdog + idle watcher) |
| `stop` | Stop the Frugality system |
| `status` | Show system status and health |
| `update` | Update model configurations |
| `doctor` | Diagnose and fix system issues |
| `version` | Show version information |
| `help` | Show help message |

## Configuration

Frugality uses environment variables for configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOME` | - | User home directory |
| `CCR_PORT` | 3456 | Claude Code Router port |
| `CCR_PRESETS_DIR` | ~/.claude-code-router/presets | Presets directory |
| `LOG_DIR` | ~/.frugality/logs | Log directory |
| `STATE_DIR` | ~/.frugality/state | State directory |
| `CACHE_DIR` | ~/.frugality/cache | Cache directory |
| `WATCHDOG_INTERVAL_MS` | 300000 | Health check interval (5 min) |
| `PING_TIMEOUT_MS` | 8000 | Health check timeout |
| `CACHE_TTL_MS` | 1800000 | Cache TTL (30 min) |

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
