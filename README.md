# Frugality

> Claude Code. Free models. Zero compromise.

**✨ Beautiful, simple, and provider-friendly.**

---

## 🚀 Quick Start

Clone and install in one command:

```bash
git clone https://github.com/OneHotTake/frugality.git
cd frugality
./scripts/install.sh
```

Then:
```bash
claude-frugal  # Start coding with free models
```

---

## 🎯 How It Works

```
claude-frugal
    │
🔍 frugality.py ─── Discovers free models
    │
📝 free-claude-code ── Routes to best models
    │
🤖 Claude Code
```

**Smart selection**: Automatically picks the best free model for each task:
- Complex tasks → Highest scoring S+ models
- Coding → Powerful S models
- Quick checks → Lightweight A models
- All providers → Works with any provider in free-coding-models

---

## 🔧 Dependencies

Frugality depends on these tools:

### Required
- **Python 3.7+** - Core engine
- **Node.js 18+** - For free-coding-models
- **uv** - Package manager for free-claude-code
- **Claude Code** - The main CLI

### Optional (for model access)
- **free-coding-models** - Discovers and manages AI models
- **free-claude-code** - Proxy backend (required for Claude Code)

[→ See free-coding-models docs](https://github.com/xxradar/free-coding-models) for configuring local models like Ollama, LiteLLM, or custom endpoints.

---

## 📦 Installation

### 1. Install Dependencies

```bash
# Core tools
npm install -g free-coding-models
curl -LsSf https://astral.sh/uv/install.sh | sh

# Claude Code
npm install -g @anthropic-ai/claude

# Free Claude Code proxy
uv tool install git+https://github.com/Alishahryar1/free-claude-code.git
```

### 2. Setup API Keys

```bash
# Configure providers you want to use
free-coding-models
```

This will walk you through setting up API keys for providers like OpenRouter, Groq, etc.

### 3. Install Frugality

```bash
./scripts/install.sh
```

The installer will create `claude-frugal` command in your `~/bin`.

### 4. Verify Installation

```bash
claude-frugal --check-keys  # Check your API keys
claude-frugal --help        # See all options
```

---

## 🎮 Usage

### Basic Usage

```bash
claude-frugal              # Start coding with free models
```

### Advanced Options

```bash
claude-frugal --refresh    # Discover new models
claude-frugal --check-keys # Verify API keys
claude-frugal --verbose    # Debug info
```

### Example Output

```
🚀 Frugality - Claude Code on Free Models

🔍 Discovering models...
✅ Providers available: openrouter, groq

📋 Active Models:
  MODEL_OPUS     → deepseek-v3           ⭐
  MODEL_SONNET   → qwen-3.5             🌟
  MODEL_HAIKU    → mistral-large        💪

🎯 Starting Claude Code...
```

---

## 🛠️ Troubleshooting

### Quick Fixes

```bash
# Check API keys
claude-frugal --check-keys

# Refresh model list
claude-frugal --refresh

# Test free-coding-models
free-coding-models --json | head -5

# Check free-claude-code
fcc --version
```

### Common Issues

**❌ No models found**
```bash
# Check if free-coding-models sees your models
free-coding-models --json | head -10
```

**❌ Local models not showing**
```bash
# Configure local models in free-coding-models
# See: https://github.com/xxradar/free-coding-models
```

**❌ Missing dependencies**
```bash
# Install Node.js
# Install uv
# Install Claude Code
```

**❌ Config errors**
```bash
# Regenerate config
claude-frugal --refresh

# Check generated config
cat ~/.config/free-claude-code/.env
```

---

## 🌟 Features

### ✅ Smart Model Selection
- **Automatic discovery**: Finds models from all your configured providers
- **Quality-based routing**: Picks S+ models for complex tasks, S for coding, A for quick checks
- **Multi-provider support**: Works with any provider in free-coding-models
- **Clean display**: Shows exactly which model is handling each task type

### ✅ Beautiful UX
- Clear status messages
- Progress indicators
- Helpful error messages

### ✅ Simple Setup
- Automatic model discovery
- Smart defaults
- One-command installation

---

## 🔄 Migration from CCR

If you're coming from CCR:
```bash
# Uninstall old version
npm uninstall -g @musistudio/claude-code-router

# Install new backend
uv tool install git+https://github.com/Alishahryar1/free-claude-code.git

# Setup frugality
./scripts/install.sh
```

---

## 📊 Model Support

Frugality works with any model provider supported by [free-coding-models](https://github.com/xxradar/free-coding-models):

- **Cloud providers**: OpenRouter, Groq, Cerebras, NVIDIA NIM
- **Local models**: Ollama, LiteLLM, custom servers
- **50+ endpoints**: Everything from free-coding-models

To configure local models, see the [free-coding-models documentation](https://github.com/xxradar/free-coding-models).

---

## 🤝 Contributing

We love contributions! See the [GitHub repo](https://github.com/OneHotTake/frugality).

---

## 📄 License

MIT License