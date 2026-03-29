# Frugality — Cost-Optimized AI Development

Frugality is an open-source project that orchestrates free-tier AI models for Claude Code or OpenCode. It provides a cost-effective solution for AI-assisted development.

## Architecture

Frugality consists of several components:

* `packages/core`: The core logic of Frugality, responsible for model selection, caching, and routing.
* `packages/watchdog`: A health monitor that triggers bridge updates when models degrade.
* `packages/cli`: The command-line interface for Frugality, providing commands for starting, stopping, and updating the system.
* `packages/skill`: The skill document for Frugality, defining the delegation rules and guidelines for AI-assisted development.

## This Branch: OpenCode Integration

This branch (`opencode`) is specifically designed for OpenCode. Unlike the main branch which uses CCR and claudish, this branch:

- Works with OpenCode's native agent spawning system
- Does not require Claude Code Router (CCR)
- Does not require claudish
- Routes agents to cost-effective free-tier models

## Development Commands

* `npm run test`: Run unit tests for all packages.
* `npm run stress-test`: Run stress tests for the entire system.
* `npm run doctor`: Run the doctor command to diagnose and fix issues.
* `npm run start`: Start the Frugality system.
* `npm run update`: Update the Frugality system to the latest version.

## AI Orchestration

For OpenCode, Frugality optimizes agent spawning. When OpenCode spawns an agent to help with coding tasks, Frugality ensures the agent uses the best available free-tier model.

The `packages/skill/SKILL.md` file defines the delegation rules and guidelines for AI-assisted development.

## State Files

Frugality uses several state files to manage its state:

* `.ai/CURRENT_TASK.md`: The current task being worked on.
* `.ai/REPO_MAP.md`: The repository structure.
* `.ai/SESSION_SUMMARY.md`: A summary of completed work.
* `.ai/FAILURES.ndjson`: A log of sub-agent failures.
* `.ai/MODEL_STATE.json`: The current routing configuration.

## Session Startup Checklist

1. Read `CLAUDE.md`.
2. Read `.ai/CURRENT_TASK.md`.
3. Read `.ai/REPO_MAP.md`.
4. Check `.ai/FAILURES.ndjson` for unresolved blockers.
5. Inspect `.ai/MODEL_STATE.json` for current routes.
6. Begin work — delegate immediately when task type qualifies.