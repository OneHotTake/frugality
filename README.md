# Frugality

> Claude Code. Free models. Zero compromise.

**✨ Beautiful, simple, and provider-friendly.**

---

⚠️ **WARNING**: This project is currently under heavy development and may break at any time. Use at your own risk!

---

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
🧪 Model probing ─── Tests tool-call capability
    │
📝 free-claude-code ── Routes to best models
    │
🤖 Claude Code
```

**Smart selection**: Automatically picks the best free model for each task:
- **Discovery**: Finds all models from free-coding-models
- **Probing**: Tests each model with actual tool calls (certifies working models)
- **Selection**: Picks certified models by tier (S+, S, A, B)
- **Routing**: Routes to best model for each task type
- **All providers**: Works with any provider in free-coding-models

---

## 🔧 Dependencies

Frugality depends on these tools:

### Required
- **Python 3.7+** - Core engine for model discovery
- **Node.js 18+** - Required for free-coding-models
- **uv** - Package manager for free-claude-code
- **Claude Code** - The main CLI
- **free-coding-models** - Discovers and manages all AI models
- **free-claude-code** - Proxy backend that routes Claude Code to models

[→ Configure models and API keys](https://github.com/xxradar/free-coding-models) (supports Ollama, LiteLLM, cloud providers, and custom endpoints).

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
claude-frugal --refresh      # Discover new models
claude-frugal --check-keys   # Verify API keys
claude-frugal --verbose     # Debug info
claude-frugal --skip-probe  # Skip model testing (faster)
claude-frugal --prompt      # Interactive model selection
claude-frugal --edit        # Edit model assignments
claude-frugal --timeout 5  # 5-second timeout for prompt
```

### Example Output

```
🚀 Frugality - Claude Code on Free Models

🔍 Discovering models...
✅ Providers available: openrouter, groq, nvidia

📋 Active Models:
  MODEL_OPUS     → openrouter/deepseek-v3     ⭐
  MODEL_SONNET   → groq/qwen-3.5              🌟
  MODEL_HAIKU    → nvidia/mistral-large       💪

🎯 Starting Claude Code...
```

### Interactive Selection Example

```
🚀 Frugality - Claude Code on Free Models

🔍 Testing models with tool calls...
 groq/qwen-3.5: OK
 openrouter/qwen-3.5: OK
 nvidia/qwen-3.5: FAIL (auth_error:401)

✅ 2 model(s) certified for tool use

🚀 Current Model Selection
============================================================

 Default (S)             → groq/qwen-3.5 (S, 128k)
 Background (A)          → groq/qwen-3.5 (S, 128k)
 Thinking (R1)           → groq/qwen-3.5 (S, 128k)
 Long Context            → groq/qwen-3.5 (S, 128k)

 Options:
 [1] ✅ Accept & Launch (timeout in 3s)
 [2] 🔄 Refresh from providers
 [3] ✏️  Edit model assignments
```

### Interactive Edit Mode Example

```
📋 Available models for 'Default (S)':
 [1] groq/qwen-3.5 (S, 128k) ← CURRENT
 [2] openrouter/qwen-3.5 (S, 128k)
 [3] nvidia/qwen-3.5 (S, 128k)
 [4] openrouter/deepseek-v3 (S+, 200k)

Select model for Default: 2
✅ Updated Default assignment
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

**❌ Probing takes too long**
```bash
# Skip model testing for faster startup
claude-frugal --skip-probe

# Or probe specific providers only
# Configure only needed providers in free-coding-models
```

**❌ Models failing probe tests**
```bash
# Check API keys are correct
free-coding-models --json | grep -E "(auth|error)"

# Skip probes if models are known to work
claude-frugal --skip-probe

# Models are tested with tool calls - some don't support this
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
- **Model testing**: Probes each model with real tool calls to verify capability
- **Quality-based routing**: Picks S+ models for complex tasks, S for coding, A for quick checks
- **Multi-provider support**: Works with any provider in free-coding-models
- **Provider display**: Shows provider and model (e.g., "openrouter/qwen-3.5")
- **Interactive selection**: Choose between providers when same model is available
- **Selection caching**: Remembers your choices for faster launches

### ✅ Beautiful UX
- Clear status messages
- Progress indicators
- Helpful error messages
- Interactive model selection with timeout
- Color-coded model tiers and status

### ✅ Interactive Features
- **Model Selection Prompt**: Shows current assignments with 3-second timeout
- **Model Editor**: Fine-tune which model handles each task type
- **Auto-selection**: Picks best models after timeout
- **Provider Choice**: When same model available from multiple providers

### ✅ Simple Setup
- Automatic model discovery
- Smart defaults
- One-command installation

---


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