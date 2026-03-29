# frugality

> Claude Code. Free models. Zero compromise.

Cost-optimized AI development. Frugality routes free-tier models through Claude Code for reliable, intelligent coding assistance without subscription costs.

## Install

```bash
git clone https://github.com/OneHotTake/frugality.git
cd frugality
bash install.sh
```

## Quick start

### Claude Code (hybrid mode)

```bash
frug-claude
```

Starts frugality in hybrid mode with your Claude Code subscription as primary, free-tier agents for delegated tasks.

### OpenCode (free + hybrid)

```bash
frug-opencode
```

Starts frugality with OpenCode in hybrid mode.

## Prerequisites

- **Node.js** >= 18
- **Claude Code** or **OpenCode** installed
- **free-coding-models** ([repo](https://github.com/anthropics/free-coding-models))
- **jq**, **curl** (standard utilities)

## Commands

| Command | Description |
|---------|-------------|
| `frug-claude` | Start Claude Code with hybrid mode |
| `frug-opencode` | Start OpenCode with hybrid mode |
| `frug start [MODE]` | Start watchdog. MODE: `--hybrid`, `--agentic`, `--opencode` |
| `frug stop` | Stop all services |
| `frug status` | Show system status |
| `frug update [--immediate]` | Refresh model cache |
| `frug doctor` | Diagnose system |

## Operating modes

| Mode | Primary | Agents | Best for |
|------|---------|--------|----------|
| `--hybrid` | Subscription | Free-tier | Claude Code users with agents |
| `--agentic` | Free-tier | Free-tier | Zero-cost coding |
| `--opencode` | OpenCode | Free-tier | OpenCode with agents |
| `--opencode --hybrid` | Free-tier + OpenCode | Free | Fully autonomous coding |

## How it works

1. **Discovery**: Queries `free-coding-models` for available providers
2. **Selection**: Routes tasks to best model (NVIDIA, Groq, Cerebras, etc.)
3. **Health**: Watchdog monitors model performance, switches on degradation
4. **Safety**: Applies config changes only when system idle (zero-interruption)

## Development

```bash
npm test           # Run tests
npm run doctor     # Diagnose system
npm run stress-test # Stress tests
```

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
