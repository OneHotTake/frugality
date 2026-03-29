'use strict';

const fs = require('fs');
const { execSync } = require('child_process');
const defaults = require('../../../config/defaults');

const safeRestart = {
  getActiveConnections: (port) => {
    try {
      const output = execSync(`ss -tan | grep :${port} | wc -l`, { encoding: 'utf8' });
      return parseInt(output.trim()) || 0;
    } catch (err) {
      try {
        const output = execSync(`lsof -i :${port} 2>/dev/null | wc -l`, { encoding: 'utf8' });
        return Math.max(0, parseInt(output.trim()) - 1); // Subtract header
      } catch (e) {
        return 0;
      }
    }
  },

  isRequestInFlight: (logPath, timeoutSeconds) => {
    try {
      if (!fs.existsSync(logPath)) return false;
      
      const lines = fs.readFileSync(logPath, 'utf8').split('\n').filter(l => l.trim());
      if (lines.length === 0) return false;

      const lastLine = lines[lines.length - 1];
      const match = lastLine.match(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
      if (!match) return false;

      const lastTs = new Date(match[0]).getTime();
      const age = (Date.now() - lastTs) / 1000;
      
      return age < timeoutSeconds && !lastLine.includes('completed');
    } catch (err) {
      return false;
    }
  },

  isIdle: (port, logPath) => {
    const connections = safeRestart.getActiveConnections(port);
    const inFlight = safeRestart.isRequestInFlight(logPath, defaults.ACTIVE_REQUEST_TIMEOUT_S);

    return {
      idle: connections === 0 && !inFlight,
      connections,
      inFlight,
      reason: connections > 0 ? `${connections} active connections` : 
              inFlight ? 'request in flight' : null
    };
  },

  setPendingRestart: (reason) => {
    try {
      fs.mkdirSync(defaults.STATE_DIR, { recursive: true });
      const tempFile = defaults.PENDING_RESTART + '.tmp';
      const data = { reason, timestamp: new Date().toISOString() };
      fs.writeFileSync(tempFile, JSON.stringify(data), 'utf8');
      fs.renameSync(tempFile, defaults.PENDING_RESTART);
    } catch (err) {
      console.error(`Failed to set pending restart: ${err.message}`);
    }
  },

  clearPendingRestart: () => {
    try {
      if (fs.existsSync(defaults.PENDING_RESTART)) {
        fs.unlinkSync(defaults.PENDING_RESTART);
      }
    } catch (err) {
      console.error(`Failed to clear pending restart: ${err.message}`);
    }
  },

  hasPendingRestart: () => {
    try {
      if (!fs.existsSync(defaults.PENDING_RESTART)) {
        return { pending: false };
      }
      const data = JSON.parse(fs.readFileSync(defaults.PENDING_RESTART, 'utf8'));
      const age = Date.now() - new Date(data.timestamp).getTime();
      return { pending: true, age, reason: data.reason };
    } catch (err) {
      return { pending: false };
    }
  },

  verifyCCRHealth: (port, timeout) => {
    timeout = timeout || 30000;
    const start = Date.now();
    
    while (Date.now() - start < timeout) {
      try {
        const output = execSync(`curl -s http://localhost:${port}/health 2>&1`, { 
          timeout: 5000,
          encoding: 'utf8'
        });
        if (output.includes('ok') || output.includes('healthy')) {
          return { healthy: true, latencyMs: Date.now() - start };
        }
      } catch (err) {
        // Still waiting
      }
      
      // Wait 500ms before retry
      const delay = () => new Promise(resolve => setTimeout(resolve, 500));
      require('util').promisify(setTimeout)(500);
    }

    return { healthy: false, latencyMs: timeout };
  },

  restartCCR: () => {
    try {
      execSync('ccr restart', { timeout: 60000 });
      return { restarted: true };
    } catch (err) {
      throw new Error(`CCR restart failed: ${err.message}`);
    }
  },

  safeRestart: (opts) => {
    opts = opts || {};
    const force = opts.force || false;
    const wait = opts.wait || false;
    const maxWaitMs = opts.maxWaitMs || defaults.MAX_DEFER_WAIT_MS;

    if (force) {
      safeRestart.restartCCR();
      safeRestart.clearPendingRestart();
      return { restarted: true, deferred: false, reason: 'forced' };
    }

    const idle = safeRestart.isIdle(defaults.CCR_PORT, path.join(defaults.LOG_DIR, 'ccr.log'));
    
    if (idle.idle) {
      safeRestart.restartCCR();
      safeRestart.clearPendingRestart();
      return { restarted: true, deferred: false, reason: 'idle' };
    }

    if (wait) {
      safeRestart.setPendingRestart('waiting for idle');
      return { restarted: false, deferred: true, reason: idle.reason };
    }

    safeRestart.setPendingRestart(idle.reason);
    return { restarted: false, deferred: true, reason: idle.reason };
  }
};

const path = require('path');
module.exports = safeRestart;
