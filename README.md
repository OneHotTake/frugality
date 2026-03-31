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

## 🔧 Running with Local Models

Frugality works great with local models! Here's how to set it up:

### Local Ollama Models

```bash
# Make sure Ollama is running
ollama serve

# Ollama models will automatically appear in free-coding-models
# They'll be listed as "ollama/llama3", "ollama/mistral", etc.
```

### Local LiteLLM/Proxy Servers

```bash
# Point free-coding-models to your local server
# Create ~/.free-coding-models.json:
{
  "local-server": {
    "baseUrl": "http://localhost:8000",
    "models": ["my-model"]
  }
}

# Run free-coding-models to configure
free-coding-models
```

### Self-Hosted Endpoints

Any OpenAI-compatible endpoint works:
- Local LLM servers
- Kubernetes clusters
- Cloud deployments
- Private APIs

Just add the endpoint to `free-coding-models` and frugality will automatically detect and use your models.

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

# For local models, ensure server is running:
ollama serve  # or your local server
```

**❌ Models not working**
```bash
# Some models don't support tool calls
# Frugality automatically filters these out
# Try: claude-frugal --refresh to get compatible models
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

### ✅ Works with Any Model
Frugality supports models from any source - cloud APIs, local servers, or self-hosted endpoints:

- **Cloud APIs**: OpenRouter, Groq, Cerebras, NVIDIA NIM
- **Local LLMs**: Ollama, LiteLLM, local OpenAI-compatible servers
- **Self-hosted**: Your own model endpoints
- **50+ providers**: Everything supported by free-coding-models

### ✅ Smart Model Filtering
We automatically discover and filter models to ensure they work well:

- **Tool-call compatibility**: Only models that support function calling are selected
- **Quality filtering**: Higher tier models (S+, S, A) are prioritized for complex tasks
- **Provider mixing**: Uses the best available model from each configured provider
- **Local & cloud**: Seamlessly works with both local and remote models

### ✅ Intelligent Selection
- **Tier-based routing**: S+ for complex tasks, S for coding, A for quick checks
- **Automatic fallback**: If your preferred model is unavailable, we use the next best
- **Clean display**: Shows you exactly which model is handling each task type

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

## 📊 Compatible Model Sources

Frugality works with any model source supported by `free-coding-models`:

**Cloud Providers:**
- OpenRouter (DeepSeek, Qwen, etc.)
- Groq (Mixtral, Llama)
- Cerebras (Mixtral, Granite)
- NVIDIA NIM

**Local & Self-Hosted:**
- Ollama servers
- LiteLLM proxies
- Custom OpenAI-compatible endpoints
- Kubernetes deployments

**All providers are supported** - cloud, local, or hybrid setups. Run:
```bash
free-coding-models --providers
```
to see all available options.

---

## 🤝 Contributing

We love contributions! See the [GitHub repo](https://github.com/OneHotTake/frugality).

---

## 📄 License

MIT License