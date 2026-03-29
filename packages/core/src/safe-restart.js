const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const http = require('http');

const defaults = {
  PENDING_RESTART: path.join(process.env.HOME || '/home/user', '.frugality/state/pending-restart'),
  CCR_PORT: 3456,
  PING_TIMEOUT_MS: 8000,
  ACTIVE_REQUEST_TIMEOUT_S: 30,
  LOG_DIR: path.join(process.env.HOME || '/home/user', '.frugality/logs'),
  STATE_DIR: path.join(process.env.HOME || '/home/user', '.frugality/state'),
  PID_WATCHDOG: path.join(process.env.HOME || '/home/user', '.frugality/watchdog.pid')
};

const ensureDirs = () => {
  if (!fs.existsSync(defaults.STATE_DIR)) {
    fs.mkdirSync(defaults.STATE_DIR, { recursive: true });
  }
  if (!fs.existsSync(defaults.LOG_DIR)) {
    fs.mkdirSync(defaults.LOG_DIR, { recursive: true });
  }
};

const safeRestart = {
  getActiveConnections: (port) => {
    ensureDirs();
    const testPort = port || defaults.CCR_PORT;
    
    return new Promise((resolve) => {
      const req = http.request({
        hostname: 'localhost',
        port: testPort,
        path: '/health',
        method: 'GET',
        timeout: 1000
      }, (res) => {
        resolve({ count: res.statusCode === 200 ? 1 : 0, healthy: true });
      });
      
      req.on('error', () => {
        resolve({ count: 0, healthy: false });
      });
      
      req.on('timeout', () => {
        req.destroy();
        resolve({ count: 0, healthy: false });
      });
      
      req.end();
    });
  },

  isRequestInFlight: (logPath, timeoutSeconds) => {
    const logFile = logPath || path.join(defaults.LOG_DIR, 'requests.log');
    const timeout = timeoutSeconds || defaults.ACTIVE_REQUEST_TIMEOUT_S;
    
    if (!fs.existsSync(logFile)) {
      return false;
    }
    
    try {
      const stats = fs.statSync(logFile);
      const now = Date.now();
      const fileAge = now - stats.mtimeMs;
      
      return fileAge < (timeout * 1000);
    } catch {
      return false;
    }
  },

  isIdle: () => {
    return safeRestart.getActiveConnections().then(connections => {
      return connections.count === 0 && !safeRestart.isRequestInFlight();
    });
  },

  setPendingRestart: (reason) => {
    ensureDirs();
    const restartData = {
      reason: reason || 'unspecified',
      timestamp: new Date().toISOString()
    };
    fs.writeFileSync(defaults.PENDING_RESTART, JSON.stringify(restartData, null, 2));
    return restartData;
  },

  clearPendingRestart: () => {
    if (fs.existsSync(defaults.PENDING_RESTART)) {
      fs.unlinkSync(defaults.PENDING_RESTART);
    }
    return true;
  },

  hasPendingRestart: () => {
    return fs.existsSync(defaults.PENDING_RESTART);
  },

  restartCCR: () => {
    ensureDirs();
    
    try {
      const pidPath = defaults.PID_WATCHDOG;
      if (fs.existsSync(pidPath)) {
        const pid = parseInt(fs.readFileSync(pidPath, 'utf8').trim(), 10);
        if (pid && !isNaN(pid)) {
          try {
            process.kill(pid, 'SIGTERM');
          } catch (e) {
          }
        }
      }
      
      return { success: true, message: 'CCR restart initiated' };
    } catch (error) {
      return { success: false, error: error.message };
    }
  },

  verifyCCRHealth: (port, timeout) => {
    const testPort = port || defaults.CCR_PORT;
    const testTimeout = timeout || defaults.PING_TIMEOUT_MS;
    
    return new Promise((resolve) => {
      const req = http.request({
        hostname: 'localhost',
        port: testPort,
        path: '/health',
        method: 'GET',
        timeout: testTimeout
      }, (res) => {
        const healthy = res.statusCode === 200;
        resolve({ healthy, statusCode: res.statusCode });
      });
      
      req.on('error', (err) => {
        resolve({ healthy: false, error: err.message });
      });
      
      req.on('timeout', () => {
        req.destroy();
        resolve({ healthy: false, error: 'timeout' });
      });
      
      req.end();
    });
  },

  safeRestart: async (opts) => {
    const options = opts || {};
    const force = options.force || false;
    const reason = options.reason || 'manual restart';
    
    if (!force) {
      const idle = await safeRestart.isIdle();
      if (!idle) {
        safeRestart.setPendingRestart(reason);
        return { status: 'pending', reason: 'not idle' };
      }
    }
    
    const result = safeRestart.restartCCR();
    
    if (result.success) {
      safeRestart.clearPendingRestart();
      return { status: 'restarted', reason };
    }
    
    return { status: 'failed', error: result.error };
  },

  getPendingRestart: () => {
    if (fs.existsSync(defaults.PENDING_RESTART)) {
      try {
        const content = fs.readFileSync(defaults.PENDING_RESTART, 'utf8');
        return JSON.parse(content);
      } catch {
        return null;
      }
    }
    return null;
  },

  setStateDir: (dir) => {
    defaults.STATE_DIR = dir;
    defaults.PENDING_RESTART = path.join(dir, 'pending-restart');
  },
  
  setLogDir: (dir) => {
    defaults.LOG_DIR = dir;
  },
  
  setPort: (port) => {
    defaults.CCR_PORT = port;
  },

  getDefaults: () => ({ ...defaults })
};

module.exports = safeRestart;
