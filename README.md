# Frugality

> Claude Code. Free models. Zero compromise.

## v2.0.0 Migration: CCR has been retired.
> Install the new backend: `uv tool install git+https://github.com/Alishahryar1/free-claude-code.git`
> Then run `fcc-init` to scaffold the config, and `claude-frugal` as normal.

## Fast Start

Already have Claude Code? One command:

```bash
npx frugality
```

That's it. It discovers free models, picks the best ones, and launches Claude Code through them. You'll be coding in ~30 seconds.

---

## How it works

```
claude-frugal
    |
frugality.py  ->  free-coding-models --json  ->  tier mapping  ->  write cc-nim config
    |
    fcc (proxy)  ←── Anthropic-format requests
         ├── opus slot  → NIM kimi-k2.5
         ├── sonnet slot → NIM glm4.7
         └── haiku slot  → OpenRouter step-3.5-flash
         |
         ▼
    Claude Code
```

Every launch discovers the best available free models and configures [free-claude-code](https://github.com/Alishahryar1/free-claude-code) to proxy them. Just type `claude-frugal` instead of `claude`.

## Routing tiers

| Tier | Models | Used for |
|------|--------|----------|
| **opus** | S/S+ (60-70% SWE) | Complex tasks, planning |
| **sonnet** | S/A+ (40-70%) | Core coding work |
| **haiku** | A/A- (20-40%) | Quota checks, topic detection |

free-claude-code automatically routes Claude Code's requests to the appropriate model based on complexity.

---

## Install

### What you need

| Dependency | Why | Install |
|-----------|-----|---------|
| Python 3.7+ | Core engine | [python.org](https://www.python.org/downloads/) |
| Node.js 18+ | Model discovery tools | [nodejs.org](https://nodejs.org/) |
| uv | Package manager for free-claude-code | [astral.sh/uv](https://astral.sh/uv) |
| [Claude Code](https://claude.ai/code) | What you're making cheaper | Official installer |

### Step 1: Model discovery (required)

```bash
npm install -g free-coding-models
free-coding-models   # interactive -- walks you through API key setup
```

This discovers what free models are available from 16+ providers (NVIDIA NIM, OpenRouter, Groq, etc.). You'll set up API keys once.

### Step 2: free-claude-code proxy (required)

```bash
uv tool install git+https://github.com/Alishahryar1/free-claude-code.git
fcc-init  # creates initial config
```

free-claude-code is the proxy that sits between Claude Code and the free models. It handles protocol compliance and intelligent routing.

### Step 3: Frugality

```bash
git clone https://github.com/OneHotTake/frugality.git
cd frugality
./scripts/install.sh
```

The installer drops `claude-frugal` and `frugal-opencode` into `~/bin/`. Make sure that's in your `$PATH`.

### Verify

```bash
claude-frugal         # should discover models and launch
```

---

## Usage

```bash
claude-frugal         # discover models + launch Claude Code
frugal-opencode       # launch OpenCode with free models (no proxy needed)
python3 frugality.py  # discover models and write cc-nim config only (no launch)
```

## Troubleshooting

```bash
# Check cc-nim is installed
fcc --version

# Check active model config
cat ~/.config/free-claude-code/.env

# Re-run model discovery manually
python3 frugality.py

# Check cc-nim logs (see free-claude-code docs for flags)
fcc --help

# Check model discovery
free-coding-models --json

# Force fresh model discovery
rm ~/.frugality/cache/last-known-good.json  # if cached
```

## Roadmap

- `--dry-run` -- preview config without writing
- `--tier` -- override model tier selection
- `frug doctor` -- one-command diagnostics
- Provider auto-detection for local NIM deployments

## License

MIT