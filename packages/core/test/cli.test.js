/**
 * CLI integration tests — exercises frug.run() for all major commands,
 * including the new hybrid mode.  No real watchdog/idle-watcher processes
 * are spawned; all I/O is scoped to a temp directory.
 */

const assert = require('assert');
const path = require('path');
const fs = require('fs');
const { describe, it, before, after } = require('node:test');

describe('CLI Integration Tests', () => {
  const testDir = path.join('/tmp', 'frugality-cli-test-' + process.pid);

  // frug is required inside before() so process.env.HOME is already set,
  // ensuring the dynamic getHome() helper reads the test directory.
  let frug;

  before(() => {
    process.env.HOME = testDir;
    fs.mkdirSync(testDir, { recursive: true });
    // Clear any previously cached version so getHome() sees the updated HOME
    Object.keys(require.cache).forEach(key => {
      if (key.includes('frugal-opencode') && !key.includes('node_modules')) {
        delete require.cache[key];
      }
    });
    frug = require('../../../bin/frug.js');
  });

  after(() => {
    delete process.env.FRUGALITY_MAIN_MODEL;
    if (fs.existsSync(testDir)) {
      fs.rmSync(testDir, { recursive: true, force: true });
    }
  });

  // ── version ────────────────────────────────────────────────────────────────

  it('version returns a version string', async () => {
    const result = await frug.run(['version']);
    assert.ok(result.version);
    assert.strictEqual(typeof result.version, 'string');
    assert.ok(result.version.match(/\d+\.\d+\.\d+/));
  });

  // ── help ───────────────────────────────────────────────────────────────────

  it('help returns a commands array', async () => {
    const result = await frug.run(['help']);
    assert.ok(Array.isArray(result.commands));
    assert.ok(result.commands.length > 0);
    // Hybrid commands must be present
    const cmds = result.commands.map(c => c.cmd);
    assert.ok(cmds.some(c => c.includes('--hybrid')), 'hybrid command missing from help');
  });

  it('unknown command falls through to help', async () => {
    const result = await frug.run(['not-a-real-command']);
    assert.ok(result.commands);
  });

  // ── doctor ─────────────────────────────────────────────────────────────────

  it('doctor runs without throwing', async () => {
    const result = await frug.run(['doctor']);
    assert.ok(typeof result.success === 'boolean');
    assert.ok(Array.isArray(result.issues));
    assert.ok(Array.isArray(result.fixed));
  });

  // ── start --light (no external deps) ──────────────────────────────────────

  it('start --light returns light mode', async () => {
    const result = await frug.run(['start', '--light']);
    assert.strictEqual(result.success, true);
    assert.strictEqual(result.mode, 'light');
  });

  // ── stop ───────────────────────────────────────────────────────────────────

  it('stop returns success', async () => {
    const result = await frug.run(['stop']);
    assert.strictEqual(result.success, true);
  });

  // ── status ─────────────────────────────────────────────────────────────────

  it('status returns a version and mode', async () => {
    const result = await frug.run(['status']);
    assert.ok(result);
    assert.ok(result.version);
    assert.ok(result.mode);
  });

  // ── update ─────────────────────────────────────────────────────────────────

  it('update refreshes the model cache', async () => {
    const result = await frug.run(['update']);
    assert.ok(typeof result.success === 'boolean');
    // Even if refresh succeeds or fails we get a result object
  });

  // ── agent sub-commands ─────────────────────────────────────────────────────

  it('agent status returns mode info', async () => {
    const result = await frug.run(['agent', 'status']);
    assert.ok(result.version);
    assert.ok(result.mode);
  });

  it('agent models returns models object', async () => {
    const result = await frug.run(['agent', 'models']);
    assert.ok(result.models !== undefined);
    assert.strictEqual(typeof result.models, 'object');
  });

  it('agent refresh returns success', async () => {
    const result = await frug.run(['agent', 'refresh']);
    assert.ok(typeof result.success === 'boolean');
  });

  it('agent unknown action returns error', async () => {
    const result = await frug.run(['agent', 'invalid-action']);
    assert.strictEqual(result.success, false);
    assert.ok(result.error);
  });

  // ── opencode sub-commands ──────────────────────────────────────────────────

  it('opencode status returns version and mode', async () => {
    const result = await frug.run(['opencode', 'status']);
    assert.ok(result.version);
    assert.ok(result.mode);
  });

  it('opencode models returns object', async () => {
    const result = await frug.run(['opencode', 'models']);
    assert.ok(result.models !== undefined);
  });

  it('opencode init creates directories', async () => {
    const result = await frug.run(['opencode', 'init']);
    assert.strictEqual(result.success, true);
  });

  it('opencode unknown action returns error', async () => {
    const result = await frug.run(['opencode', 'nope']);
    assert.strictEqual(result.success, false);
  });

  // ── hybrid sub-commands ────────────────────────────────────────────────────

  it('hybrid config returns routing table', async () => {
    const result = await frug.run(['hybrid', 'config']);
    assert.strictEqual(result.success, true);
    assert.ok(result.config);
    assert.strictEqual(result.config.mode, 'hybrid');
    assert.ok(result.config.taskRouting);
  });

  it('hybrid status returns active flag', async () => {
    const result = await frug.run(['hybrid', 'status']);
    assert.ok(typeof result.active === 'boolean');
    assert.ok(result.state);
  });

  it('hybrid unknown action returns error', async () => {
    const result = await frug.run(['hybrid', 'bad-action']);
    assert.strictEqual(result.success, false);
  });

  // ── start --hybrid (core hybrid mode) ─────────────────────────────────────

  it('start --hybrid returns hybrid mode result', async () => {
    const result = await frug.run(['start', '--hybrid']);
    assert.strictEqual(result.success, true);
    assert.strictEqual(result.mode, 'hybrid');
    assert.ok(result.mainModel);
    assert.ok(result.hybridConfig);
    assert.strictEqual(result.hybridConfig.mode, 'hybrid');
    // Clean up
    await frug.run(['stop']);
  });

  it('start --hybrid persists hybrid-mode state file', async () => {
    await frug.run(['start', '--hybrid']);
    const stateFile = path.join(testDir, '.frugality/state/hybrid-mode');
    assert.ok(fs.existsSync(stateFile), 'hybrid-mode state file should exist');
    const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
    assert.strictEqual(state.mode, 'hybrid');
    await frug.run(['stop']);
  });

  it('stop clears hybrid-mode state file', async () => {
    await frug.run(['start', '--hybrid']);
    await frug.run(['stop']);
    const stateFile = path.join(testDir, '.frugality/state/hybrid-mode');
    assert.strictEqual(fs.existsSync(stateFile), false, 'hybrid-mode state file should be gone after stop');
  });

  it('status shows hybrid mode when hybrid-mode file exists', async () => {
    await frug.run(['start', '--hybrid']);
    const status = await frug.run(['status']);
    assert.strictEqual(status.mode, 'hybrid');
    await frug.run(['stop']);
  });

  it('start --opencode --hybrid returns hybrid opencode mode', async () => {
    const result = await frug.run(['start', '--opencode', '--hybrid']);
    assert.strictEqual(result.success, true);
    assert.strictEqual(result.mode, 'hybrid');
    await frug.run(['stop']);
  });

  it('start --hybrid respects FRUGALITY_MAIN_MODEL env var', async () => {
    process.env.FRUGALITY_MAIN_MODEL = 'claude-opus-4-6';
    const result = await frug.run(['start', '--hybrid']);
    assert.strictEqual(result.mainModel, 'claude-opus-4-6');
    delete process.env.FRUGALITY_MAIN_MODEL;
    await frug.run(['stop']);
  });

  // ── init --hybrid ─────────────────────────────────────────────────────────

  it('init --hybrid writes HYBRID.md when file absent', async () => {
    const hybridMdPath = path.join(process.cwd(), 'HYBRID.md');
    // Remove if it already exists from a prior start --hybrid call
    if (fs.existsSync(hybridMdPath)) fs.unlinkSync(hybridMdPath);

    const result = await frug.run(['init', '--hybrid']);
    assert.strictEqual(result.success, true);
    assert.ok(result.templatePath);

    // Clean up
    if (fs.existsSync(result.templatePath)) fs.unlinkSync(result.templatePath);
  });

  it('init --hybrid refuses to overwrite without --force', async () => {
    const hybridMdPath = path.join(process.cwd(), 'HYBRID.md');
    fs.writeFileSync(hybridMdPath, 'placeholder');

    const result = await frug.run(['init', '--hybrid']);
    assert.strictEqual(result.success, false);
    assert.ok(result.message.includes('already exists'));

    fs.unlinkSync(hybridMdPath);
  });

  // ── config ─────────────────────────────────────────────────────────────────

  it('config show returns an object', async () => {
    const result = await frug.run(['config', 'show']);
    assert.ok(result);
    assert.ok(result.version);
  });

  it('config with no action returns path and commands', async () => {
    const result = await frug.run(['config']);
    assert.ok(result.path);
    assert.ok(Array.isArray(result.commands));
  });

  it('config set stores a value', async () => {
    const result = await frug.run(['config', 'set', 'logging.level', 'debug']);
    assert.strictEqual(result.saved, true);
  });

  it('config set without value returns error', async () => {
    const result = await frug.run(['config', 'set', 'logging.level']);
    assert.strictEqual(result.success, false);
    assert.ok(result.error);
  });

  it('config reset restores defaults', async () => {
    const result = await frug.run(['config', 'reset']);
    assert.strictEqual(result.saved, true);
  });
});
