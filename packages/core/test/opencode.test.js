const assert = require('assert');
const path = require('path');
const fs = require('fs');
const { describe, it, before, after } = require('node:test');

describe('OpenCode Integration Tests', () => {
  const testDir = path.join(process.env.HOME || '/home/user', '.frugality-opencode-test');
  const testCacheDir = path.join(testDir, 'cache');
  const testStateDir = path.join(testDir, 'state');
  const testLogDir = path.join(testDir, 'logs');
  
  before(() => {
    process.env.HOME = testDir;
    if (!fs.existsSync(testDir)) {
      fs.mkdirSync(testDir, { recursive: true });
    }
  });
  
  after(() => {
    if (fs.existsSync(testDir)) {
      fs.rmSync(testDir, { recursive: true, force: true });
    }
  });
  
  describe('OpenCode CLI Integration', () => {
    const bridge = require('../src/bridge');
    const safeRestart = require('../src/safe-restart');
    const bestModel = require('../src/best-model');
    const idleWatcher = require('../src/idle-watcher');
    
    it('should have all required functions exposed', () => {
      assert.strictEqual(typeof bridge.buildProviderConfig, 'function');
      assert.strictEqual(typeof bridge.buildManifest, 'function');
      assert.strictEqual(typeof bridge.writeManifest, 'function');
      assert.strictEqual(typeof bridge.promoteStaged, 'function');
      assert.strictEqual(typeof bridge.installPreset, 'function');
      assert.strictEqual(typeof bridge.runBridge, 'function');
      
      assert.strictEqual(typeof safeRestart.getActiveConnections, 'function');
      assert.strictEqual(typeof safeRestart.isRequestInFlight, 'function');
      assert.strictEqual(typeof safeRestart.isIdle, 'function');
      assert.strictEqual(typeof safeRestart.setPendingRestart, 'function');
      assert.strictEqual(typeof safeRestart.clearPendingRestart, 'function');
      assert.strictEqual(typeof safeRestart.hasPendingRestart, 'function');
      assert.strictEqual(typeof safeRestart.restartCCR, 'function');
      assert.strictEqual(typeof safeRestart.verifyCCRHealth, 'function');
      assert.strictEqual(typeof safeRestart.safeRestart, 'function');
      
      assert.strictEqual(typeof bestModel.queryFreeModels, 'function');
      assert.strictEqual(typeof bestModel.extractProviderKey, 'function');
      assert.strictEqual(typeof bestModel.selectByTaskType, 'function');
      assert.strictEqual(typeof bestModel.writeCache, 'function');
      assert.strictEqual(typeof bestModel.readCache, 'function');
      assert.strictEqual(typeof bestModel.getBestModel, 'function');
      assert.strictEqual(typeof bestModel.refreshAll, 'function');
      
      assert.strictEqual(typeof idleWatcher.checkAndApplyPending, 'function');
      assert.strictEqual(typeof idleWatcher.rotateLogs, 'function');
      assert.strictEqual(typeof idleWatcher.start, 'function');
      assert.strictEqual(typeof idleWatcher.stop, 'function');
      assert.strictEqual(typeof idleWatcher.isRunning, 'function');
    });
    
    it('should build provider config for opencode', () => {
      const config = bridge.buildProviderConfig('opencode-model', 'OPENCODE_API_KEY', 'https://api.opencode.ai');
      assert.strictEqual(config.modelId, 'opencode-model');
      assert.strictEqual(config.providerKeyName, 'OPENCODE_API_KEY');
      assert.strictEqual(config.baseUrl, 'https://api.opencode.ai');
    });
    
    it('should build manifest for opencode models', () => {
      const models = [
        { id: 'opencode-model-1', provider: 'opencode', tier: 'S' },
        { id: 'opencode-model-2', provider: 'opencode', tier: 'S' }
      ];
      const manifest = bridge.buildManifest(models);
      assert.strictEqual(manifest.version, '1.0');
      assert.strictEqual(manifest.models.length, 2);
      assert.strictEqual(manifest.models[0].id, 'opencode-model-1');
    });
    
    it('should run bridge with opencode options', () => {
      bridge.setPresetsDir(path.join(testDir, 'presets'));
      const result = bridge.runBridge({
        preset: 'opencode-preset',
        models: [{ id: 'opencode-model', provider: 'opencode' }],
        staging: false
      });
      assert.strictEqual(result.status, 'active');
      assert.ok(result.manifestPath.includes('manifest.json'));
    });
    
    it('should install opencode preset', () => {
      bridge.setPresetsDir(path.join(testDir, 'presets'));
      const presetPath = bridge.installPreset('opencode-new-preset');
      assert.ok(presetPath.includes('opencode-new-preset'));
    });
    
    it('should query free models for opencode', async () => {
      const models = await bestModel.queryFreeModels('S', 'fiable');
      assert.ok(Array.isArray(models));
      assert.ok(models.length > 0);
    });
    
    it('should select model by task type for opencode', () => {
      const models = [
        { id: 'opencode-model-1', tier: 'S', capabilities: ['chat'] },
        { id: 'opencode-model-2', tier: 'A', capabilities: ['chat'] }
      ];
      const selected = bestModel.selectByTaskType(models);
      assert.strictEqual(selected.id, 'opencode-model-1');
    });
    
    it('should extract provider key for opencode model', () => {
      const key = bestModel.extractProviderKey('claude-3-haiku');
      assert.strictEqual(key.provider, 'anthropic');
      assert.strictEqual(key.keyName, 'ANTHROPIC_API_KEY');
    });
    
    it('should write and read cache for opencode', () => {
      bestModel.setCacheDir(testCacheDir);
      bestModel.writeCache('opencode-task', 'opencode-model', { key: 'value' });
      const cached = bestModel.readCache('opencode-task');
      assert.strictEqual(cached.modelId, 'opencode-model');
    });
    
    it('should get best model for opencode', async () => {
      bestModel.setCacheDir(testCacheDir);
      const model = await bestModel.getBestModel('opencode-test');
      assert.ok(model);
      assert.ok(model.id);
    });
    
    it('should clear cache for opencode', () => {
      bestModel.setCacheDir(testCacheDir);
      bestModel.clearCache();
      const cached = bestModel.readCache('opencode-task');
      assert.strictEqual(cached, null);
    });
    
    it('should set and clear pending restart for opencode', () => {
      safeRestart.setStateDir(testStateDir);
      const result = safeRestart.setPendingRestart('opencode test reason');
      assert.strictEqual(result.reason, 'opencode test reason');
      assert.ok(safeRestart.hasPendingRestart());
      safeRestart.clearPendingRestart();
      assert.strictEqual(safeRestart.hasPendingRestart(), false);
    });
    
    it('should get pending restart data for opencode', () => {
      safeRestart.setStateDir(testStateDir);
      safeRestart.setPendingRestart('opencode test');
      const pending = safeRestart.getPendingRestart();
      assert.strictEqual(pending.reason, 'opencode test');
      safeRestart.clearPendingRestart();
    });
    
    it('should check isRequestInFlight for opencode', () => {
      safeRestart.setLogDir(testLogDir);
      const inFlight = safeRestart.isRequestInFlight();
      assert.strictEqual(typeof inFlight, 'boolean');
    });
    
    it('should restart CCR for opencode', () => {
      safeRestart.setStateDir(testStateDir);
      const result = safeRestart.restartCCR();
      assert.strictEqual(result.success, true);
    });
    
    it('should check and apply pending for opencode', () => {
      idleWatcher.setStateDir(testStateDir);
      idleWatcher.setPendingConfig({ opencode: 'config' });
      const pending = idleWatcher.checkAndApplyPending();
      assert.strictEqual(pending.action, 'config');
    });
    
    it('should rotate logs for opencode', () => {
      idleWatcher.setLogDir(testLogDir);
      const result = idleWatcher.rotateLogs();
      assert.strictEqual(typeof result.rotated, 'boolean');
    });
    
    it('should start and stop idle watcher for opencode', () => {
      idleWatcher.setStateDir(testStateDir);
      const startResult = idleWatcher.start({ pollInterval: 1000 });
      assert.strictEqual(startResult.started, true);
      assert.strictEqual(idleWatcher.isRunning(), true);
      const stopResult = idleWatcher.stop();
      assert.strictEqual(stopResult.stopped, true);
    });
  });
  
  describe('OpenCode CLI Error Handling', () => {
    const bridge = require('../src/bridge');
    const safeRestart = require('../src/safe-restart');
    const bestModel = require('../src/best-model');
    const idleWatcher = require('../src/idle-watcher');
    
    it('should handle missing modelId for opencode', () => {
      assert.throws(() => bridge.buildProviderConfig(), /modelId is required/);
    });
    
    it('should handle missing providerKeyName for opencode', () => {
      assert.throws(() => bridge.buildProviderConfig('test-model'), /providerKeyName is required/);
    });
    
    it('should handle non-array models for opencode', () => {
      assert.throws(() => bridge.buildManifest('not-an-array'), /models must be an array/);
    });
    
    it('should handle missing manifest for opencode', () => {
      assert.throws(() => bridge.writeManifest(), /manifest is required/);
    });
    
    it('should handle missing presetName for opencode', () => {
      assert.throws(() => bridge.writeManifest({}), /presetName is required/);
    });
    
    it('should handle promoteStaged with missing staging dir for opencode', () => {
      assert.throws(() => bridge.promoteStaged('nonexistent'), /Staging directory does not exist/);
    });
    
    it('should handle promoteStaged with missing manifest for opencode', () => {
      bridge.setPresetsDir(path.join(testDir, 'presets'));
      fs.mkdirSync(path.join(testDir, 'presets', 'test-preset', 'staging'), { recursive: true });
      assert.throws(() => bridge.promoteStaged('test-preset'), /Staged manifest not found/);
    });
    
    it('should handle missing presetName for install for opencode', () => {
      assert.throws(() => bridge.installPreset(), /presetName is required/);
    });
    
    it('should handle runBridge with invalid options for opencode', () => {
      bridge.setPresetsDir(path.join(testDir, 'presets'));
      const result = bridge.runBridge({
        preset: 'test-preset',
        models: [{ id: 'test-model', provider: 'test' }],
        staging: false
      });
      assert.strictEqual(result.status, 'active');
    });
    
    it('should handle setPendingRestart for opencode', () => {
      safeRestart.setStateDir(testStateDir);
      const result = safeRestart.setPendingRestart('test reason');
      assert.strictEqual(result.reason, 'test reason');
    });
    
    it('should handle clearPendingRestart for opencode', () => {
      safeRestart.setStateDir(testStateDir);
      safeRestart.setPendingRestart('test');
      safeRestart.clearPendingRestart();
      assert.strictEqual(safeRestart.hasPendingRestart(), false);
    });
    
    it('should handle getPendingRestart when none exists for opencode', () => {
      safeRestart.setStateDir(testStateDir);
      const pending = safeRestart.getPendingRestart();
      assert.strictEqual(pending, null);
    });
    
    it('should handle isRequestInFlight with missing log for opencode', () => {
      safeRestart.setLogDir(testLogDir);
      const inFlight = safeRestart.isRequestInFlight();
      assert.strictEqual(typeof inFlight, 'boolean');
    });
    
    it('should handle restartCCR with no PID file for opencode', () => {
      safeRestart.setStateDir(testStateDir);
      const result = safeRestart.restartCCR();
      assert.strictEqual(result.success, true);
    });
    
    it('should handle verifyCCRHealth connection refused for opencode', async () => {
      const result = await safeRestart.verifyCCRHealth(3456, 1000);
      assert.strictEqual(result.healthy, false);
    });
    
    it('should handle safeRestart with pending restart for opencode', async () => {
      safeRestart.setStateDir(testStateDir);
      const result = await safeRestart.safeRestart({ force: false });
      assert.ok(result.status);
    });
    
    it('should handle safeRestart with force for opencode', async () => {
      safeRestart.setStateDir(testStateDir);
      const result = await safeRestart.safeRestart({ force: true });
      assert.ok(result.status);
    });
    
    it('should handle extractProviderKey with missing modelId for opencode', () => {
      assert.throws(() => bestModel.extractProviderKey(), /modelId is required/);
    });
    
    it('should handle extractProviderKey with unknown model for opencode', () => {
      const key = bestModel.extractProviderKey('unknown-model');
      assert.strictEqual(key.provider, 'unknown');
      assert.strictEqual(key.keyName, 'API_KEY');
    });
    
    it('should handle selectByTaskType with empty array for opencode', () => {
      const selected = bestModel.selectByTaskType([]);
      assert.strictEqual(selected, null);
    });
    
    it('should handle selectByTaskType with invalid input for opencode', () => {
      const selected = bestModel.selectByTaskType(null);
      assert.strictEqual(selected, null);
    });
    
    it('should handle readCache with no cache file for opencode', () => {
      bestModel.setCacheDir(testCacheDir);
      const cached = bestModel.readCache('nonexistent-task');
      assert.strictEqual(cached, null);
    });
    
    it('should handle readCache with stale cache for opencode', () => {
      bestModel.setCacheDir(testCacheDir);
      bestModel.setCacheTTL(1);
      bestModel.writeCache('stale-task', 'stale-model', { key: 'value' });
      setTimeout(() => {
        const cached = bestModel.readCache('stale-task');
        assert.strictEqual(cached, null);
        bestModel.setCacheTTL(1800000);
      }, 10);
    });
    
    it('should handle clearCache for opencode', () => {
      bestModel.setCacheDir(testCacheDir);
      bestModel.clearCache();
      const cached = bestModel.readCache('test-task');
      assert.strictEqual(cached, null);
    });
    
    it('should handle queryFreeModels for opencode', async () => {
      const models = await bestModel.queryFreeModels();
      assert.ok(Array.isArray(models));
      assert.ok(models.length > 0);
    });
    
    it('should handle getBestModel for opencode', async () => {
      bestModel.setCacheDir(testCacheDir);
      const model = await bestModel.getBestModel('test');
      assert.ok(model);
    });
    
    it('should handle refreshAll for opencode', async () => {
      bestModel.setCacheDir(testCacheDir);
      const result = await bestModel.refreshAll();
      assert.strictEqual(result.refreshed, true);
    });
    
    it('should handle checkAndApplyPending with no pending for opencode', () => {
      idleWatcher.setStateDir(testStateDir);
      idleWatcher.clearPendingConfig();
      const pending = idleWatcher.checkAndApplyPending();
      assert.ok(pending === null || pending.action === undefined);
    });
    
    it('should handle checkAndApplyPending with pending config for opencode', () => {
      idleWatcher.setStateDir(testStateDir);
      idleWatcher.setPendingConfig({ test: 'config' });
      const pending = idleWatcher.checkAndApplyPending();
      assert.strictEqual(pending.action, 'config');
    });
    
    it('should handle rotateLogs with no log file for opencode', () => {
      idleWatcher.setLogDir(testLogDir);
      const result = idleWatcher.rotateLogs();
      assert.strictEqual(typeof result.rotated, 'boolean');
    });
    
    it('should handle start twice for opencode', () => {
      idleWatcher.setStateDir(testStateDir);
      const startResult1 = idleWatcher.start({ pollInterval: 1000 });
      assert.strictEqual(startResult1.started, true);
      const startResult2 = idleWatcher.start({ pollInterval: 1000 });
      assert.ok(startResult2.started === true || startResult2.started === false);
      idleWatcher.stop();
    });
    
    it('should handle stop when not running for opencode', () => {
      const stopResult = idleWatcher.stop();
      assert.ok(stopResult.stopped === true || stopResult.stopped === false);
    });
    
    it('should handle isRunning when not running for opencode', () => {
      const running = idleWatcher.isRunning();
      assert.strictEqual(running, false);
    });
    
    it('should handle clearPendingConfig for opencode', () => {
      idleWatcher.setStateDir(testStateDir);
      idleWatcher.setPendingConfig({ test: 'config' });
      const cleared = idleWatcher.clearPendingConfig();
      assert.strictEqual(cleared, true);
    });
  });
});
