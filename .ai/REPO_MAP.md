# Repository Map

## Structure
- `bin/` — CLI entry point (frug.js)
- `packages/core/` — Model selection, bridging, restarts
- `packages/watchdog/` — Health monitoring
- `packages/skill/` — Delegation guide
- `config/` — Configuration defaults
- `docs/` — Documentation
- `presets/` — CCR preset configurations
- `.ai/` — AI orchestration state

## Key Files
- `config/defaults.js` — Single source of truth
- `packages/core/src/best-model.js` — Model discovery + caching
- `packages/core/src/bridge.js` — FCM-to-CCR bridge
- `packages/core/src/safe-restart.js` — Zero-interruption restart
- `packages/core/src/idle-watcher.js` — Deferred apply logic
- `packages/watchdog/src/watchdog.js` — Health monitoring
- `bin/frug.js` — Main CLI
