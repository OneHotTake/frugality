# Frugality — Operations Guide

This is the frugality repository. We use frugality itself to develop frugality.

## Project Overview

Frugality is a cost-optimized AI orchestration layer for Claude Code. It discovers free-tier models, routes work intelligently, and monitors health with zero-interruption restarts.

## Architecture

- **`packages/core/`** — Model selection, bridging, safe-restart logic
- **`packages/watchdog/`** — Health monitoring, proactive updates
- **`packages/skill/`** — Delegation guide for sub-agents
- **`bin/frug.js`** — CLI entry point
- **`config/defaults.js`** — Single source of truth for all settings

## Development Commands

```bash
npm test                # Run unit tests
npm run stress-test     # Full integration test
npm run doctor          # Diagnose issues
npm run start           # Start the system
npm run lint            # Check syntax
```

## AI Orchestration

This repo uses its own delegation system. When working here:

**Delegate immediately:**
- Test generation
- Documentation writing
- Boilerplate generation

**You handle:**
- Logic design (bridge, safe-restart, routing decisions)
- UX decisions (CLI commands, error messages)
- Code review before commits

Reference `packages/skill/SKILL.md` for full delegation guide.

## Session Startup

1. Read `CLAUDE.md` ← you are here
2. Read `.ai/CURRENT_TASK.md`
3. Read `.ai/REPO_MAP.md`
4. Check `.ai/FAILURES.ndjson` for blockers
5. Inspect `.ai/MODEL_STATE.json` for routes
6. Begin work — delegate when appropriate

## State Files

- `.ai/CURRENT_TASK.md` — what we're working on
- `.ai/REPO_MAP.md` — repository structure
- `.ai/MODEL_STATE.json` — current routing config
- `.ai/FAILURES.ndjson` — sub-agent failures (if any)

## Version

v0.1.0 — Initial release
