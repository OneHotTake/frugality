'use strict';

const path = require('path');
const HOME = process.env.HOME || '/home/user';

module.exports = {
  // File paths
  CCR_CONFIG: path.join(HOME, '.claude-code-router/config.json'),
  CCR_PORT: 3456,
  CCR_PRESETS_DIR: path.join(HOME, '.claude-code-router/presets'),
  FCM_JSON: path.join(HOME, '.free-coding-models.json'),
  LOG_DIR: path.join(HOME, '.frugality/logs'),
  STATE_DIR: path.join(HOME, '.frugality/state'),
  CACHE_DIR: path.join(HOME, '.frugality/cache'),
  PID_WATCHDOG: path.join(HOME, '.frugality/watchdog.pid'),
  PID_IDLE_WATCHER: path.join(HOME, '.frugality/idle-watcher.pid'),
  PENDING_RESTART: path.join(HOME, '.frugality/state/pending-restart'),
  PENDING_CONFIG: path.join(HOME, '.frugality/state/pending-config'),

  // Model selection
  MODEL_TIER: 'S',
  MODEL_SORT: 'fiable',

  // Timing
  WATCHDOG_INTERVAL_MS: 300000,        // 5 min
  PROACTIVE_UPDATE_MS: 1800000,        // 30 min
  PING_TIMEOUT_MS: 8000,               // 8 sec
  ACTIVE_REQUEST_TIMEOUT_S: 30,
  IDLE_POLL_MS: 10000,                 // 10 sec
  MAX_DEFER_WAIT_MS: 3600000,          // 1 hour

  // Limits
  MAX_CCR_RESTART_ATTEMPTS: 3,
  LOG_MAX_SIZE_BYTES: 5 * 1024 * 1024, // 5 MB
  CACHE_TTL_MS: 1800000,               // 30 min

  // Version
  get VERSION() {
    try {
      return require('../package.json').version;
    } catch (e) {
      return '0.1.0';
    }
  }
};
