#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const defaults = require('../config/defaults');
const bestModel = require('../packages/core/src/best-model');
const bridge = require('../packages/core/src/bridge');
const safeRestart = require('../packages/core/src/safe-restart');
const idleWatcher = require('../packages/core/src/idle-watcher');
const watchdog = require('../packages/watchdog/src/watchdog');

const args = process.argv.slice(2);
const command = args[0] || 'help';
const flags = args.slice(1);

const commands = {
  async start(opts) {
    console.log(`[frug] Starting frugality v${defaults.VERSION}...`);
    
    // Check all dependencies
    const deps = ['free-coding-models', 'ccr', 'jq', 'curl'];
    for (const dep of deps) {
      try {
        execSync(`which ${dep} > /dev/null 2>&1`);
      } catch (err) {
        console.error(`❌ Missing: ${dep}`);
        process.exit(1);
      }
    }

    // Ensure directories
    [defaults.STATE_DIR, defaults.LOG_DIR, defaults.CACHE_DIR].forEach(dir => {
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    });

    // Run bridge to select models
    try {
      const result = await bridge.runBridge({ immediate: true });
      console.log('✓ Models selected and applied');
    } catch (err) {
      console.error(`⚠ Bridge failed: ${err.message}`);
    }

    // Start daemons
    if (!opts.includes('--no-watchdog')) {
      watchdog.start();
      console.log(`✓ Watchdog started (PID ${process.pid})`);
    }

    if (!opts.includes('--no-idle-watcher')) {
      idleWatcher.start();
      console.log(`✓ Idle watcher started`);
    }

    // Install skill if needed
    const skillDir = path.join(process.cwd(), '.claude/skills/frugality-usage');
    if (!fs.existsSync(skillDir)) {
      fs.mkdirSync(skillDir, { recursive: true });
      const skillPath = path.join(__dirname, '../packages/skill/SKILL.md');
      if (fs.existsSync(skillPath)) {
        fs.copyFileSync(skillPath, path.join(skillDir, 'SKILL.md'));
        console.log('✓ Skill installed');
      }
    }

    console.log('\n✓ Frugality ready!');
    console.log('Next: ccr code');
  },

  async stop() {
    watchdog.stop();
    idleWatcher.stop();
    console.log('✓ Stopped watchdog and idle watcher');
  },

  async status() {
    const wd = watchdog.isRunning();
    const iw = idleWatcher.isRunning();
    const pending = safeRestart.hasPendingRestart();

    console.log(`\nfrugality v${defaults.VERSION}`);
    console.log(`Watchdog: ${wd ? '✓ running' : '✗ stopped'}`);
    console.log(`Idle watcher: ${iw ? '✓ running' : '✗ stopped'}`);
    console.log(`Pending restart: ${pending.pending ? `✓ ${pending.reason}` : '✗ no'}`);
    console.log();

    // Show cached models
    const tasks = ['default', 'fast', 'analysis', 'reasoning'];
    console.log('Cached models:');
    for (const task of tasks) {
      const cached = bestModel.readCache(task);
      console.log(`  ${task.padEnd(12)} ${cached || '(uncached)'}`);
    }
  },

  async update(opts) {
    const immediate = opts.includes('--immediate');
    const dryRun = opts.includes('--dry-run');

    try {
      const result = await bridge.runBridge({ immediate, dryRun });
      if (dryRun) {
        console.log(JSON.stringify(result.manifest, null, 2));
      } else {
        console.log(`✓ Update ${immediate ? 'applied' : 'staged'}`);
      }
    } catch (err) {
      console.error(`❌ Update failed: ${err.message}`);
      process.exit(1);
    }
  },

  async init() {
    [defaults.STATE_DIR, defaults.LOG_DIR, defaults.CACHE_DIR].forEach(dir => {
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    });

    // Install skill
    const skillDir = path.join(process.cwd(), '.claude/skills/frugality-usage');
    fs.mkdirSync(skillDir, { recursive: true });
    const skillPath = path.join(__dirname, '../packages/skill/SKILL.md');
    if (fs.existsSync(skillPath)) {
      fs.copyFileSync(skillPath, path.join(skillDir, 'SKILL.md'));
    }

    console.log('✓ Initialized frugality');
    console.log('✓ Directories created');
    console.log('✓ Skill installed');
    console.log('\nNext: frug start');
  },

  doctor() {
    console.log(`\nfrugality doctor v${defaults.VERSION}\n`);

    const checks = [];

    // Check binaries
    const binaries = ['free-coding-models', 'ccr', 'jq', 'curl'];
    for (const bin of binaries) {
      try {
        execSync(`which ${bin} > /dev/null 2>&1`);
        checks.push({ name: bin, pass: true });
      } catch (err) {
        checks.push({ name: bin, pass: false, error: 'not installed' });
      }
    }

    // Check files
    const files = [
      { path: defaults.FCM_JSON, name: 'Free Coding Models config' },
      { path: defaults.CCR_PRESETS_DIR, name: 'CCR presets directory' }
    ];
    
    for (const file of files) {
      const exists = fs.existsSync(file.path);
      checks.push({ name: file.name, pass: exists });
    }

    // Print results
    for (const check of checks) {
      const icon = check.pass ? '✓' : '✗';
      console.log(`${icon} ${check.name}${check.error ? ': ' + check.error : ''}`);
    }

    const failures = checks.filter(c => !c.pass).length;
    console.log(`\n${failures ? '❌ Issues found' : '✓ All checks passed'}\n`);
    
    process.exit(failures > 0 ? 1 : 0);
  },

  help() {
    console.log(`\nfrugality v${defaults.VERSION}
Claude Code. Free models. Zero compromise.

Usage: frug <command> [options]

Commands:
  start                 Start frugality (watchdog + idle watcher)
  stop                  Stop all services
  status                Show system status
  update [--immediate]  Refresh model cache
  init                  Initialize frugality in current project
  doctor                Diagnose system
  help                  Show this message

Examples:
  frug start
  frug update --immediate
  frug status
\n`);
  },

  version() {
    console.log(`frugality v${defaults.VERSION}`);
  }
};

// Main
(async () => {
  try {
    if (command === 'help' || command === '-h' || command === '--help') {
      commands.help();
    } else if (command === 'version' || command === '-v' || command === '--version') {
      commands.version();
    } else if (commands[command]) {
      await commands[command](flags);
    } else {
      console.error(`Unknown command: ${command}`);
      commands.help();
      process.exit(1);
    }
  } catch (err) {
    console.error(`Error: ${err.message}`);
    process.exit(1);
  }
})();
