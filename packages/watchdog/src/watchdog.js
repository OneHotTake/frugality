'use strict';

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const defaults = require('../../../config/defaults');
const safeRestart = require('../../../packages/core/src/safe-restart');
const bridge = require('../../../packages/core/src/bridge');

let interval = null;
let isRunning = false;
let failureCount = 0;

const watchdog = {
  pingCurrentModel: () => {
    try {
      const port = defaults.CCR_PORT;
      const start = Date.now();
      
      const output = execSync(`curl -s -X POST http://localhost:${port}/v1/messages -H "Content-Type: application/json" -d '{"model":"test"}' 2>&1`, {
        timeout: defaults.PING_TIMEOUT_MS,
        encoding: 'utf8'
      });

      const latencyMs = Date.now() - start;
      const healthy = !output.includes('error');
      
      return { healthy, latencyMs, modelId: 'current' };
    } catch (err) {
      return { healthy: false, latencyMs: defaults.PING_TIMEOUT_MS, error: err.message };
    }
  },

  checkCCRProcess: () => {
    try {
      execSync(`curl -s http://localhost:${defaults.CCR_PORT}/health`, {
        timeout: 5000,
        encoding: 'utf8'
      });
      return { healthy: true };
    } catch (err) {
      return { healthy: false, error: err.message };
    }
  },

  handleUnhealthy: async (reason) => {
    try {
      console.log(`[watchdog] Model unhealthy: ${reason}, running bridge...`);
      
      // Stage new config
      await bridge.runBridge({ dryRun: false, immediate: false });
      
      // Set pending restart flag
      safeRestart.setPendingRestart(`watchdog: ${reason}`);
      
      failureCount++;
    } catch (err) {
      console.error(`[watchdog] Failed to handle unhealthy: ${err.message}`);
    }
  },

  handleCCRDown: (attempt) => {
    try {
      console.log(`[watchdog] CCR down (attempt ${attempt}/${defaults.MAX_CCR_RESTART_ATTEMPTS})`);
      
      if (attempt >= defaults.MAX_CCR_RESTART_ATTEMPTS) {
        console.error('[watchdog] CRITICAL: CCR restart attempts exhausted');
        fs.appendFileSync(
          path.join(defaults.LOG_DIR, 'watchdog.log'),
          `${new Date().toISOString()} CRITICAL: CCR down after ${attempt} restart attempts\n`,
          'utf8'
        );
        return false;
      }

      safeRestart.restartCCR();
      return true;
    } catch (err) {
      console.error(`[watchdog] CCR restart failed: ${err.message}`);
      return false;
    }
  },

  mainLoop: async () => {
    try {
      // Check CCR process
      const ccrHealth = watchdog.checkCCRProcess();
      if (!ccrHealth.healthy) {
        failureCount++;
        const shouldRetry = watchdog.handleCCRDown(failureCount);
        if (!shouldRetry) return;
      } else {
        failureCount = 0;
      }

      // Ping current model
      const modelHealth = watchdog.pingCurrentModel();
      if (!modelHealth.healthy || modelHealth.latencyMs > defaults.PING_TIMEOUT_MS) {
        await watchdog.handleUnhealthy(`latency ${modelHealth.latencyMs}ms`);
      }

      // Check proactive update interval
      const lastUpdate = watchdog.getLastUpdate();
      if (lastUpdate && Date.now() - lastUpdate > defaults.PROACTIVE_UPDATE_MS) {
        console.log('[watchdog] Proactive update interval reached, running bridge...');
        await bridge.runBridge({ immediate: false });
      }
    } catch (err) {
      console.error(`[watchdog] mainLoop error: ${err.message}`);
    }
  },

  getLastUpdate: () => {
    try {
      const statePath = path.join(defaults.STATE_DIR, 'last-update');
      if (fs.existsSync(statePath)) {
        return parseInt(fs.readFileSync(statePath, 'utf8'));
      }
    } catch (err) {
      // Ignore
    }
    return null;
  },

  setLastUpdate: () => {
    try {
      fs.mkdirSync(defaults.STATE_DIR, { recursive: true });
      fs.writeFileSync(path.join(defaults.STATE_DIR, 'last-update'), Date.now().toString(), 'utf8');
    } catch (err) {
      // Ignore
    }
  },

  rotateLogs: () => {
    try {
      if (!fs.existsSync(defaults.LOG_DIR)) return;

      const watchdogLog = path.join(defaults.LOG_DIR, 'watchdog.log');
      if (fs.existsSync(watchdogLog)) {
        const stat = fs.statSync(watchdogLog);
        if (stat.size > defaults.LOG_MAX_SIZE_BYTES) {
          fs.renameSync(watchdogLog, watchdogLog + '.1');
        }
      }
    } catch (err) {
      // Ignore
    }
  },

  start: (opts) => {
    opts = opts || {};
    const checkInterval = opts.interval || defaults.WATCHDOG_INTERVAL_MS;

    if (isRunning) return { already: true };

    try {
      fs.mkdirSync(defaults.STATE_DIR, { recursive: true });
      fs.mkdirSync(defaults.LOG_DIR, { recursive: true });
      fs.writeFileSync(defaults.PID_WATCHDOG, process.pid.toString(), 'utf8');
      
      isRunning = true;
      failureCount = 0;

      interval = setInterval(async () => {
        await watchdog.mainLoop();
        watchdog.rotateLogs();
      }, checkInterval);

      return { started: true, pid: process.pid, interval: checkInterval };
    } catch (err) {
      console.error(`[watchdog] Start failed: ${err.message}`);
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
      if (fs.existsSync(defaults.PID_WATCHDOG)) {
        fs.unlinkSync(defaults.PID_WATCHDOG);
      }
    } catch (err) {
      // Ignore
    }
    return { stopped: true };
  },

  status: () => {
    return {
      running: isRunning,
      pid: isRunning ? process.pid : null,
      failureCount,
      lastUpdate: watchdog.getLastUpdate()
    };
  },

  isRunning: () => {
    try {
      if (!fs.existsSync(defaults.PID_WATCHDOG)) return false;
      const pid = parseInt(fs.readFileSync(defaults.PID_WATCHDOG, 'utf8').trim());
      process.kill(pid, 0);
      return true;
    } catch (err) {
      return false;
    }
  }
};

module.exports = watchdog;
