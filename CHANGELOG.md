# Changelog

## [1.0.0] - FINAL CCR RELEASE - 2026-03-31

### Deprecated
- Claude Code Router (CCR) retired: unreliable tool-call failover,
  no SSE protocol compliance, no sub-agent isolation.

### Migration
- Backend: claude-code-router → free-claude-code (cc-nim)
- Config target: CCR JSON → ~/.config/free-claude-code/.env
- Failover: restart-flag daemon → cc-nim exponential backoff +
  proactive rolling-window throttle + Task tool interception