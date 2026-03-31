# Frugality

> Claude Code. Free models. Zero compromise.

**✨ Beautiful, simple, and multi-friendly.**

---

## 🚀 Fast Start

One command to get started:

```bash
npx frugality
```

That's it! It discovers free models and starts Claude Code. You'll be coding in ~30 seconds.

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

**Smart routing**: Automatically picks the best free model for each task:
- Complex tasks → Fast S+ models
- Coding → Powerful S models
- Quick checks → Lightweight A models
- All providers → NVIDIA NIM, OpenRouter, Groq, 16+ more

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
# Interactive setup
free-coding-models
```

Walk through the setup for providers you want to use (NVIDIA, OpenRouter, Groq, etc.).

### 3. Install Frugality

```bash
git clone https://github.com/OneHotTake/frugality.git
cd frugality
./scripts/install.sh
```

### 4. Verify Installation

```bash
claude-frugal --check-keys  # Check API keys
claude-frugal --help        # See all options
```

---

## 🎮 Usage

### Basic Usage

```bash
claude-frugal              # Start coding with free models
frugal-opencode            # Start OpenCode with free models
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
✅ Providers available: nvidia, openrouter

📋 Active Models:
  MODEL_OPUS     → DeepSeek V3        ⭐
  MODEL_SONNET   → MiniMax M2.5       🌟
  MODEL_HAIKU    → Mistral Large      💪

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
# Setup API keys
free-coding-models

# Check output
free-coding-models --json
```

**❌ Missing dependencies**
```bash
# Install Node.js
# Install uv
# Install Claude Code
```

**❌ Configuration errors**
```bash
# Regenerate config
claude-frugal --refresh

# Check config file
cat ~/.config/free-claude-code/.env
```

---

## 🌟 Features

### ✅ Multi-Provider Support
- NVIDIA NIM (local & cloud)
- OpenRouter
- Groq
- Cerebras
- 16+ other providers

### ✅ Smart Routing
- Tier-based model selection
- Automatic provider mixing
- Context-aware routing

### ✅ Beautiful UX
- Clear status messages
- Progress indicators
- Helpful error messages

### ✅ Zero Configuration
- Automatic model discovery
- Smart defaults
- One-command setup

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

## 📊 Supported Providers

| Provider | Models | Cost |
|----------|--------|------|
| NVIDIA NIM | Llama, Mistral, Kimi | Free |
| OpenRouter | DeepSeek, Qwen, Groq | Free tier |
| Groq | Mixtral, Llama | Free |
| Cerebras | Mixtral, Granite | Free |
| 16+ more | Various | Free tiers |

---

## 🤝 Contributing

We love contributions! See the [GitHub repo](https://github.com/OneHotTake/frugality).

---

## 📄 License

MIT License