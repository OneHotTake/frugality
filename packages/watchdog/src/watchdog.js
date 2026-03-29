const fs = require('fs');
const path = require('path');
const http = require('http');

const defaults = {
  WATCHDOG_INTERVAL_MS: 300000,
  PROACTIVE_UPDATE_MS: 1800000,
  PING_TIMEOUT_MS: 8000,
  CCR_PORT: 3456,
  LOG_DIR: path.join(process.env.HOME || '/home/user', '.frugality/logs'),
  STATE_DIR: path.join(process.env.HOME || '/home/user', '.frugality/state'),
  PID_WATCHDOG: path.join(process.env.HOME || '/home/user', '.frugality/watchdog.pid'),
  MAX_CCR_RESTART_ATTEMPTS: 3
};

let watchdogInterval = null;
let running = false;
let restartAttempts = 0;
let lastHealthCheck = null;

const ensureDirs = () => {
  if (!fs.existsSync(defaults.STATE_DIR)) {
    fs.mkdirSync(defaults.STATE_DIR, { recursive: true });
  }
  if (!fs.existsSync(defaults.LOG_DIR)) {
    fs.mkdirSync(defaults.LOG_DIR, { recursive: true });
  }
};

const watchdog = {
  pingCurrentModel: async () => {
    return new Promise((resolve) => {
      const req = http.request({
        hostname: 'localhost',
        port: defaults.CCR_PORT,
        path: '/health',
        method: 'GET',
        timeout: defaults.PING_TIMEOUT_MS
      }, (res) => {
        const healthy = res.statusCode === 200;
        resolve({ healthy, statusCode: res.statusCode, timestamp: Date.now() });
      });
      
      req.on('error', (err) => {
        resolve({ healthy: false, error: err.message, timestamp: Date.now() });
      });
      
      req.on('timeout', () => {
        req.destroy();
        resolve({ healthy: false, error: 'timeout', timestamp: Date.now() });
      });
      
      req.end();
    });
  },

  checkCCRProcess: () => {
    ensureDirs();
    
    const pidPath = defaults.PID_WATCHDOG;
    
    if (!fs.existsSync(pidPath)) {
      return { running: false, reason: 'no pid file' };
    }
    
    try {
      const pid = parseInt(fs.readFileSync(pidPath, 'utf8').trim(), 10);
      
      if (!pid || isNaN(pid)) {
        return { running: false, reason: 'invalid pid' };
      }
      
      try {
        process.kill(pid, 0);
        return { running: true, pid };
      } catch (e) {
        return { running: false, reason: 'process not found' };
      }
    } catch (e) {
      return { running: false, reason: e.message };
    }
  },

  handleUnhealthy: async (reason) => {
    const health = await watchdog.pingCurrentModel();
    
    if (!health.healthy) {
      restartAttempts++;
      
      if (restartAttempts >= defaults.MAX_CCR_RESTART_ATTEMPTS) {
        return { 
          action: 'max_restart_attempts_reached', 
          attempts: restartAttempts,
          reason 
        };
      }
      
      return { 
        action: 'restart', 
        attempt: restartAttempts,
        reason 
      };
    }
    
    return { action: 'none', reason: 'model recovered' };
  },

  handleCCRDown: (attempt) => {
    const maxAttempts = defaults.MAX_CCR_RESTART_ATTEMPTS;
    
    if (attempt >= maxAttempts) {
      return { 
        action: 'alert', 
        message: `CCR is down after ${attempt} restart attempts` 
      };
    }
    
    return { 
      action: 'retry', 
      attempt: attempt + 1,
      maxAttempts 
    };
  },

  mainLoop: async () => {
    ensureDirs();
    
    const processCheck = watchdog.checkCCRProcess();
    
    if (!processCheck.running) {
      lastHealthCheck = { healthy: false, error: processCheck.reason, timestamp: Date.now() };
      return { status: 'CCR not running', reason: processCheck.reason };
    }
    
    const health = await watchdog.pingCurrentModel();
    lastHealthCheck = health;
    
    if (!health.healthy) {
      restartAttempts++;
      
      if (restartAttempts <= defaults.MAX_CCR_RESTART_ATTEMPTS) {
        return { 
          status: 'unhealthy', 
          health,
          restartAttempts 
        };
      }
      
      return { 
        status: 'max_restarts_reached',
        health,
        restartAttempts 
      };
    }
    
    restartAttempts = 0;
    
    return { status: 'healthy', health };
  },

  start: (opts) => {
    if (running) {
      return { started: false, reason: 'already running' };
    }
    
    const options = opts || {};
    const interval = options.interval || defaults.WATCHDOG_INTERVAL_MS;
    
    ensureDirs();
    
    const pidPath = defaults.PID_WATCHDOG;
    fs.writeFileSync(pidPath, process.pid.toString());
    
    watchdogInterval = setInterval(async () => {
      await watchdog.mainLoop();
    }, interval);
    
    running = true;
    restartAttempts = 0;
    
    return { started: true, interval };
  },

  stop: () => {
    if (!running) {
      return { stopped: false, reason: 'not running' };
    }
    
    if (watchdogInterval) {
      clearInterval(watchdogInterval);
      watchdogInterval = null;
    }
    
    const pidPath = defaults.PID_WATCHDOG;
    if (fs.existsSync(pidPath)) {
      fs.unlinkSync(pidPath);
    }
    
    running = false;
    restartAttempts = 0;
    
    return { stopped: true };
  },

  status: () => {
    const processCheck = watchdog.checkCCRProcess();
    const health = lastHealthCheck;
    
    return {
      running,
      process: processCheck,
      lastHealthCheck: health,
      restartAttempts,
      uptime: running ? Date.now() : null
    };
  },

  rotateLogs: () => {
    ensureDirs();
    
    const logFile = path.join(defaults.LOG_DIR, 'watchdog.log');
    
    if (!fs.existsSync(logFile)) {
      return { rotated: false, reason: 'no log file' };
    }
    
    try {
      const stats = fs.statSync(logFile);
      const maxSize = 5 * 1024 * 1024;
      
      if (stats.size < maxSize) {
        return { rotated: false, reason: 'size below threshold' };
      }
      
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const archivePath = path.join(defaults.LOG_DIR, `watchdog-${timestamp}.log`);
      
      fs.renameSync(logFile, archivePath);
      
      return { rotated: true, archivePath };
    } catch (e) {
      return { rotated: false, error: e.message };
    }
  },

  resetRestartAttempts: () => {
    restartAttempts = 0;
    return { reset: true };
  },

  setInterval: (ms) => {
    defaults.WATCHDOG_INTERVAL_MS = ms;
  },
  
  setPort: (port) => {
    defaults.CCR_PORT = port;
  },

  setLogDir: (dir) => {
    defaults.LOG_DIR = dir;
  },

  setStateDir: (dir) => {
    defaults.STATE_DIR = dir;
    defaults.PID_WATCHDOG = path.join(dir, 'watchdog.pid');
  },

  getDefaults: () => ({ ...defaults })
};

module.exports = watchdog;
