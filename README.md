# Frugality

> Claude Code. Free models. Zero compromise.

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
frugality.py  ->  free-coding-models --json  ->  certify & tier  ->  write env file
    |
claudish --model <best-free-model> --interactive  ->  Claude Code
```

Every launch discovers the best available free models and configures [Claudish](https://github.com/MadAppGang/claudish) to proxy them. Just type `claude-frugal` instead of `claude`.

## Routing tiers

| Tier | Models | Used for |
|------|--------|----------|
| **default** | S/S+ (60-70% SWE) | General coding |
| **background** | A+/A (40-60%) | File reads, searches, busywork |
| **think** | Reasoning (R1, etc.) | Plan mode, hard bugs |
| **longContext** | >32K context | Big files, log analysis |

Claude Code picks the right slot per task. You never touch the config.

---

## Install

### What you need

| Dependency | Why | Install |
|-----------|-----|---------|
| Python 3.7+ | Core engine | [python.org](https://www.python.org/downloads/) |
| Node.js 18+ | Model discovery tools | [nodejs.org](https://nodejs.org/) |
| [Claude Code](https://claude.ai/code) | What you're making cheaper | Official installer |

### Step 1: Model discovery (required)

```bash
npm install -g free-coding-models
free-coding-models   # interactive -- walks you through API key setup
```

This discovers what free models are available from 16+ providers (Groq, Cerebras, SambaNova, NVIDIA, OpenRouter, etc.). You'll set up API keys once.

### Step 2: Claudish proxy (required)

```bash
npm install -g claudish
```

Claudish is the proxy that sits between Claude Code and the free models. It handles protocol compliance so Claude Code doesn't know it's not talking to Anthropic directly.

### Step 3: Frugality

```bash
git clone https://github.com/OneHotTake/frugality.git
cd frugality
./scripts/install.sh
```

The installer drops `claude-frugal` into `~/bin/`. Make sure that's in your `$PATH`.

### Verify

```bash
claude-frugal         # should discover models and launch
```

---

## Usage

```bash
claude-frugal         # discover models + launch Claude Code
python3 frugality.py  # discover models and write env file only (no launch)
```

## Troubleshooting

```bash
# Nothing working?
free-coding-models --json          # verify model discovery works
cat ~/.free-coding-models.json     # verify keys are there
claudish --version                 # verify Claudish is installed
cat ~/.frugality/current_env.sh    # check generated env file

# Force fresh model discovery (skip 24h cache)
rm ~/.frugality/cache/last-known-good.json

# Force fresh certification
python3 frugality.py --refresh
```

## Roadmap

- `--dry-run` -- preview config without writing
- `--tier` -- override model tier selection
- `frug doctor` -- one-command diagnostics
- Watchdog mode -- auto-refresh when a model's latency tanks

## License

MIT
