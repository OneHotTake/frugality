const fs = require('fs');
const path = require('path');

const defaults = {
  STATE_DIR: path.join(process.env.HOME || '/home/user', '.frugality/state'),
  LOG_DIR: path.join(process.env.HOME || '/home/user', '.frugality/logs'),
  PENDING_RESTART: path.join(process.env.HOME || '/home/user', '.frugality/state/pending-restart'),
  PENDING_CONFIG: path.join(process.env.HOME || '/home/user', '.frugality/state/pending-config'),
  LOG_MAX_SIZE_BYTES: 5 * 1024 * 1024,
  IDLE_POLL_MS: 10000,
  PID_IDLE_WATCHER: path.join(process.env.HOME || '/home/user', '.frugality/idle-watcher.pid')
};

let watcherInterval = null;
let running = false;

const ensureDirs = () => {
  if (!fs.existsSync(defaults.STATE_DIR)) {
    fs.mkdirSync(defaults.STATE_DIR, { recursive: true });
  }
  if (!fs.existsSync(defaults.LOG_DIR)) {
    fs.mkdirSync(defaults.LOG_DIR, { recursive: true });
  }
};

const idleWatcher = {
  checkAndApplyPending: () => {
    ensureDirs();
    
    if (fs.existsSync(defaults.PENDING_RESTART)) {
      try {
        const content = fs.readFileSync(defaults.PENDING_RESTART, 'utf8');
        const pending = JSON.parse(content);
        return { action: 'restart', data: pending };
      } catch (e) {
        return null;
      }
    }
    
    if (fs.existsSync(defaults.PENDING_CONFIG)) {
      try {
        const content = fs.readFileSync(defaults.PENDING_CONFIG, 'utf8');
        const pending = JSON.parse(content);
        return { action: 'config', data: pending };
      } catch (e) {
        return null;
      }
    }
    
    return null;
  },

  rotateLogs: () => {
    ensureDirs();
    
    const logFile = path.join(defaults.LOG_DIR, 'frugality.log');
    
    if (!fs.existsSync(logFile)) {
      return { rotated: false, reason: 'no log file' };
    }
    
    try {
      const stats = fs.statSync(logFile);
      
      if (stats.size < defaults.LOG_MAX_SIZE_BYTES) {
        return { rotated: false, reason: 'size below threshold' };
      }
      
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const archiveName = `frugality-${timestamp}.log`;
      const archivePath = path.join(defaults.LOG_DIR, archiveName);
      
      fs.renameSync(logFile, archivePath);
      
      return { rotated: true, archivePath };
    } catch (e) {
      return { rotated: false, error: e.message };
    }
  },

  start: (opts) => {
    if (running) {
      return { started: false, reason: 'already running' };
    }
    
    const options = opts || {};
    const pollInterval = options.pollInterval || defaults.IDLE_POLL_MS;
    
    ensureDirs();
    
    const pidPath = defaults.PID_IDLE_WATCHER;
    fs.writeFileSync(pidPath, process.pid.toString());
    
    watcherInterval = setInterval(() => {
      idleWatcher.checkAndApplyPending();
      idleWatcher.rotateLogs();
    }, pollInterval);
    
    running = true;
    
    return { started: true, pollInterval };
  },

  stop: () => {
    if (!running) {
      return { stopped: false, reason: 'not running' };
    }
    
    if (watcherInterval) {
      clearInterval(watcherInterval);
      watcherInterval = null;
    }
    
    const pidPath = defaults.PID_IDLE_WATCHER;
    if (fs.existsSync(pidPath)) {
      fs.unlinkSync(pidPath);
    }
    
    running = false;
    
    return { stopped: true };
  },

  isRunning: () => {
    const pidPath = defaults.PID_IDLE_WATCHER;
    
    if (!fs.existsSync(pidPath)) {
      return false;
    }
    
    try {
      const pid = parseInt(fs.readFileSync(pidPath, 'utf8').trim(), 10);
      if (pid && !isNaN(pid)) {
        try {
          process.kill(pid, 0);
          return true;
        } catch (e) {
          return false;
        }
      }
      return false;
    } catch (e) {
      return false;
    }
  },

  setPendingConfig: (config) => {
    ensureDirs();
    const configData = {
      config: config || {},
      timestamp: new Date().toISOString()
    };
    fs.writeFileSync(defaults.PENDING_CONFIG, JSON.stringify(configData, null, 2));
    return configData;
  },

  clearPendingConfig: () => {
    if (fs.existsSync(defaults.PENDING_CONFIG)) {
      fs.unlinkSync(defaults.PENDING_CONFIG);
    }
    return true;
  },

  setStateDir: (dir) => {
    defaults.STATE_DIR = dir;
    defaults.PENDING_RESTART = path.join(dir, 'pending-restart');
    defaults.PENDING_CONFIG = path.join(dir, 'pending-config');
  },
  
  setLogDir: (dir) => {
    defaults.LOG_DIR = dir;
  },

  getDefaults: () => ({ ...defaults })
};

module.exports = idleWatcher;
