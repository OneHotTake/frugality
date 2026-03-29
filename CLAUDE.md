# Frugality — Cost-Optimized AI Development

Frugality is a lightweight orchestration tool that automatically discovers and configures the best free-tier AI models for Claude Code and OpenCode.

## Simplified Architecture

Frugality has been refactored to a minimal, high-utility structure:

```
frugality/
├── bin/
│   ├── frugal-claude       # Wrapper: update CCR + launch Claude
│   └── frugal-opencode    # Wrapper: update OpenCode + launch OpenCode
├── .frugality/
│   ├── cache/             # Model discovery cache
│   └── logs/             # Operation logs
├── scripts/
│   ├── install.sh        # Installation script
│   └── completions/      # Shell completions
├── frugality.py          # Main orchestration script (Python)
└── README.md             # Documentation
```

## How It Works

1. **Discovery**: `frugality.py` runs `free-coding-models --json` to discover available models
2. **Tier Mapping**: Maps models to routing tiers (default, background, think, longContext)
3. **Config Generation**: Generates CCR config with Providers + Router
4. **Atomic Write**: Uses temp file + rename for safe JSON updates

## Commands

| Command | Description |
|---------|-------------|
| `frugal-claude` | Update CCR config + launch Claude Code |
| `frugal-opencode` | Configure OpenCode + launch OpenCode |
| `python3 frugality.py` | Run config update only |

## Configuration Files

- **CCR Config**: `~/.claude-code-router/config.json`
- **OpenCode Config**: `~/.config/opencode/opencode.json` (managed by free-coding-models)
- **API Keys**: `~/.free-coding-models.json`

## Model Tier Reference

| Tier | SWE Score | Use Case |
|------|-----------|----------|
| S+ | ≥70% | Complex refactors, GitHub issues |
| S | 60-70% | General workhorse |
| A+/A | 40-60% | Secondary tasks |
| B+ | 30-40% | Small changes |

## Development

```bash
# Test configuration
python3 frugality.py

# Check CCR status
ccr status

# View logs
tail -f ~/.claude-code-router/logs/ccr-*.log
```
