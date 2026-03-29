# Frugality

Cost-optimized AI development using free-tier models for Claude Code and OpenCode.

## Overview

Frugality is a lightweight orchestration tool that automatically discovers and configures the best free-tier AI models for your coding workflow. It integrates with:

- **Claude Code** via Claude Code Router (CCR)
- **OpenCode** via its native configuration

## Features

- **Automatic Model Discovery**: Queries free-coding-models to find the best available models
- **Intelligent Routing**: Configures CCR with optimal routes for different task types:
  - `default` - Best S-tier model for general tasks
  - `background` - High-uptime A-tier model for lightweight tasks
  - `think` - Reasoning-heavy model (e.g., DeepSeek-R1)
  - `longContext` - Models with >32K context window
- **Atomic Config Updates**: Safe JSON writes prevent corruption
- **Zero Dependencies**: Pure Python - no external runtime requirements

## Requirements

- Python 3.7+
- [free-coding-models](https://github.com/vava-nessa/free-coding-models) - Model discovery
- [Claude Code Router](https://github.com/musistudio/claude-code-router) - For Claude Code routing
- OpenCode (optional) - For OpenCode integration

## Installation

### 1. Install Dependencies

```bash
# Install free-coding-models (if not already installed)
npm install -g free-coding-models

# Install Claude Code Router (if not already installed)  
npm install -g @musistudio/claude-code-router

# Install Claude Code
npm install -g @anthropic-ai/claude-code
```

### 2. Install Frugality

```bash
# Clone the repository
git clone https://github.com/OneHotTake/frugality.git
cd frugality

# Run the install script
./scripts/install.sh
```

Or manually:

```bash
# Add bin to your PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$PATH:/path/to/frugality/bin"

# Or create symlinks
sudo ln -s /path/to/frugality/bin/frugal-claude /usr/local/bin/
sudo ln -s /path/to/frugality/bin/frugal-opencode /usr/local/bin/
```

### 3. Configure API Keys

**Option A: Automatic (Recommended)**

Run free-coding-models for the first time - it will prompt you to enter API keys for any providers you want to use. Keys are saved automatically to `~/.free-coding-models.json`:

```bash
free-coding-models
```

**Option B: Manual**

Create `~/.free-coding-models.json` with your API keys:

```json
{
  "apiKeys": {
    "nvidia": "nvapi-xxxxxxxx",
    "groq": "gsk_xxxxxxxx",
    "openrouter": "sk-or-xxxxx"
  }
}
```

> **Tip:** free-coding-models supports many providers. Run `free-coding-models --help` to see all available options.

## Quick Start

### Using Claude Code

```bash
# Launch Claude Code with automatic model routing
frugal-claude

# Or manually run the config first, then launch
python3 frugality.py
ccr restart
claude
```

### Using OpenCode

```bash
# Launch OpenCode with best S-tier model
frugal-opencode
```

## Usage

### Command Wrappers

| Command | Description |
|---------|-------------|
| `frugal-claude` | Update CCR config + launch Claude Code |
| `frugal-opencode` | Update OpenCode config + launch OpenCode |

### Direct Script Usage

```bash
# Update CCR configuration only
python3 frugality.py

# Check CCR status
ccr status

# Restart CCR to apply new config
ccr restart
```

### Model Tier Reference

| Tier | Description | Use Case |
|------|-------------|----------|
| S+ (≥70%) | Best of the best | Complex refactors, GitHub issues |
| S (60-70%) | Strong general use | Primary workhorse |
| A+/A (40-60%) | Solid alternatives | Secondary tasks |
| A-/B+ (30-40%) | Smaller tasks | Quick edits, small changes |
| B/C (<30%) | Code completion | Edge cases, completion |

## Configuration

### CCR Config Location

`~/.claude-code-router/config.json`

Frugality generates this automatically with:
- `Providers` - List of configured providers with API endpoints
- `Router` - Model routing rules

### OpenCode Config Location

`~/.config/opencode/opencode.json`

Frugality leverages free-coding-models' built-in OpenCode configuration.

### Frugality Cache

`~/.frugality/`
- `cache/` - Model discovery cache
- `logs/` - Operation logs

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    Frugality                            │
│  ┌─────────────────────────────────────────────────┐   │
│  │           frugality.py                          │   │
│  │  1. Query free-coding-models --json            │   │
│  │  2. Map models to routing tiers               │   │
│  │  3. Generate CCR config (Providers + Router)  │   │
│  │  4. Atomic JSON write                        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐         ┌──────────────────┐
│ Claude Code      │         │ OpenCode         │
│ (via CCR)        │         │ (native config)  │
│                  │         │                  │
│ ~/.claude-code-  │         │ ~/.config/       │
│ router/config.json│         │ opencode.json    │
└──────────────────┘         └──────────────────┘
```

## Development

```bash
# Test the configuration script
python3 frugality.py

# Verify CCR config
cat ~/.claude-code-router/config.json

# Check CCR is running
ccr status

# View CCR logs
tail -f ~/.claude-code-router/logs/ccr-*.log
```

## Troubleshooting

### No models found

```bash
# Verify free-coding-models works
free-coding-models --json

# Check API keys are configured
cat ~/.free-coding-models.json
```

### CCR not routing correctly

```bash
# Restart CCR
ccr restart

# Check config
ccr doctor
```

### OpenCode not using configured model

```bash
# Use free-coding-models directly
free-coding-models --opencode --tier S
```

## Project Structure

```
frugality/
├── bin/
│   ├── frugal-claude      # Claude Code wrapper
│   └── frugal-opencode   # OpenCode wrapper
├── .frugality/
│   ├── cache/            # Model cache
│   └── logs/             # Logs
├── frugality.py          # Main orchestration script
└── README.md             # This file
```

## License

MIT
