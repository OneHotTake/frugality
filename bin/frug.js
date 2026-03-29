#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const defaults = {
  STATE_DIR: path.join(process.env.HOME || '/home/user', '.frugality/state'),
  PID_WATCHDOG: path.join(process.env.HOME || '/home/user', '.frugality/watchdog.pid'),
  PID_IDLE_WATCHER: path.join(process.env.HOME || '/home/user', '.frugality/idle-watcher.pid'),
  VERSION: '0.2.0'
};

const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m',
  gray: '\x1b[90m',
  bold: '\x1b[1m',
  dim: '\x1b[2m'
};

const format = {
  success: (msg) => `${colors.green}✓${colors.reset} ${msg}`,
  error: (msg) => `${colors.red}✗${colors.reset} ${msg}`,
  warn: (msg) => `${colors.yellow}⚠${colors.reset} ${msg}`,
  info: (msg) => `${colors.blue}ℹ${colors.reset} ${msg}`,
  header: (msg) => `${colors.cyan}${colors.bold}${msg}${colors.reset}`,
  dim: (msg) => `${colors.dim}${msg}${colors.reset}`,
  section: (msg) => `\n${colors.magenta}${msg}${colors.reset}\n`
};

const ensureDirs = () => {
  if (!fs.existsSync(defaults.STATE_DIR)) {
    fs.mkdirSync(defaults.STATE_DIR, { recursive: true });
  }
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

const printBanner = () => {
  console.log(`${colors.cyan}
  ____                    _     
 |  _ \\  ___  ___ _ __ | |_   
 | | | |/ _ \\/ __| '_ \\| __|  
 | |_| |  __/\\__ \\ | | | |_   
 |____/ \\___||___/_| |_|\\__|  
                              
 ${colors.reset}${colors.dim}Cost-Optimized AI Development v${defaults.VERSION}${colors.reset}
  `);
};

const printStatus = (status) => {
  console.log(format.section('System Status'));
  
  console.log(`${colors.bold}Mode:${colors.reset} ${status.mode === 'agentic' ? colors.cyan : colors.yellow}${status.mode}${colors.reset}`);
  console.log(`${colors.bold}Version:${colors.reset} ${status.version}`);
  console.log(`${colors.bold}Watchdog:${colors.reset} ${status.watchdog?.running ? colors.green + 'Running' + colors.reset : colors.red + 'Stopped' + colors.reset}`);
  console.log(`${colors.bold}Idle Watcher:${colors.reset} ${status.idleWatcher?.running ? colors.green + 'Running' + colors.reset : colors.red + 'Stopped' + colors.reset}`);
  
  if (status.cacheFiles?.length > 0) {
    console.log(format.dim(`\nCached models: ${status.cacheFiles.length}`));
    for (const file of status.cacheFiles) {
      const model = fs.readFileSync(path.join(process.env.HOME || '/home/user', '.frugality/cache', file), 'utf8').trim();
      console.log(`  ${colors.gray}${file.replace('.txt', '')}:${colors.reset} ${model}`);
    }
  }
};

const printHelp = () => {
  printBanner();
  console.log(format.section('Commands'));
  console.log(`  ${colors.green}start${colors.reset}              Start Frugality (proxy mode - Claude Code)`);
  console.log(`  ${colors.green}start --opencode${colors.reset}   Start for OpenCode (recommended for OpenCode users)`);
  console.log(`  ${colors.green}start --agentic${colors.reset}   Start in agentic mode (Claude Code - recommended)`);
  console.log(`  ${colors.green}start --light${colors.reset}     Start in light mode (minimal)`);
  console.log(`  ${colors.green}stop${colors.reset}               Stop Frugality`);
  console.log(`  ${colors.green}status${colors.reset}             Show system status`);
  console.log(`  ${colors.green}agent status${colors.reset}       Show agentic mode details (Claude Code)`);
  console.log(`  ${colors.green}agent models${colors.reset}      List cached models`);
  console.log(`  ${colors.green}agent refresh${colors.reset}     Refresh model cache`);
  console.log(`  ${colors.green}update${colors.reset}            Update models`);
  console.log(`  ${colors.green}update --opencode${colors.reset} Update models for OpenCode`);
  console.log(`  ${colors.green}doctor${colors.reset}            Diagnose issues`);
  console.log(`  ${colors.green}interactive${colors.reset}        Interactive mode`);
  console.log(`  ${colors.green}config${colors.reset}            Edit configuration`);
  console.log(`  ${colors.green}version${colors.reset}            Show version`);
  console.log(`  ${colors.green}help${colors.reset}              Show this help`);
  console.log();
  console.log(format.dim('Quick aliases:'));
  console.log(`  frug-now     = start --agentic`);
  console.log(`  frug-open    = start --opencode`);
  console.log(`  frug-doc     = help`);
};

const runInteractive = () => {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  const prompt = () => {
    rl.question(`${colors.cyan}frugality>${colors.reset} `, async (input) => {
      const args = input.trim().split(/\s+/);
      if (args[0] === 'exit' || args[0] === 'quit') {
        rl.close();
        return;
      }
      
      if (args[0]) {
        try {
          const result = await frug.run(args);
          if (result && typeof result === 'object') {
            if (result.message) console.log(format.success(result.message));
            if (result.success !== undefined && !result.success) {
              console.log(format.error(result.message || 'Command failed'));
            }
          }
        } catch (e) {
          console.log(format.error(e.message));
        }
      }
      
      prompt();
    });
  };

  printBanner();
  console.log(format.info('Type "help" for commands, "exit" to quit\n'));
  prompt();
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
      case 'opencode':
        return frug.commands.opencode(parsed.positional.slice(1), parsed.flags);
      case 'stop':
        return frug.commands.stop(parsed.positional.slice(1), parsed.flags);
      case 'status':
        return frug.commands.status(parsed.positional.slice(1), parsed.flags);
      case 'update':
        return frug.commands.update(parsed.positional.slice(1), parsed.flags);
      case 'doctor':
        return frug.commands.doctor(parsed.positional.slice(1), parsed.flags);
      case 'config':
        return frug.commands.config(parsed.positional.slice(1), parsed.flags);
      case 'interactive':
      case 'i':
        runInteractive();
        return { mode: 'interactive' };
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
      const isLight = flags.light || flags.l;
      const isOpenCode = flags.opencode || flags.o;
      
      if (isOpenCode) {
        return frug.commands.startOpenCode(opts, flags);
      }
      
      if (isAgentic) {
        return frug.commands.startAgentic(opts, flags);
      }
      
      if (isLight) {
        return frug.commands.startLight(opts, flags);
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
        message: 'Frugality started in agentic mode',
        idleWatcher: iwResult,
        skillPath: '../packages/skill/SKILL.md',
        cacheDir: path.join(process.env.HOME || '/home/user', '.frugality/cache')
      };
    },

    startOpenCode: (opts, flags) => {
      ensureDirs();
      
      const bestModel = require('../packages/core/src/best-model');
      const idleWatcher = require('../packages/core/src/idle-watcher');
      
      bestModel.refreshAll().then(() => {
      }).catch(() => {
      });
      
      const iwResult = idleWatcher.start({ pollInterval: 10000 });
      
      const modeFile = path.join(defaults.STATE_DIR, 'opencode-mode');
      fs.writeFileSync(modeFile, JSON.stringify({
        mode: 'opencode',
        startedAt: new Date().toISOString(),
        version: defaults.VERSION,
        freeModels: 'https://github.com/anthropics/free-coding-models'
      }, null, 2));
      
      return {
        success: true,
        mode: 'opencode',
        message: 'Frugality started for OpenCode - using free-tier models',
        idleWatcher: iwResult,
        skillPath: 'OPENCODE.md',
        cacheDir: path.join(process.env.HOME || '/home/user', '.frugality/cache'),
        opencodeDir: path.join(process.env.HOME || '/home/user', '.opencode'),
        instructions: 'Place OPENCODE.md in your project root for OpenCode to read'
      };
    },

    startLight: (opts, flags) => {
      ensureDirs();
      
      const modeFile = path.join(defaults.STATE_DIR, 'agentic-mode');
      fs.writeFileSync(modeFile, JSON.stringify({
        mode: 'light',
        startedAt: new Date().toISOString(),
        version: defaults.VERSION
      }, null, 2));
      
      return {
        success: true,
        mode: 'light',
        message: 'Frugality started in light mode (minimal)'
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

    opencode: (opts, flags) => {
      const action = opts[0] || 'status';
      
      switch (action) {
        case 'status':
          return frug.commands.opencodeStatus(flags);
        case 'refresh':
          return frug.commands.opencodeRefresh(flags);
        case 'models':
          return frug.commands.opencodeModels(flags);
        case 'init':
          return frug.commands.opencodeInit(flags);
        default:
          return { error: `Unknown opencode action: ${action}` };
      }
    },

    opencodeStatus: (flags) => {
      const modeFile = path.join(defaults.STATE_DIR, 'opencode-mode');
      let mode = { mode: 'stopped' };
      
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
      
      const opencodeDir = path.join(process.env.HOME || '/home/user', '.opencode');
      const opencodeExists = fs.existsSync(opencodeDir);
      
      return {
        version: defaults.VERSION,
        mode: mode.mode,
        startedAt: mode.startedAt,
        cacheFiles,
        opencodeInstalled: opencodeExists,
        opencodeDir,
        freeModelsUrl: 'https://github.com/anthropics/free-coding-models'
      };
    },

    opencodeRefresh: (flags) => {
      const bestModel = require('../packages/core/src/best-model');
      
      bestModel.refreshAll().then(result => {
        return { success: true, refreshed: true, result };
      }).catch(err => {
        return { success: false, error: err.message };
      });
      
      return { success: true, message: 'Model cache refresh initiated for OpenCode' };
    },

    opencodeModels: (flags) => {
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

    opencodeInit: (flags) => {
      const opencodeDir = path.join(process.env.HOME || '/home/user', '.opencode');
      
      if (!fs.existsSync(opencodeDir)) {
        fs.mkdirSync(opencodeDir, { recursive: true });
      }
      
      const presetsDir = path.join(opencodeDir, 'presets');
      if (!fs.existsSync(presetsDir)) {
        fs.mkdirSync(presetsDir, { recursive: true });
      }
      
      return {
        success: true,
        message: 'OpenCode directories initialized',
        opencodeDir,
        presetsDir
      };
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

    stop: (opts, flags) => {
      const watchdog = require('../packages/watchdog/src/watchdog');
      const idleWatcher = require('../packages/core/src/idle-watcher');
      
      const wdResult = watchdog.stop();
      const iwResult = idleWatcher.stop();
      
      const agenticModeFile = path.join(defaults.STATE_DIR, 'agentic-mode');
      const opencodeModeFile = path.join(defaults.STATE_DIR, 'opencode-mode');
      
      if (fs.existsSync(agenticModeFile)) {
        fs.unlinkSync(agenticModeFile);
      }
      if (fs.existsSync(opencodeModeFile)) {
        fs.unlinkSync(opencodeModeFile);
      }
      
      return {
        success: true,
        message: 'Frugality stopped',
        watchdog: wdResult,
        idleWatcher: iwResult
      };
    },

    status: (opts, flags) => {
      const watchdog = require('../packages/watchdog/src/watchdog');
      const idleWatcher = require('../packages/core/src/idle-watcher');
      
      const wdStatus = watchdog.status();
      const iwRunning = idleWatcher.isRunning();
      
      let mode = 'proxy';
      
      const agenticModeFile = path.join(defaults.STATE_DIR, 'agentic-mode');
      const opencodeModeFile = path.join(defaults.STATE_DIR, 'opencode-mode');
      
      if (fs.existsSync(agenticModeFile)) {
        try {
          mode = JSON.parse(fs.readFileSync(agenticModeFile, 'utf8')).mode || 'proxy';
        } catch (e) {
          mode = 'unknown';
        }
      } else if (fs.existsSync(opencodeModeFile)) {
        try {
          mode = JSON.parse(fs.readFileSync(opencodeModeFile, 'utf8')).mode || 'opencode';
        } catch (e) {
          mode = 'unknown';
        }
      }
      
      const result = {
        version: defaults.VERSION,
        mode,
        watchdog: wdStatus,
        idleWatcher: { running: iwRunning }
      };
      
      if (flags.verbose || flags.v) {
        printStatus(result);
        return null;
      }
      
      return result;
    },

    update: (opts, flags) => {
      const bestModel = require('../packages/core/src/best-model');
      
      const isAgentic = flags.agentic || flags.a;
      
      if (isAgentic) {
        bestModel.refreshAll().then(result => {
        }).catch(err => {
        });
        return {
          success: true,
          mode: 'agentic',
          message: 'Agentic mode: Model cache refreshed'
        };
      }
      
      bestModel.refreshAll().then(result => {
      });
      
      return {
        success: true,
        mode: 'proxy',
        message: 'Update initiated'
      };
    },

    config: (opts, flags) => {
      const config = require('../packages/core/src/config');
      const action = opts[0];
      
      switch (action) {
        case 'show':
        case 'get':
          const key = opts[1];
          return config.load();
        case 'set':
          if (opts[1] && opts[2]) {
            return config.set(opts[1], opts[2]);
          }
          return { error: 'Usage: config set <key> <value>' };
        case 'reset':
          return config.reset();
        case 'path':
          return { path: config.getPath() };
        default:
          return {
            path: config.getPath(),
            exists: config.exists(),
            commands: ['show', 'set', 'reset', 'path']
          };
      }
    },

    doctor: (opts, flags) => {
      const issues = [];
      const warnings = [];
      
      const dirs = [
        path.join(process.env.HOME || '/home/user', '.frugality'),
        path.join(process.env.HOME || '/home/user', '.claude-code-router'),
        path.join(process.env.HOME || '/home/user', '.opencode'),
      ];
      
      for (const dir of dirs) {
        if (!fs.existsSync(dir)) {
          warnings.push(`Missing directory: ${dir} (will be created on first run)`);
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
      return { 
        version: defaults.VERSION,
        name: 'Frugality',
        tagline: 'Cost-Optimized AI Development'
      };
    },

    help: () => {
      return {
        version: defaults.VERSION,
        tagline: 'Cost-Optimized AI Development',
        commands: [
          { cmd: 'start', desc: 'Start proxy mode (Claude Code)', alias: '' },
          { cmd: 'start --opencode', desc: 'Start for OpenCode', alias: 'frug-open' },
          { cmd: 'start --agentic', desc: 'Start agentic mode (Claude Code)', alias: 'frug-now' },
          { cmd: 'start --light', desc: 'Start light mode (minimal)', alias: '' },
          { cmd: 'agent status', desc: 'Show agentic mode status', alias: '' },
          { cmd: 'agent models', desc: 'List cached models', alias: '' },
          { cmd: 'agent refresh', desc: 'Refresh model cache', alias: '' },
          { cmd: 'stop', desc: 'Stop the system', alias: '' },
          { cmd: 'status', desc: 'Show system status', alias: '' },
          { cmd: 'update', desc: 'Update models', alias: '' },
          { cmd: 'update --opencode', desc: 'Update models for OpenCode', alias: '' },
          { cmd: 'update --agentic', desc: 'Update agentic cache', alias: '' },
          { cmd: 'doctor', desc: 'Diagnose issues', alias: '' },
          { cmd: 'config', desc: 'Manage configuration', alias: '' },
          { cmd: 'interactive', desc: 'Interactive mode', alias: 'i' },
          { cmd: 'version', desc: 'Show version', alias: '' },
          { cmd: 'help', desc: 'Show this help', alias: '' }
        ]
      };
    }
  }
};

if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.includes('--help') || args.includes('-h')) {
    printHelp();
    process.exit(0);
  }
  
  Promise.resolve(frug.run(args)).then(result => {
    if (result && typeof result === 'object') {
      console.log(JSON.stringify(result, null, 2));
    }
  }).catch(err => {
    console.error(format.error(err.message));
    process.exit(1);
  });
}

module.exports = frug;
