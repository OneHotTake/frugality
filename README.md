# Frugality

> Claude Code. Free models. Zero compromise.

> **v1.0.0 -> v2.0.0 Migration:** CCR has been retired. Run `npm uninstall -g @musistudio/claude-code-router`
> to clean up. The `claude-frugal` command now uses Claudish as its proxy backend.

Claude Code is the best AI coding agent out there. It's also expensive when it's reading files, searching code, and doing background busywork. Frugality fixes that -- it auto-discovers the best free-tier models and routes the boring stuff there, so Claude's quota goes toward the things only Claude can do.

## How it works

```
claude-frugal
    |
frugality.py  ->  free-coding-models --json  ->  map to tiers  ->  write env file
    |
claudish --model <best-model> --interactive  ->  Claude Code
```

Every time you launch, it finds the best available free models and writes `~/.frugality/current_env.sh` for [Claudish](https://github.com/MadAppGang/claudish) to consume. You just type `claude-frugal` instead of `claude`.

## Routing tiers

| Route | Model tier | Used for |
|-------|-----------|----------|
| `default` | S-tier (60-70% SWE) | General coding |
| `background` | A-tier (40-60%) | File reads, searches, busywork |
| `think` | Reasoning model (R1, etc.) | Plan mode, hard bugs |
| `longContext` | >32K context | Big files, log analysis |

Claude Code picks the right slot per task. You never touch the config.

## Install

**Prerequisites:** Python 3.7+, Node.js 18+, [Claude Code](https://claude.ai/code)

```bash
# 1. Install the model tools
npm install -g free-coding-models claudish

# 2. Clone and install frugality
git clone https://github.com/OneHotTake/frugality.git
cd frugality
./scripts/install.sh

# 3. Set up your API keys (interactive)
free-coding-models
```

The installer drops `claude-frugal` into `~/bin/`. Make sure that's in your `$PATH`.

## Usage

```bash
claude-frugal         # discover models + launch Claude Code via Claudish
python3 frugality.py  # discover models and write env file only
```

## API keys

Keys live in `~/.free-coding-models.json`. Run `free-coding-models` once and it'll walk you through setup. Frugality supports [16 providers](frugality.py) including Groq, Cerebras, SambaNova, NVIDIA NIM, and OpenRouter.

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

## Call Classification

Frugality includes a `classify_call_weight()` function that detects lightweight API calls (quota checks, topic detection) vs heavy coding calls. This allows future routing optimizations where short, tool-free requests can be sent to cheaper models.

## Roadmap

- `--dry-run` -- preview env config without writing
- `--tier` -- override model tier selection
- `frug doctor` -- one-command diagnostics
- Watchdog mode -- auto-refresh when a model's latency tanks

## License

MIT
