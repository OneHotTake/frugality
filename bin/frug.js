#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const defaults = {
  STATE_DIR: path.join(process.env.HOME || '/home/user', '.frugality/state'),
  PID_WATCHDOG: path.join(process.env.HOME || '/home/user', '.frugality/watchdog.pid'),
  PID_IDLE_WATCHER: path.join(process.env.HOME || '/home/user', '.frugality/idle-watcher.pid'),
  VERSION: '0.1.0'
};

const ensureDirs = () => {
  if (!fs.existsSync(defaults.STATE_DIR)) {
    fs.mkdirSync(defaults.STATE_DIR, { recursive: true });
  }
};

const frug = {
  run: async (args) => {
    const command = args[0] || 'help';
    
    switch (command) {
      case 'start':
        return frug.commands.start(args.slice(1));
      case 'stop':
        return frug.commands.stop(args.slice(1));
      case 'status':
        return frug.commands.status(args.slice(1));
      case 'update':
        return frug.commands.update(args.slice(1));
      case 'doctor':
        return frug.commands.doctor(args.slice(1));
      case 'version':
        return frug.commands.version();
      case 'help':
      default:
        return frug.commands.help();
    }
  },

  commands: {
    start: (opts) => {
      ensureDirs();
      
      const watchdog = require('../packages/watchdog/src/watchdog');
      const idleWatcher = require('../packages/core/src/idle-watcher');
      
      const wdResult = watchdog.start({ interval: 300000 });
      const iwResult = idleWatcher.start({ pollInterval: 10000 });
      
      return {
        success: true,
        message: 'Frugality started successfully',
        watchdog: wdResult,
        idleWatcher: iwResult
      };
    },

    stop: (opts) => {
      const watchdog = require('../packages/watchdog/src/watchdog');
      const idleWatcher = require('../packages/core/src/idle-watcher');
      
      const wdResult = watchdog.stop();
      const iwResult = idleWatcher.stop();
      
      return {
        success: true,
        message: 'Frugality stopped',
        watchdog: wdResult,
        idleWatcher: iwResult
      };
    },

    status: (opts) => {
      const watchdog = require('../packages/watchdog/src/watchdog');
      const idleWatcher = require('../packages/core/src/idle-watcher');
      
      const wdStatus = watchdog.status();
      const iwRunning = idleWatcher.isRunning();
      
      return {
        version: defaults.VERSION,
        watchdog: wdStatus,
        idleWatcher: { running: iwRunning }
      };
    },

    update: (opts) => {
      const bestModel = require('../packages/core/src/best-model');
      const bridge = require('../packages/core/src/bridge');
      
      bestModel.refreshAll().then(result => {
        console.log('Models refreshed:', result);
      });
      
      return {
        success: true,
        message: 'Update initiated'
      };
    },

    doctor: (opts) => {
      const issues = [];
      const warnings = [];
      
      const dirs = [
        path.join(process.env.HOME || '/home/user', '.frugality'),
        path.join(process.env.HOME || '/home/user', '.claude-code-router'),
      ];
      
      for (const dir of dirs) {
        if (!fs.existsSync(dir)) {
          issues.push(`Missing directory: ${dir}`);
        }
      }
      
      const pidFiles = [defaults.PID_WATCHDOG, defaults.PID_IDLE_WATCHER];
      for (const pidFile of pidFiles) {
        if (fs.existsSync(pidFile)) {
          try {
            const pid = parseInt(fs.readFileSync(pidFile, 'utf8').trim(), 10);
            try {
              process.kill(pid, 0);
            } catch (e) {
              warnings.push(`Stale PID file: ${pidFile}`);
            }
          } catch (e) {
            issues.push(`Invalid PID file: ${pidFile}`);
          }
        }
      }
      
      return {
        success: issues.length === 0,
        issues,
        warnings,
        message: issues.length === 0 ? 'All checks passed' : 'Issues found'
      };
    },

    version: () => {
      return { version: defaults.VERSION };
    },

    help: () => {
      return {
        commands: [
          { name: 'start', description: 'Start the Frugality system' },
          { name: 'stop', description: 'Stop the Frugality system' },
          { name: 'status', description: 'Show system status' },
          { name: 'update', description: 'Update model configurations' },
          { name: 'doctor', description: 'Diagnose system issues' },
          { name: 'version', description: 'Show version information' },
          { name: 'help', description: 'Show this help message' }
        ]
      };
    }
  }
};

if (require.main === module) {
  const args = process.argv.slice(2);
  Promise.resolve(frug.run(args)).then(result => {
    console.log(JSON.stringify(result, null, 2));
  }).catch(err => {
    console.error('Error:', err.message);
    process.exit(1);
  });
}

module.exports = frug;
