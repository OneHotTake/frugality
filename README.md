# Frugality

Cost-optimized AI development using free-tier models for Claude Code or OpenCode.

## Quick Start

### For Claude Code (Recommended)

```bash
# Clone and set up
git clone https://github.com/OneHotTake/frugality.git
cd frugality
npm install

# Make commands available globally
npm link

# Run
frug-claude                    # Starts Claude Code in hybrid mode
frug-claude --help             # Show Claude Code help
```

### For OpenCode

```bash
# Same setup as above, then:
frug-opencode                  # Starts OpenCode in hybrid mode
frug-opencode --help           # Show OpenCode help
```

### Core Commands

```bash
frug start --hybrid            # Hybrid mode (subscription main + free agents)
frug start --agentic           # Fully free (all free-tier models)
frug start --opencode          # OpenCode fully free
frug status                    # Show system status
frug stop                      # Stop all processes
frug doctor                    # Diagnose and fix issues
frug update                    # Refresh model cache
```

## Operating Modes

| Mode | Main Model | Agents | Cost | Best For |
|------|-----------|--------|------|----------|
| **Hybrid** | Anthropic subscription | Free-tier | Low | Best reasoning + free agents |
| **Fully Free** | Free-tier | Free-tier | $0 | Maximum cost savings |
| **OpenCode Free** | Free-tier | Free-tier | $0 | OpenCode users, zero cost |

## Configuration

Set these environment variables to customize behavior:

```bash
export FRUGALITY_MAIN_MODEL="claude-sonnet-4-6"    # Default: claude-sonnet-4-6
export WATCHDOG_INTERVAL_MS="300000"                # Health check interval (ms)
export CACHE_TTL_MS="1800000"                       # Cache TTL (30 min)
```

State is stored in `~/.frugality/` (automatically created).

## External Dependencies

Frugality integrates with these systems:

- **[Claude Code](https://github.com/anthropics/claude-code)** — Official CLI tool for Claude
- **[OpenCode](https://github.com/anthropics/opencode)** — Agent-spawning platform for coding
- **[Free Coding Models](https://github.com/anthropics/free-coding-models)** — Free-tier models for agents
- **CCR (Claude Code Router)** — Optional routing layer for proxy mode (legacy)
- **claudish** — Optional sub-agent spawning for Claude Code (legacy)

## Architecture

```
frugality/
├── bin/
│   ├── frug.js           # Core CLI
│   ├── frug-claude.js    # Claude Code wrapper (starts hybrid mode)
│   └── frug-opencode.js  # OpenCode wrapper (starts hybrid mode)
├── packages/
│   ├── core/             # Model selection, caching, hybrid routing
│   ├── watchdog/         # Health monitoring
│   └── skill/            # Agent instruction templates
└── HYBRID.md             # Claude Code hybrid mode config (generated)
```

## Development

```bash
npm install                           # Install dependencies
npm link                              # Make frug-* commands available globally
npm run test                          # Run unit tests
node bin/frug.js doctor               # Diagnose issues
npm run start                         # Start system
npm run lint                          # Check code

# Direct usage without npm link
node bin/frug-claude.js               # Run frug-claude directly
node bin/frug.js start --hybrid       # Run frug directly
```

## License

MIT
