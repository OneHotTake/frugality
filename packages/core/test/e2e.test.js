const assert = require('assert');
const path = require('path');
const fs = require('fs');
const { describe, it, before, after } = require('node:test');

describe('Core Package E2E Tests', () => {
  const testDir = path.join(process.env.HOME || '/home/user', '.frugality-test');
  const testCacheDir = path.join(testDir, 'cache');
  const testStateDir = path.join(testDir, 'state');
  const testLogDir = path.join(testDir, 'logs');
  
  before(() => {
    process.env.HOME = testDir;
  });
  
  after(() => {
    if (fs.existsSync(testDir)) {
      fs.rmSync(testDir, { recursive: true, force: true });
    }
  });
  
  describe('bridge module', () => {
    const bridge = require('../src/bridge');
    
    it('should build provider config', () => {
      const config = bridge.buildProviderConfig('test-model', 'TEST_API_KEY', 'https://api.test.com');
      assert.strictEqual(config.modelId, 'test-model');
      assert.strictEqual(config.providerKeyName, 'TEST_API_KEY');
      assert.strictEqual(config.baseUrl, 'https://api.test.com');
    });
    
    it('should throw error without modelId', () => {
      assert.throws(() => bridge.buildProviderConfig(), /modelId is required/);
    });
    
    it('should build manifest from models', () => {
      const models = [
        { id: 'model-1', provider: 'anthropic', tier: 'S' },
        { id: 'model-2', provider: 'openai', tier: 'S' }
      ];
      const manifest = bridge.buildManifest(models);
      assert.strictEqual(manifest.version, '1.0');
      assert.strictEqual(manifest.models.length, 2);
      assert.strictEqual(manifest.models[0].id, 'model-1');
    });
    
    it('should throw error for non-array models', () => {
      assert.throws(() => bridge.buildManifest('not-an-array'), /models must be an array/);
    });
    
    it('should run bridge with options', () => {
      bridge.setPresetsDir(path.join(testDir, 'presets'));
      const result = bridge.runBridge({
        preset: 'test-preset',
        models: [{ id: 'test-model', provider: 'test' }],
        staging: false
      });
      assert.strictEqual(result.status, 'active');
      assert.ok(result.manifestPath.includes('manifest.json'));
    });
    
    it('should install preset', () => {
      bridge.setPresetsDir(path.join(testDir, 'presets'));
      const presetPath = bridge.installPreset('new-preset');
      assert.ok(presetPath.includes('new-preset'));
    });
  });
  
  describe('safe-restart module', () => {
    const safeRestart = require('../src/safe-restart');
    
    it('should set and clear pending restart', () => {
      safeRestart.setStateDir(testStateDir);
      const result = safeRestart.setPendingRestart('test reason');
      assert.strictEqual(result.reason, 'test reason');
      assert.ok(safeRestart.hasPendingRestart());
      safeRestart.clearPendingRestart();
      assert.strictEqual(safeRestart.hasPendingRestart(), false);
    });
    
    it('should get pending restart data', () => {
      safeRestart.setStateDir(testStateDir);
      safeRestart.setPendingRestart('test');
      const pending = safeRestart.getPendingRestart();
      assert.strictEqual(pending.reason, 'test');
      safeRestart.clearPendingRestart();
    });
    
    it('should check isRequestInFlight', () => {
      safeRestart.setLogDir(testLogDir);
      const inFlight = safeRestart.isRequestInFlight();
      assert.strictEqual(typeof inFlight, 'boolean');
    });
    
    it('should restart CCR', () => {
      safeRestart.setStateDir(testStateDir);
      const result = safeRestart.restartCCR();
      assert.strictEqual(result.success, true);
    });
  });
  
  describe('best-model module', () => {
    const bestModel = require('../src/best-model');
    
    it('should query free models', async () => {
      const models = await bestModel.queryFreeModels('S', 'fiable');
      assert.ok(Array.isArray(models));
      assert.ok(models.length > 0);
    });
    
    it('should select model by task type', () => {
      const models = [
        { id: 'model-1', tier: 'S', capabilities: ['chat'] },
        { id: 'model-2', tier: 'A', capabilities: ['chat'] }
      ];
      const selected = bestModel.selectByTaskType(models);
      assert.strictEqual(selected.id, 'model-1');
    });
    
    it('should extract provider key', () => {
      const key = bestModel.extractProviderKey('claude-3-haiku');
      assert.strictEqual(key.provider, 'anthropic');
      assert.strictEqual(key.keyName, 'ANTHROPIC_API_KEY');
    });
    
    it('should write and read cache', () => {
      bestModel.setCacheDir(testCacheDir);
      bestModel.writeCache('test-task', 'test-model', { key: 'value' });
      const cached = bestModel.readCache('test-task');
      assert.strictEqual(cached.modelId, 'test-model');
    });
    
    it('should get best model', async () => {
      bestModel.setCacheDir(testCacheDir);
      const model = await bestModel.getBestModel('test');
      assert.ok(model);
      assert.ok(model.id);
    });
    
    it('should clear cache', () => {
      bestModel.setCacheDir(testCacheDir);
      bestModel.clearCache();
      const cached = bestModel.readCache('test-task');
      assert.strictEqual(cached, null);
    });
  });
  
  describe('idle-watcher module', () => {
    const idleWatcher = require('../src/idle-watcher');
    
    it('should check and apply pending', () => {
      idleWatcher.setStateDir(testStateDir);
      idleWatcher.setPendingConfig({ test: 'config' });
      const pending = idleWatcher.checkAndApplyPending();
      assert.strictEqual(pending.action, 'config');
    });
    
    it('should rotate logs', () => {
      idleWatcher.setLogDir(testLogDir);
      const result = idleWatcher.rotateLogs();
      assert.strictEqual(typeof result.rotated, 'boolean');
    });
    
    it('should start and stop', () => {
      idleWatcher.setStateDir(testStateDir);
      const startResult = idleWatcher.start({ pollInterval: 1000 });
      assert.strictEqual(startResult.started, true);
      assert.strictEqual(idleWatcher.isRunning(), true);
      const stopResult = idleWatcher.stop();
      assert.strictEqual(stopResult.stopped, true);
    });
  });
});
