# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Frugality - Beautiful & Simple Free Model Routing

Frugality discovers available free-tier AI models and configures [free-claude-code](https://github.com/Alishahryar1/free-claude-code) to use them automatically.

## 🎯 Design Philosophy

- **Simple**: One command to get started
- **Beautiful**: Clear UI with helpful messages
- **Multi-provider**: Supports NVIDIA NIM, OpenRouter, Groq, 16+ more
- **Smart**: Automatic best-model selection per task

## 📦 Prerequisites

- Python 3.7+
- Node.js 18+
- `uv` (package manager)
- `free-coding-models` (npm)
- `free-claude-code` (uv tool)
- `claude` (npm)

## 🏗️ Architecture

### Core Flow

1. **Discovery**: `frugality.py` runs `free-coding-models --json`
2. **Selection**: Picks best models by tier (S+, S, A, B)
3. **Routing**: Writes `~/.config/free-claude-code/.env`
4. **Proxy**: `free-claude-code` routes to appropriate model

### Multi-Provider Support

All providers are supported with proper prefixes:
- NVIDIA NIM: `nvidia_nim/model/name`
- OpenRouter: `open_router/model/name`
- Groq: `groq/model/name`
- And 16+ more...

### Smart Features

- **Tier-based routing**: S+ for complex, S for coding, A for lightweight
- **Provider mixing**: Uses best available from each provider
- **Auto-thinking**: Enables thinking mode for supported models
- **Atomic writes**: Preserves user config

## 🚀 Scripts

### `bin/claude-frugal`
- Beautiful welcome banner
- Dependency checking with helpful messages
- Model discovery with progress
- Active model display
- Launches `fcc` proxy

### `bin/frugal-opencode`
- Launches OpenCode natively
- Uses same model discovery
- No proxy needed for OpenCode

### `scripts/install.sh`
- Delightful installation flow
- Clear dependency checking
- Creates both wrappers
- Runs initial discovery

## 📁 Key Paths

| Path | Purpose |
|------|---------|
| `~/.free-coding-models.json` | API keys (input) |
| `~/.config/free-claude-code/.env` | cc-nim config (output) |
| `~/.frugality/cache/` | Frugality cache |

## 🛠️ Development

### Testing

```bash
# Test model discovery
python3 frugality.py --check-keys

# Test full flow
claude-frugal --check-keys

# Run with verbose
python3 frugality.py --verbose
```

### Adding New Providers

1. Add to `PROVIDER_PREFIXES` in `frugality.py`
2. Update key detection in `get_existing_keys()`
3. Test with real API keys

## 🎨 UI/UX Patterns

### Success Messages
- Use ✅ for success
- Use 🚀 for actions
- Use 📋 for information
- Use 💡 for tips

### Error Messages
- Use ❌ for errors
- Use ⚠️ for warnings
- Always include fix suggestion
- Keep it concise

### Progress Indicators
- Use 🔍 for discovery
- Use 🎯 for launching
- Use 📊 for status

## 🔧 Implementation Notes

### Model Selection
- Sort by SWE score first
- Then by context size
- Prefer configured providers
- Always have fallbacks

### Config Writing
- Atomic writes with backup
- Preserve user settings
- Add clear markers
- Don't clobber custom configs

### Provider Support
- All providers from free-coding-models
- Automatic prefix detection
- Error handling for invalid prefixes
- Graceful degradation on failure