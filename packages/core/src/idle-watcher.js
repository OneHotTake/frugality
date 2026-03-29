'use strict';

const fs = require('fs');
const path = require('path');
const defaults = require('../../../config/defaults');
const safeRestart = require('./safe-restart');
const bridge = require('./bridge');

let interval = null;
let isRunning = false;

const idleWatcher = {
  checkAndApplyPending: async () => {
    try {
      const pending = safeRestart.hasPendingRestart();
      const configPending = fs.existsSync(defaults.PENDING_CONFIG);

      if (!pending.pending && !configPending) {
        return { checked: true, applied: false };
      }

      const idle = safeRestart.isIdle(defaults.CCR_PORT, path.join(defaults.LOG_DIR, 'ccr.log'));
      
      if (!idle.idle) {
        // Still busy, check age
        if (pending.age > defaults.MAX_DEFER_WAIT_MS) {
          console.warn(`[idle-watcher] Pending restart deferred for ${pending.age}ms, exceeds max wait`);
        }
        return { checked: true, applied: false, reason: 'busy' };
      }

      // Idle! Apply pending
      if (configPending) {
        try {
          const config = JSON.parse(fs.readFileSync(defaults.PENDING_CONFIG, 'utf8'));
          bridge.promoteStaged(config.preset);
          fs.unlinkSync(defaults.PENDING_CONFIG);
        } catch (err) {
          console.error(`[idle-watcher] Failed to apply config: ${err.message}`);
        }
      }

      if (pending.pending) {
        safeRestart.restartCCR();
        safeRestart.clearPendingRestart();
      }

      return { checked: true, applied: true };
    } catch (err) {
      console.error(`[idle-watcher] Check failed: ${err.message}`);
      return { checked: false, applied: false, error: err.message };
    }
  },

  rotateLogs: () => {
    try {
      if (!fs.existsSync(defaults.LOG_DIR)) return;

      const files = fs.readdirSync(defaults.LOG_DIR);
      for (const file of files) {
        const filePath = path.join(defaults.LOG_DIR, file);
        const stat = fs.statSync(filePath);
        
        if (stat.size > defaults.LOG_MAX_SIZE_BYTES) {
          const rotated = filePath + '.1';
          if (fs.existsSync(rotated)) {
            fs.unlinkSync(rotated);
          }
          fs.renameSync(filePath, rotated);
        }
      }
    } catch (err) {
      console.error(`[idle-watcher] Log rotation failed: ${err.message}`);
    }
  },

  start: (opts) => {
    opts = opts || {};
    const pollInterval = opts.pollInterval || defaults.IDLE_POLL_MS;

    if (isRunning) return { already: true };

    try {
      // Create state dir
      if (!fs.existsSync(defaults.STATE_DIR)) {
        fs.mkdirSync(defaults.STATE_DIR, { recursive: true });
      }

      // Write PID file
      fs.writeFileSync(defaults.PID_IDLE_WATCHER, process.pid.toString(), 'utf8');
      isRunning = true;

      interval = setInterval(() => {
        idleWatcher.checkAndApplyPending();
        idleWatcher.rotateLogs();
      }, pollInterval);

      return { started: true, pid: process.pid, interval: pollInterval };
    } catch (err) {
      console.error(`[idle-watcher] Start failed: ${err.message}`);
      return { started: false, error: err.message };
    }
  },

  stop: () => {
    if (interval) {
      clearInterval(interval);
      interval = null;
    }
    isRunning = false;
    try {
      if (fs.existsSync(defaults.PID_IDLE_WATCHER)) {
        fs.unlinkSync(defaults.PID_IDLE_WATCHER);
      }
    } catch (err) {
      // Ignore
    }
    return { stopped: true };
  },

  isRunning: () => {
    try {
      if (!fs.existsSync(defaults.PID_IDLE_WATCHER)) return false;
      const pid = parseInt(fs.readFileSync(defaults.PID_IDLE_WATCHER, 'utf8').trim());
      // Check if process exists
      process.kill(pid, 0);
      return true;
    } catch (err) {
      return false;
    }
  }
};

module.exports = idleWatcher;
