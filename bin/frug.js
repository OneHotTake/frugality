#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const defaults = {
  STATE_DIR: path.join(process.env.HOME || '/home/user', '.frugality/state'),
  PID_WATCHDOG: path.join(process.env.HOME || '/home/user', '.frugality/watchdog.pid'),
  PID_IDLE_WATCHER: path.join(process.env.HOME || '/home/user', '.frugality/idle-watcher.pid'),
  VERSION: '0.2.0'
};

const parseArgs = (args) => {
  const result = { flags: {}, positional: [] };
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith('--')) {
      const flag = args[i].slice(2);
      if (args[i + 1] && !args[i + 1].startsWith('--')) {
        result.flags[flag] = args[i + 1];
        i++;
      } else {
        result.flags[flag] = true;
      }
    } else if (args[i].startsWith('-')) {
      const flag = args[i].slice(1);
      result.flags[flag] = true;
    } else {
      result.positional.push(args[i]);
    }
  }
  return result;
};

const ensureDirs = () => {
  if (!fs.existsSync(defaults.STATE_DIR)) {
    fs.mkdirSync(defaults.STATE_DIR, { recursive: true });
  }
};

const frug = {
  run: async (args) => {
    const parsed = parseArgs(args);
    const command = parsed.positional[0] || 'help';
    
    switch (command) {
      case 'start':
        return frug.commands.start(parsed.positional.slice(1), parsed.flags);
      case 'agent':
        return frug.commands.agent(parsed.positional.slice(1), parsed.flags);
      case 'stop':
        return frug.commands.stop(parsed.positional.slice(1), parsed.flags);
      case 'status':
        return frug.commands.status(parsed.positional.slice(1), parsed.flags);
      case 'update':
        return frug.commands.update(parsed.positional.slice(1), parsed.flags);
      case 'doctor':
        return frug.commands.doctor(parsed.positional.slice(1), parsed.flags);
      case 'version':
        return frug.commands.version();
      case 'help':
      default:
        return frug.commands.help();
    }
  },

  commands: {
    start: (opts, flags) => {
      ensureDirs();
      
      const isAgentic = flags.agentic || flags.a;
      
      if (isAgentic) {
        return frug.commands.startAgentic(opts, flags);
      }
      
      const watchdog = require('../packages/watchdog/src/watchdog');
      const idleWatcher = require('../packages/core/src/idle-watcher');
      
      const wdResult = watchdog.start({ interval: 300000 });
      const iwResult = idleWatcher.start({ pollInterval: 10000 });
      
      return {
        success: true,
        mode: 'proxy',
        message: 'Frugality started in proxy mode',
        watchdog: wdResult,
        idleWatcher: iwResult
      };
    },

    startAgentic: (opts, flags) => {
      ensureDirs();
      
      const bestModel = require('../packages/core/src/best-model');
      const idleWatcher = require('../packages/core/src/idle-watcher');
      
      bestModel.refreshAll().then(() => {
        console.log('Model cache refreshed');
      }).catch(() => {
      });
      
      const iwResult = idleWatcher.start({ pollInterval: 10000 });
      
      const modeFile = path.join(defaults.STATE_DIR, 'agentic-mode');
      fs.writeFileSync(modeFile, JSON.stringify({
        mode: 'agentic',
        startedAt: new Date().toISOString(),
        version: defaults.VERSION
      }, null, 2));
      
      return {
        success: true,
        mode: 'agentic',
        message: 'Frugality started in agentic mode - Claude is now the primary router',
        idleWatcher: iwResult,
        skillPath: '../packages/skill/SKILL.md',
        promptPath: '../.prompts/operate-cost-optimized-mode.md',
        cacheDir: path.join(process.env.HOME || '/home/user', '.frugality/cache')
      };
    },

    agent: (opts, flags) => {
      const action = opts[0] || 'status';
      
      switch (action) {
        case 'status':
          return frug.commands.agentStatus(flags);
        case 'refresh':
          return frug.commands.agentRefresh(flags);
        case 'models':
          return frug.commands.agentModels(flags);
        default:
          return { error: `Unknown agent action: ${action}` };
      }
    },

    agentStatus: (flags) => {
      const modeFile = path.join(defaults.STATE_DIR, 'agentic-mode');
      let mode = { mode: 'proxy' };
      
      if (fs.existsSync(modeFile)) {
        try {
          mode = JSON.parse(fs.readFileSync(modeFile, 'utf8'));
        } catch (e) {
          mode = { mode: 'unknown' };
        }
      }
      
      const cacheDir = path.join(process.env.HOME || '/home/user', '.frugality/cache');
      const cacheFiles = fs.existsSync(cacheDir) 
        ? fs.readdirSync(cacheDir).filter(f => f.endsWith('.txt'))
        : [];
      
      return {
        version: defaults.VERSION,
        mode: mode.mode,
        startedAt: mode.startedAt,
        cacheFiles,
        skillActive: fs.existsSync('../packages/skill/SKILL.md')
      };
    },

    agentRefresh: (flags) => {
      const bestModel = require('../packages/core/src/best-model');
      
      bestModel.refreshAll().then(result => {
        return { success: true, refreshed: true, result };
      }).catch(err => {
        return { success: false, error: err.message };
      });
      
      return { success: true, message: 'Model cache refresh initiated' };
    },

    agentModels: (flags) => {
      const cacheDir = path.join(process.env.HOME || '/home/user', '.frugality/cache');
      const models = {};
      
      if (fs.existsSync(cacheDir)) {
        const files = fs.readdirSync(cacheDir);
        for (const file of files) {
          if (file.endsWith('.txt')) {
            const modelType = file.replace('.txt', '');
            models[modelType] = fs.readFileSync(path.join(cacheDir, file), 'utf8').trim();
          }
        }
      }
      
      return { models };
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

    update: (opts, flags) => {
      const bestModel = require('../packages/core/src/best-model');
      
      const isAgentic = flags.agentic || flags.a;
      
      if (isAgentic) {
        bestModel.refreshAll().then(result => {
          console.log('Agentic mode: Model cache refreshed');
        }).catch(err => {
          console.error('Refresh error:', err.message);
        });
        return {
          success: true,
          mode: 'agentic',
          message: 'Agentic mode: Model cache refreshed'
        };
      }
      
      bestModel.refreshAll().then(result => {
        console.log('Models refreshed:', result);
      });
      
      return {
        success: true,
        mode: 'proxy',
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
        version: defaults.VERSION,
        description: 'Cost-optimized AI development with free-tier models',
        commands: [
          { name: 'start', description: 'Start in proxy mode (CCR as router)' },
          { name: 'start --agentic', description: 'Start in agentic mode (Claude as router)' },
          { name: 'agent status', description: 'Show agentic mode status' },
          { name: 'agent models', description: 'List cached models' },
          { name: 'agent refresh', description: 'Refresh model cache' },
          { name: 'stop', description: 'Stop the Frugality system' },
          { name: 'status', description: 'Show system status' },
          { name: 'update', description: 'Update model configurations (proxy mode)' },
          { name: 'update --agentic', description: 'Update model cache (agentic mode)' },
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
