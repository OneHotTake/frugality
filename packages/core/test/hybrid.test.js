const assert = require('assert');
const path = require('path');
const fs = require('fs');
const { describe, it, before, after } = require('node:test');

describe('Hybrid Module Tests', () => {
  const testDir      = path.join('/tmp', 'frugality-hybrid-test-' + process.pid);
  const testCacheDir = path.join(testDir, 'cache');
  const testStateDir = path.join(testDir, 'state');

  const hybrid = require('../src/hybrid');

  before(() => {
    process.env.HOME = testDir;
    fs.mkdirSync(testCacheDir, { recursive: true });
    fs.mkdirSync(testStateDir, { recursive: true });
    hybrid.setCacheDir(testCacheDir);
    hybrid.setStateDir(testStateDir);
  });

  after(() => {
    delete process.env.FRUGALITY_MAIN_MODEL;
    if (fs.existsSync(testDir)) {
      fs.rmSync(testDir, { recursive: true, force: true });
    }
  });

  // ── getMainModel ──────────────────────────────────────────────────────────

  it('returns default main model when env var not set', () => {
    delete process.env.FRUGALITY_MAIN_MODEL;
    const model = hybrid.getMainModel();
    assert.strictEqual(typeof model, 'string');
    assert.ok(model.length > 0);
    assert.strictEqual(model, hybrid.getFallbackModels().main);
  });

  it('respects FRUGALITY_MAIN_MODEL env var', () => {
    process.env.FRUGALITY_MAIN_MODEL = 'claude-opus-4-6';
    assert.strictEqual(hybrid.getMainModel(), 'claude-opus-4-6');
    delete process.env.FRUGALITY_MAIN_MODEL;
  });

  // ── getAgentModel ─────────────────────────────────────────────────────────

  it('returns fallback when cache is empty', () => {
    const model = hybrid.getAgentModel('fast');
    assert.strictEqual(typeof model, 'string');
    assert.ok(model.length > 0);
  });

  it('reads fast model from cache file', () => {
    fs.writeFileSync(path.join(testCacheDir, 'best-model-fast.txt'), 'gemini-flash-test');
    const model = hybrid.getAgentModel('fast');
    assert.strictEqual(model, 'gemini-flash-test');
    fs.unlinkSync(path.join(testCacheDir, 'best-model-fast.txt'));
  });

  it('reads analysis model from cache file', () => {
    fs.writeFileSync(path.join(testCacheDir, 'best-model-analysis.txt'), 'gpt4-analysis-test');
    const model = hybrid.getAgentModel('analysis');
    assert.strictEqual(model, 'gpt4-analysis-test');
    fs.unlinkSync(path.join(testCacheDir, 'best-model-analysis.txt'));
  });

  it('reads reasoning model from cache file', () => {
    fs.writeFileSync(path.join(testCacheDir, 'best-model-reasoning.txt'), 'deepseek-test');
    const model = hybrid.getAgentModel('reasoning');
    assert.strictEqual(model, 'deepseek-test');
    fs.unlinkSync(path.join(testCacheDir, 'best-model-reasoning.txt'));
  });

  it('falls back to default cache when typed cache missing', () => {
    fs.writeFileSync(path.join(testCacheDir, 'best-model-default.txt'), 'default-fallback-model');
    const model = hybrid.getAgentModel('fast'); // fast cache absent
    assert.strictEqual(model, 'default-fallback-model');
    fs.unlinkSync(path.join(testCacheDir, 'best-model-default.txt'));
  });

  it('returns hardcoded fallback when all cache files absent', () => {
    const model = hybrid.getAgentModel('fast');
    const fallbacks = hybrid.getFallbackModels();
    assert.strictEqual(model, fallbacks.fast);
  });

  it('handles unknown task type without throwing', () => {
    const model = hybrid.getAgentModel('unknown-type');
    assert.strictEqual(typeof model, 'string');
    assert.ok(model.length > 0);
  });

  // ── buildHybridConfig ─────────────────────────────────────────────────────

  it('builds a complete hybrid config object', () => {
    const cfg = hybrid.buildHybridConfig();
    assert.strictEqual(cfg.mode, 'hybrid');
    assert.ok(cfg.main);
    assert.ok(cfg.main.model);
    assert.ok(cfg.agents);
    assert.ok(cfg.agents.fast);
    assert.ok(cfg.agents.analysis);
    assert.ok(cfg.agents.reasoning);
    assert.ok(cfg.taskRouting);
    assert.strictEqual(cfg.taskRouting.BOILERPLATE, 'fast');
    assert.strictEqual(cfg.taskRouting.TESTS, 'fast');
    assert.strictEqual(cfg.taskRouting.DOCS, 'fast');
    assert.strictEqual(cfg.taskRouting.ANALYSIS, 'analysis');
    assert.strictEqual(cfg.taskRouting.REASONING, 'reasoning');
    assert.strictEqual(cfg.taskRouting.ARCHITECTURE, 'main');
  });

  // ── writeHybridState / readHybridState ────────────────────────────────────

  it('writes and reads hybrid state', () => {
    const state = hybrid.writeHybridState({ version: '0.3.0' });
    assert.strictEqual(state.mode, 'hybrid');
    assert.ok(state.startedAt);
    assert.strictEqual(state.version, '0.3.0');

    const read = hybrid.readHybridState();
    assert.ok(read);
    assert.strictEqual(read.mode, 'hybrid');
    assert.strictEqual(read.version, '0.3.0');
  });

  it('isHybridMode returns true after writeHybridState', () => {
    hybrid.writeHybridState({});
    assert.strictEqual(hybrid.isHybridMode(), true);
  });

  it('clearHybridState removes state file', () => {
    hybrid.writeHybridState({});
    assert.strictEqual(hybrid.isHybridMode(), true);
    hybrid.clearHybridState();
    assert.strictEqual(hybrid.isHybridMode(), false);
  });

  it('readHybridState returns null when no state file', () => {
    hybrid.clearHybridState();
    assert.strictEqual(hybrid.readHybridState(), null);
  });

  // ── getHybridTemplate ─────────────────────────────────────────────────────

  it('template contains key sections', () => {
    const tpl = hybrid.getHybridTemplate();
    assert.ok(tpl.includes('hybrid mode'));
    assert.ok(tpl.includes('Anthropic subscription'));
    assert.ok(tpl.includes('Task Type'));
    assert.ok(tpl.includes('fast'));
    assert.ok(tpl.includes('analysis'));
    assert.ok(tpl.includes('reasoning'));
    assert.ok(tpl.includes('Delegate to Free Agent'));
    assert.ok(tpl.includes('frug update'));
  });

  // ── writeTemplate ─────────────────────────────────────────────────────────

  it('writes HYBRID.md to specified path', () => {
    const targetPath = path.join(testDir, 'HYBRID.md');
    const result = hybrid.writeTemplate(targetPath);
    assert.strictEqual(result, targetPath);
    assert.ok(fs.existsSync(targetPath));
    const content = fs.readFileSync(targetPath, 'utf8');
    assert.ok(content.includes('hybrid mode'));
  });
});
