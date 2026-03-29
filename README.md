# frugality

> Claude Code. Free models. Zero compromise.

Professional AI-assisted development shouldn't require a paid API subscription
for every token. **Frugality** is the orchestration layer that makes free-tier
models a reliable foundation — not a compromise.

## What it does

- **Discovers free models** via `free-coding-models` CLI, live benchmarking
- **Routes intelligently** through claude-code-router based on task type
- **Stays responsive** with zero-interruption safe-restart logic
- **Monitors health** and switches models when performance degrades

## Architecture

```
┌─────────────────────────────────────────┐
│  Claude Code (Your brain, subscription)  │
└──────────────┬──────────────────────────┘
               │
        ┌──────v────────┐
        │  CCR (router) │
        └──────┬────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
   Free      Free      Free
  Model A  Model B   Model C
  (NVIDIA) (Groq)   (OpenRouter)
```

## Quick start

```bash
# Install
npm install -g frugality

# One-time project setup
frug init

# Start routing
frug start

# Code with free agents
ccr code
```

## Commands

| Command | Description |
|---------|-------------|
| `frug start` | Start watchdog + idle watcher |
| `frug stop` | Stop all services |
| `frug status` | Show current state |
| `frug update [--immediate]` | Refresh model cache |
| `frug init` | Initialize project |
| `frug doctor` | Diagnose system |

## Prerequisites

- **Node.js** >= 18
- **free-coding-models** ([install](https://github.com/anthropics/free-coding-models))
- **CCR** (Claude Code Router)
- **jq** (JSON processor)
- **curl** (HTTP client)

## How it works

1. **Discovery**: Frugality queries `free-coding-models` for available models
2. **Selection**: Best model selected for each task type (fast/analysis/reasoning)
3. **Routing**: Router pushes config to CCR, which intercepts Claude Code's calls
4. **Monitoring**: Watchdog pings models, detects degradation
5. **Switching**: When a model degrades, bridge finds replacement, restarts safely

## Contributing

We welcome contributions! Presets are the highest-value way to contribute.

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

MIT
