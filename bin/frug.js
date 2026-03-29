#!/usr/bin/env node

'use strict';

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const VERSION = '0.3.0';

// Read HOME dynamically so tests can override process.env.HOME before calling.
const getHome = () => process.env.HOME || '/home/user';

const defaults = {
  get STATE_DIR()        { return path.join(getHome(), '.frugality/state'); },
  get PID_WATCHDOG()     { return path.join(getHome(), '.frugality/watchdog.pid'); },
  get PID_IDLE_WATCHER() { return path.join(getHome(), '.frugality/idle-watcher.pid'); },
  VERSION
};

// ---------------------------------------------------------------------------
// Terminal colours
// ---------------------------------------------------------------------------

const c = {
  reset:   '\x1b[0m',
  red:     '\x1b[31m',
  green:   '\x1b[32m',
  yellow:  '\x1b[33m',
  blue:    '\x1b[34m',
  cyan:    '\x1b[36m',
  magenta: '\x1b[35m',
  gray:    '\x1b[90m',
  bold:    '\x1b[1m',
  dim:     '\x1b[2m'
};

const fmt = {
  success: (msg) => `${c.green}✓${c.reset} ${msg}`,
  error:   (msg) => `${c.red}✗${c.reset} ${msg}`,
  warn:    (msg) => `${c.yellow}⚠${c.reset} ${msg}`,
  info:    (msg) => `${c.blue}ℹ${c.reset} ${msg}`,
  header:  (msg) => `${c.cyan}${c.bold}${msg}${c.reset}`,
  dim:     (msg) => `${c.dim}${msg}${c.reset}`,
  section: (msg) => `\n${c.magenta}${msg}${c.reset}\n`
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ensureDirs = () => {
  if (!fs.existsSync(defaults.STATE_DIR)) {
    fs.mkdirSync(defaults.STATE_DIR, { recursive: true });
  }
};

const readModeFile = (filePath) => {
  if (!fs.existsSync(filePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (e) {
    return null;
  }
};

const parseArgs = (args) => {
  const result = { flags: {}, positional: [] };
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith('--')) {
      const flag = args[i].slice(2);
      if (args[i + 1] && !args[i + 1].startsWith('-')) {
        result.flags[flag] = args[i + 1];
        i++;
      } else {
        result.flags[flag] = true;
      }
    } else if (args[i].startsWith('-') && args[i].length === 2) {
      result.flags[args[i].slice(1)] = true;
    } else {
      result.positional.push(args[i]);
    }
  }
  return result;
};

const readCacheDir = () => {
  const cacheDir = path.join(getHome(), '.frugality/cache');
  if (!fs.existsSync(cacheDir)) return [];
  return fs.readdirSync(cacheDir).filter(f => f.endsWith('.txt'));
};

const readCacheModel = (file) => {
  const cacheDir = path.join(getHome(), '.frugality/cache');
  try {
    return fs.readFileSync(path.join(cacheDir, file), 'utf8').trim();
  } catch (e) {
    return '(unreadable)';
  }
};

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

const printBanner = () => {
  console.log(`${c.cyan}
  ____                    _
 |  _ \\  ___  ___ _ __ | |_
 | | | |/ _ \\/ __| '_ \\| __|
 | |_| |  __/\\__ \\ | | | |_
 |____/ \\___||___/_| |_|\\__|

 ${c.reset}${c.dim}Cost-Optimized AI Development v${VERSION}${c.reset}
  `);
};

const printStatus = (status) => {
  console.log(fmt.section('System Status'));
  const modeColor = { hybrid: c.magenta, agentic: c.cyan, opencode: c.green }[status.mode] || c.yellow;
  console.log(`${c.bold}Mode:${c.reset}         ${modeColor}${status.mode}${c.reset}`);
  console.log(`${c.bold}Version:${c.reset}      ${status.version}`);
  console.log(`${c.bold}Watchdog:${c.reset}     ${status.watchdog?.running ? c.green + 'Running' + c.reset : c.red + 'Stopped' + c.reset}`);
  console.log(`${c.bold}Idle Watcher:${c.reset} ${status.idleWatcher?.running ? c.green + 'Running' + c.reset : c.red + 'Stopped' + c.reset}`);

  if (status.mode === 'hybrid' && status.hybridConfig) {
    const hc = status.hybridConfig;
    console.log(`\n${c.bold}Hybrid Config:${c.reset}`);
    console.log(`  Main model:      ${c.cyan}${hc.main?.model || 'unknown'}${c.reset}`);
    console.log(`  Agent (fast):    ${hc.agents?.fast || 'unknown'}`);
    console.log(`  Agent (analysis):${hc.agents?.analysis || 'unknown'}`);
    console.log(`  Agent (reasoning):${hc.agents?.reasoning || 'unknown'}`);
  }

  const cacheFiles = readCacheDir();
  if (cacheFiles.length > 0) {
    console.log(fmt.dim(`\nCached models (${cacheFiles.length}):`));
    for (const file of cacheFiles) {
      console.log(`  ${c.gray}${file.replace('.txt', '')}:${c.reset} ${readCacheModel(file)}`);
    }
  }
};

const printHelp = () => {
  printBanner();
  console.log(fmt.section('Commands'));

  const cmds = [
    ['start',                  'Start fully-free mode (proxy, no CCR required by default)'],
    ['start --agentic',        'Claude Code agentic mode (free models for all agents)'],
    ['start --opencode',       'OpenCode fully-free mode'],
    ['start --hybrid',         'Hybrid: subscription main + free-model agents (Claude Code)'],
    ['start --opencode --hybrid', 'Hybrid: subscription main + free-model agents (OpenCode)'],
    ['start --light',          'Light mode (minimal — no watchdog)'],
    ['stop',                   'Stop all Frugality processes'],
    ['status',                 'Show system status'],
    ['status --verbose',       'Show status + cached models'],
    ['init --hybrid',          'Write HYBRID.md to current project'],
    ['init --opencode',        'Write OPENCODE.md to current project'],
    ['agent status',           'Agentic mode details'],
    ['agent models',           'List cached models'],
    ['agent refresh',          'Refresh model cache'],
    ['update',                 'Refresh model cache'],
    ['doctor',                 'Diagnose and auto-fix issues'],
    ['config show',            'Show configuration'],
    ['config set <key> <val>', 'Set a configuration value'],
    ['config reset',           'Reset to defaults'],
    ['interactive',            'Interactive REPL (alias: i)'],
    ['version',                'Show version'],
    ['help',                   'Show this help']
  ];

  for (const [cmd, desc] of cmds) {
    console.log(`  ${c.green}${cmd.padEnd(30)}${c.reset} ${desc}`);
  }

  console.log();
  console.log(fmt.dim('Quick aliases:  frug-now = start --agentic  |  frug-open = start --opencode'));
};

// ---------------------------------------------------------------------------
// Interactive mode
// ---------------------------------------------------------------------------

const runInteractive = () => {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

  const prompt = () => {
    rl.question(`${c.cyan}frugality>${c.reset} `, async (input) => {
      const args = input.trim().split(/\s+/);
      if (args[0] === 'exit' || args[0] === 'quit') {
        rl.close();
        return;
      }
      if (args[0]) {
        try {
          const result = await frug.run(args);
          if (result && typeof result === 'object') {
            if (result.success === false) {
              console.log(fmt.error(result.message || result.error || 'Command failed'));
            } else if (result.message) {
              console.log(fmt.success(result.message));
            }
          }
        } catch (e) {
          console.log(fmt.error(e.message));
        }
      }
      prompt();
    });
  };

  printBanner();
  console.log(fmt.info('Type "help" for commands, "exit" to quit\n'));
  prompt();
};

// ---------------------------------------------------------------------------
// Command implementations
// ---------------------------------------------------------------------------

const commands = {

  // ── start ────────────────────────────────────────────────────────────────

  start: async (opts, flags) => {
    ensureDirs();

    const isHybrid   = flags.hybrid   || flags.H;
    const isAgentic  = flags.agentic  || flags.a;
    const isOpenCode = flags.opencode || flags.o;
    const isLight    = flags.light    || flags.l;

    if (isHybrid && isOpenCode) return commands.startHybrid(opts, { ...flags, platform: 'opencode' });
    if (isHybrid)               return commands.startHybrid(opts, flags);
    if (isOpenCode)             return commands.startOpenCode(opts, flags);
    if (isAgentic)              return commands.startAgentic(opts, flags);
    if (isLight)                return commands.startLight(opts, flags);

    return commands.startProxy(opts, flags);
  },

  startProxy: (opts, flags) => {
    const watchdog    = require('../packages/watchdog/src/watchdog');
    const idleWatcher = require('../packages/core/src/idle-watcher');

    const wdResult = watchdog.start({ interval: 300000 });
    const iwResult = idleWatcher.start({ pollInterval: 10000 });

    return {
      success: true,
      mode: 'proxy',
      message: 'Frugality started in proxy mode (CCR health monitoring enabled)',
      watchdog: wdResult,
      idleWatcher: iwResult
    };
  },

  startAgentic: async (opts, flags) => {
    ensureDirs();

    const bestModel   = require('../packages/core/src/best-model');
    const idleWatcher = require('../packages/core/src/idle-watcher');

    try {
      await bestModel.refreshAll();
    } catch (err) {
      console.error(fmt.warn(`Model cache refresh failed: ${err.message}`));
    }

    const iwResult = idleWatcher.start({ pollInterval: 10000 });

    fs.writeFileSync(
      path.join(defaults.STATE_DIR, 'agentic-mode'),
      JSON.stringify({ mode: 'agentic', startedAt: new Date().toISOString(), version: VERSION }, null, 2)
    );

    return {
      success: true,
      mode: 'agentic',
      message: 'Frugality started in agentic mode — all agents use free-tier models',
      idleWatcher: iwResult,
      skillPath: path.resolve(__dirname, '../packages/skill/SKILL.md'),
      cacheDir: path.join(getHome(), '.frugality/cache')
    };
  },

  startOpenCode: async (opts, flags) => {
    ensureDirs();

    const bestModel   = require('../packages/core/src/best-model');
    const idleWatcher = require('../packages/core/src/idle-watcher');

    try {
      await bestModel.refreshAll();
    } catch (err) {
      console.error(fmt.warn(`Model cache refresh failed: ${err.message}`));
    }

    const iwResult = idleWatcher.start({ pollInterval: 10000 });

    fs.writeFileSync(
      path.join(defaults.STATE_DIR, 'opencode-mode'),
      JSON.stringify({
        mode: 'opencode',
        startedAt: new Date().toISOString(),
        version: VERSION,
        freeModels: 'https://github.com/anthropics/free-coding-models'
      }, null, 2)
    );

    return {
      success: true,
      mode: 'opencode',
      message: 'Frugality started for OpenCode — all agents use free-tier models',
      idleWatcher: iwResult,
      skillPath: path.resolve(__dirname, '../OPENCODE.md'),
      cacheDir: path.join(getHome(), '.frugality/cache'),
      opencodeDir: path.join(getHome(), '.opencode'),
      instructions: 'Place OPENCODE.md in your project root for OpenCode to read'
    };
  },

  startHybrid: async (opts, flags) => {
    ensureDirs();

    const bestModel   = require('../packages/core/src/best-model');
    const hybridMod   = require('../packages/core/src/hybrid');
    const idleWatcher = require('../packages/core/src/idle-watcher');

    // Refresh free-model cache so agent routing is current
    try {
      await bestModel.refreshAll();
    } catch (err) {
      console.error(fmt.warn(`Model cache refresh failed: ${err.message}`));
    }

    const iwResult = idleWatcher.start({ pollInterval: 10000 });

    const platform  = flags.platform || (flags.opencode ? 'opencode' : 'claude-code');
    const mainModel = hybridMod.getMainModel();
    const state     = hybridMod.writeHybridState({ version: VERSION });

    // Write HYBRID.md to cwd if it doesn't already exist
    const hybridMdPath = path.join(process.cwd(), 'HYBRID.md');
    if (!fs.existsSync(hybridMdPath)) {
      try {
        hybridMod.writeTemplate(hybridMdPath);
      } catch (err) {
        console.error(fmt.warn(`Could not write HYBRID.md: ${err.message}`));
      }
    }

    return {
      success: true,
      mode: 'hybrid',
      platform,
      mainModel,
      message: `Frugality started in hybrid mode — main: ${mainModel}, agents: free-tier`,
      idleWatcher: iwResult,
      hybridConfig: state,
      hybridMdPath,
      cacheDir: path.join(getHome(), '.frugality/cache')
    };
  },

  startLight: (opts, flags) => {
    ensureDirs();

    fs.writeFileSync(
      path.join(defaults.STATE_DIR, 'agentic-mode'),
      JSON.stringify({ mode: 'light', startedAt: new Date().toISOString(), version: VERSION }, null, 2)
    );

    return {
      success: true,
      mode: 'light',
      message: 'Frugality started in light mode (no watchdog)'
    };
  },

  // ── stop ─────────────────────────────────────────────────────────────────

  stop: (opts, flags) => {
    const watchdog    = require('../packages/watchdog/src/watchdog');
    const idleWatcher = require('../packages/core/src/idle-watcher');

    const wdResult = watchdog.stop();
    const iwResult = idleWatcher.stop();

    // Clear all mode state files
    const modeFiles = ['agentic-mode', 'opencode-mode', 'hybrid-mode'];
    for (const f of modeFiles) {
      const fp = path.join(defaults.STATE_DIR, f);
      if (fs.existsSync(fp)) fs.unlinkSync(fp);
    }

    return {
      success: true,
      message: 'Frugality stopped',
      watchdog: wdResult,
      idleWatcher: iwResult
    };
  },

  // ── status ───────────────────────────────────────────────────────────────

  status: (opts, flags) => {
    const watchdog    = require('../packages/watchdog/src/watchdog');
    const idleWatcher = require('../packages/core/src/idle-watcher');

    const wdStatus  = watchdog.status();
    const iwRunning = idleWatcher.isRunning();

    // Determine active mode by inspecting state files (hybrid takes precedence)
    const hybridData   = readModeFile(path.join(defaults.STATE_DIR, 'hybrid-mode'));
    const agenticData  = readModeFile(path.join(defaults.STATE_DIR, 'agentic-mode'));
    const opencodeData = readModeFile(path.join(defaults.STATE_DIR, 'opencode-mode'));

    let mode = 'proxy';
    let modeData = null;

    if (hybridData)   { mode = 'hybrid';   modeData = hybridData;   }
    else if (agenticData)  { mode = agenticData.mode || 'agentic'; modeData = agenticData; }
    else if (opencodeData) { mode = 'opencode'; modeData = opencodeData; }

    const result = {
      version: VERSION,
      mode,
      startedAt: modeData?.startedAt || null,
      watchdog: wdStatus,
      idleWatcher: { running: iwRunning },
      hybridConfig: hybridData ? hybridData : undefined,
      cacheFiles: readCacheDir()
    };

    if (flags.verbose || flags.v) {
      printStatus(result);
      return null;
    }

    return result;
  },

  // ── init ─────────────────────────────────────────────────────────────────

  init: async (opts, flags) => {
    ensureDirs();

    const isHybrid   = flags.hybrid   || flags.H;
    const isOpenCode = flags.opencode || flags.o;
    const force      = flags.force    || flags.f;

    if (isHybrid)   return commands.initHybrid(flags);
    if (isOpenCode) return commands.initOpenCode(flags);
    return commands.initFree(flags);
  },

  initHybrid: (flags) => {
    const hybridMod    = require('../packages/core/src/hybrid');
    const bestModel    = require('../packages/core/src/best-model');
    const templatePath = path.join(process.cwd(), 'HYBRID.md');
    const force        = flags.force || flags.f;

    if (fs.existsSync(templatePath) && !force) {
      return {
        success: false,
        message: `HYBRID.md already exists. Use --force to overwrite.`,
        path: templatePath
      };
    }

    // Attempt a cache refresh so the template shows real model names
    bestModel.refreshAll().catch(() => {});

    hybridMod.writeTemplate(templatePath);
    hybridMod.writeHybridState({ version: VERSION });

    return {
      success: true,
      message: 'Hybrid mode initialised',
      templatePath,
      mainModel: hybridMod.getMainModel(),
      instructions: [
        'HYBRID.md written to your project root.',
        'Claude Code will read it automatically on session start.',
        'Run "frug start --hybrid" to activate.'
      ]
    };
  },

  initOpenCode: (flags) => {
    const templateSrc  = path.resolve(__dirname, '../OPENCODE.md');
    const templateDest = path.join(process.cwd(), 'OPENCODE.md');
    const force        = flags.force || flags.f;

    if (fs.existsSync(templateDest) && !force) {
      return {
        success: false,
        message: `OPENCODE.md already exists. Use --force to overwrite.`,
        path: templateDest
      };
    }

    if (fs.existsSync(templateSrc)) {
      fs.copyFileSync(templateSrc, templateDest);
    }

    return {
      success: true,
      message: 'OpenCode mode initialised',
      templatePath: templateDest,
      instructions: 'OPENCODE.md written to your project root. Run "frug start --opencode" to activate.'
    };
  },

  initFree: (flags) => {
    ensureDirs();
    const bestModel = require('../packages/core/src/best-model');
    bestModel.refreshAll().catch(() => {});
    return {
      success: true,
      message: 'Fully-free mode initialised — model cache warming up',
      cacheDir: path.join(getHome(), '.frugality/cache')
    };
  },

  // ── agent sub-commands ───────────────────────────────────────────────────

  agent: (opts, flags) => {
    const action = opts[0] || 'status';
    switch (action) {
      case 'status':  return commands.agentStatus(flags);
      case 'refresh': return commands.agentRefresh(flags);
      case 'models':  return commands.agentModels(flags);
      default:        return { success: false, error: `Unknown agent action: ${action}` };
    }
  },

  agentStatus: (flags) => {
    const modeData   = readModeFile(path.join(defaults.STATE_DIR, 'agentic-mode'));
    const cacheFiles = readCacheDir();

    return {
      version: VERSION,
      mode: modeData?.mode || 'proxy',
      startedAt: modeData?.startedAt || null,
      cacheFiles,
      skillActive: fs.existsSync(path.resolve(__dirname, '../packages/skill/SKILL.md'))
    };
  },

  agentRefresh: async (flags) => {
    const bestModel = require('../packages/core/src/best-model');
    try {
      const result = await bestModel.refreshAll();
      return { success: true, message: 'Model cache refreshed', ...result };
    } catch (err) {
      return { success: false, error: err.message };
    }
  },

  agentModels: (flags) => {
    const cacheDir = path.join(getHome(), '.frugality/cache');
    const models = {};
    if (fs.existsSync(cacheDir)) {
      for (const file of fs.readdirSync(cacheDir).filter(f => f.endsWith('.txt'))) {
        models[file.replace('.txt', '')] = readCacheModel(file);
      }
    }
    return { models };
  },

  // ── opencode sub-commands ────────────────────────────────────────────────

  opencode: (opts, flags) => {
    const action = opts[0] || 'status';
    switch (action) {
      case 'status':  return commands.opencodeStatus(flags);
      case 'refresh': return commands.opencodeRefresh(flags);
      case 'models':  return commands.opencodeModels(flags);
      case 'init':    return commands.opencodeInit(flags);
      default:        return { success: false, error: `Unknown opencode action: ${action}` };
    }
  },

  opencodeStatus: (flags) => {
    const modeData   = readModeFile(path.join(defaults.STATE_DIR, 'opencode-mode'));
    const cacheFiles = readCacheDir();
    const opencodeDir = path.join(getHome(), '.opencode');

    return {
      version: VERSION,
      mode: modeData?.mode || 'stopped',
      startedAt: modeData?.startedAt || null,
      cacheFiles,
      opencodeInstalled: fs.existsSync(opencodeDir),
      opencodeDir,
      freeModelsUrl: 'https://github.com/anthropics/free-coding-models'
    };
  },

  opencodeRefresh: async (flags) => {
    const bestModel = require('../packages/core/src/best-model');
    try {
      const result = await bestModel.refreshAll();
      return { success: true, message: 'Model cache refreshed for OpenCode', ...result };
    } catch (err) {
      return { success: false, error: err.message };
    }
  },

  opencodeModels: (flags) => {
    return commands.agentModels(flags);
  },

  opencodeInit: (flags) => {
    const opencodeDir = path.join(getHome(), '.opencode');
    const presetsDir  = path.join(opencodeDir, 'presets');

    if (!fs.existsSync(opencodeDir)) fs.mkdirSync(opencodeDir, { recursive: true });
    if (!fs.existsSync(presetsDir))  fs.mkdirSync(presetsDir,  { recursive: true });

    return {
      success: true,
      message: 'OpenCode directories initialised',
      opencodeDir,
      presetsDir
    };
  },

  // ── hybrid sub-commands ───────────────────────────────────────────────────

  hybrid: (opts, flags) => {
    const action = opts[0] || 'status';
    switch (action) {
      case 'status':   return commands.hybridStatus(flags);
      case 'config':   return commands.hybridConfig(flags);
      case 'template': return commands.hybridTemplate(flags);
      default:         return { success: false, error: `Unknown hybrid action: ${action}` };
    }
  },

  hybridStatus: (flags) => {
    const hybridMod  = require('../packages/core/src/hybrid');
    const state      = hybridMod.readHybridState();
    const cacheFiles = readCacheDir();

    return {
      version: VERSION,
      active: hybridMod.isHybridMode(),
      state: state || { mode: 'not started' },
      cacheFiles
    };
  },

  hybridConfig: (flags) => {
    const hybridMod = require('../packages/core/src/hybrid');
    return { success: true, config: hybridMod.buildHybridConfig() };
  },

  hybridTemplate: (flags) => {
    const hybridMod    = require('../packages/core/src/hybrid');
    const templatePath = path.join(process.cwd(), 'HYBRID.md');
    const force        = flags.force || flags.f;

    if (fs.existsSync(templatePath) && !force) {
      return {
        success: false,
        message: 'HYBRID.md already exists. Use --force to overwrite.',
        path: templatePath
      };
    }

    hybridMod.writeTemplate(templatePath);
    return { success: true, message: 'HYBRID.md written', path: templatePath };
  },

  // ── update ───────────────────────────────────────────────────────────────

  update: async (opts, flags) => {
    const bestModel = require('../packages/core/src/best-model');
    try {
      const result = await bestModel.refreshAll();
      return { success: true, message: 'Model cache refreshed', ...result };
    } catch (err) {
      return { success: false, error: err.message };
    }
  },

  // ── config ───────────────────────────────────────────────────────────────

  config: (opts, flags) => {
    const configMod = require('../packages/core/src/config');
    const action    = opts[0];

    switch (action) {
      case 'show':
      case 'get':
        return configMod.load();

      case 'set':
        if (opts[1] && opts[2] !== undefined) {
          return configMod.set(opts[1], opts[2]);
        }
        return { success: false, error: 'Usage: config set <key> <value>' };

      case 'reset':
        return configMod.reset();

      case 'path':
        return { path: configMod.getPath() };

      default:
        return {
          path: configMod.getPath(),
          exists: configMod.exists(),
          commands: ['show', 'set <key> <val>', 'reset', 'path']
        };
    }
  },

  // ── doctor ───────────────────────────────────────────────────────────────

  doctor: (opts, flags) => {
    const issues   = [];
    const warnings = [];
    const fixed    = [];

    const dirs = [
      path.join(getHome(), '.frugality'),
      path.join(getHome(), '.frugality/cache'),
      path.join(getHome(), '.frugality/state'),
      path.join(getHome(), '.frugality/logs'),
      path.join(getHome(), '.opencode')
    ];

    for (const dir of dirs) {
      if (!fs.existsSync(dir)) {
        try {
          fs.mkdirSync(dir, { recursive: true });
          fixed.push(`Created missing directory: ${dir}`);
        } catch (e) {
          issues.push(`Cannot create directory ${dir}: ${e.message}`);
        }
      }
    }

    // Check and clean stale PID files
    const pidFiles = [defaults.PID_WATCHDOG, defaults.PID_IDLE_WATCHER];
    for (const pidFile of pidFiles) {
      if (fs.existsSync(pidFile)) {
        try {
          const pid = parseInt(fs.readFileSync(pidFile, 'utf8').trim(), 10);
          if (!pid || isNaN(pid)) {
            issues.push(`Invalid PID in ${pidFile}`);
          } else {
            try {
              process.kill(pid, 0);
            } catch (e) {
              // Process not running → stale PID file
              fs.unlinkSync(pidFile);
              fixed.push(`Removed stale PID file: ${pidFile}`);
            }
          }
        } catch (e) {
          issues.push(`Cannot read PID file ${pidFile}: ${e.message}`);
        }
      }
    }

    return {
      success: issues.length === 0,
      issues,
      warnings,
      fixed,
      message: issues.length === 0
        ? `All checks passed${fixed.length ? ` (${fixed.length} issues auto-fixed)` : ''}`
        : `${issues.length} issue(s) found`
    };
  },

  // ── version / help ───────────────────────────────────────────────────────

  version: () => ({
    version: VERSION,
    name: 'Frugality',
    tagline: 'Cost-Optimized AI Development'
  }),

  help: () => ({
    version: VERSION,
    tagline: 'Cost-Optimized AI Development',
    commands: [
      { cmd: 'start',                     desc: 'Start proxy mode' },
      { cmd: 'start --agentic',           desc: 'Agentic mode — free models for all agents' },
      { cmd: 'start --opencode',          desc: 'OpenCode fully-free mode', alias: 'frug-open' },
      { cmd: 'start --hybrid',            desc: 'Hybrid: subscription + free agents', alias: 'frug-hybrid' },
      { cmd: 'start --opencode --hybrid', desc: 'OpenCode hybrid mode' },
      { cmd: 'start --light',             desc: 'Light mode — no watchdog' },
      { cmd: 'stop',                      desc: 'Stop all processes' },
      { cmd: 'status',                    desc: 'Show status' },
      { cmd: 'status --verbose',          desc: 'Show status + cached model list' },
      { cmd: 'init --hybrid',             desc: 'Write HYBRID.md to current project' },
      { cmd: 'init --opencode',           desc: 'Write OPENCODE.md to current project' },
      { cmd: 'agent status',              desc: 'Show agentic mode details' },
      { cmd: 'agent models',              desc: 'List cached models' },
      { cmd: 'agent refresh',             desc: 'Refresh model cache' },
      { cmd: 'hybrid status',             desc: 'Show hybrid mode details' },
      { cmd: 'hybrid config',             desc: 'Show hybrid routing config' },
      { cmd: 'update',                    desc: 'Refresh model cache' },
      { cmd: 'doctor',                    desc: 'Diagnose + auto-fix issues' },
      { cmd: 'config show',               desc: 'Show config file' },
      { cmd: 'config set <key> <val>',    desc: 'Set config value' },
      { cmd: 'config reset',              desc: 'Reset to defaults' },
      { cmd: 'interactive',               desc: 'Interactive REPL', alias: 'i' },
      { cmd: 'version',                   desc: 'Show version' },
      { cmd: 'help',                      desc: 'Show this help' }
    ]
  })
};

// ---------------------------------------------------------------------------
// Main dispatcher
// ---------------------------------------------------------------------------

const frug = {
  run: async (args) => {
    const parsed  = parseArgs(args);
    const command = parsed.positional[0] || 'help';

    switch (command) {
      case 'start':       return commands.start(parsed.positional.slice(1), parsed.flags);
      case 'stop':        return commands.stop(parsed.positional.slice(1), parsed.flags);
      case 'status':      return commands.status(parsed.positional.slice(1), parsed.flags);
      case 'init':        return commands.init(parsed.positional.slice(1), parsed.flags);
      case 'update':      return commands.update(parsed.positional.slice(1), parsed.flags);
      case 'agent':       return commands.agent(parsed.positional.slice(1), parsed.flags);
      case 'opencode':    return commands.opencode(parsed.positional.slice(1), parsed.flags);
      case 'hybrid':      return commands.hybrid(parsed.positional.slice(1), parsed.flags);
      case 'doctor':      return commands.doctor(parsed.positional.slice(1), parsed.flags);
      case 'config':      return commands.config(parsed.positional.slice(1), parsed.flags);
      case 'interactive':
      case 'i':           runInteractive(); return { mode: 'interactive' };
      case 'version':     return commands.version();
      case 'help':
      default:            return commands.help();
    }
  },

  commands  // exported for testing
};

// ---------------------------------------------------------------------------
// CLI entry point
// ---------------------------------------------------------------------------

if (require.main === module) {
  const args = process.argv.slice(2);

  if (args.includes('--help') || args.includes('-h')) {
    printHelp();
    process.exit(0);
  }

  Promise.resolve(frug.run(args))
    .then(result => {
      if (result && typeof result === 'object') {
        console.log(JSON.stringify(result, null, 2));
      }
    })
    .catch(err => {
      console.error(fmt.error(err.message));
      process.exit(1);
    });
}

module.exports = frug;
