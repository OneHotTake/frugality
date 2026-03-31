# Changelog

## [1.0.0] - FINAL CCR RELEASE - 2026-03-31

### Deprecated
- Claude Code Router (CCR) backend retired due to unreliable failover on
  tool call failures and lack of SSE protocol compliance.
- `frugal-claude` CCR wrapper is superseded by Claudish-backed implementation.
- CCR config generation in `frugality.py` is superseded by Claudish invocation.

### Migration
- Backend: claude-code-router → claudish
- Proxy model: HTTP config file → per-invocation --model flag
- Failover: restart-flag daemon → Claudish native protocol compliance
