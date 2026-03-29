const assert = require('assert');
const path = require('path');
const fs = require('fs');
const { describe, it, before, after } = require('node:test');

describe('Failure Scenario Tests', () => {
  const testDir = path.join(process.env.HOME || '/home/user', '.frugality-fail-test');
  const testCacheDir = path.join(testDir, 'cache');
  const testStateDir = path.join(testDir, 'state');
  const testLogDir = path.join(testDir, 'logs');
  const testPresetsDir = path.join(testDir, 'presets');
  
  before(() => {
    process.env.HOME = testDir;
  });
  
  after(() => {
    if (fs.existsSync(testDir)) {
      fs.rmSync(testDir, { recursive: true, force: true });
    }
  });

  describe('bridge module failures', () => {
    const bridge = require('../src/bridge');
    
    it('should handle missing modelId', () => {
      assert.throws(() => bridge.buildProviderConfig(), /modelId is required/);
      assert.throws(() => bridge.buildProviderConfig(null, 'key'), /modelId is required/);
    });
    
    it('should handle missing providerKeyName', () => {
      assert.throws(() => bridge.buildProviderConfig('model', null), /providerKeyName is required/);
      assert.throws(() => bridge.buildProviderConfig('model'), /providerKeyName is required/);
    });
    
    it('should handle non-array models', () => {
      assert.throws(() => bridge.buildManifest(null), /models must be an array/);
      assert.throws(() => bridge.buildManifest('string'), /models must be an array/);
      assert.throws(() => bridge.buildManifest(123), /models must be an array/);
      assert.throws(() => bridge.buildManifest({}), /models must be an array/);
    });
    
    it('should handle missing manifest', () => {
      assert.throws(() => bridge.writeManifest(null, 'preset'), /manifest is required/);
      assert.throws(() => bridge.writeManifest(undefined, 'preset'), /manifest is required/);
    });
    
    it('should handle missing presetName', () => {
      assert.throws(() => bridge.writeManifest({}, null), /presetName is required/);
      assert.throws(() => bridge.writeManifest({}, undefined), /presetName is required/);
    });
    
    it('should handle promoteStaged with missing staging dir', () => {
      bridge.setPresetsDir(testPresetsDir);
      assert.throws(() => bridge.promoteStaged('nonexistent'), /Staging directory does not exist/);
    });
    
    it('should handle promoteStaged with missing manifest', () => {
      // Staging dir is now a sibling: .staging-<presetName> (not inside the preset dir)
      const stagingDir = path.join(testPresetsDir, '.staging-test');
      fs.mkdirSync(stagingDir, { recursive: true });
      assert.throws(() => bridge.promoteStaged('test'), /Staged manifest not found/);
    });
    
    it('should handle missing presetName for install', () => {
      assert.throws(() => bridge.installPreset(null), /presetName is required/);
      assert.throws(() => bridge.installPreset(''), /presetName is required/);
    });
    
    it('should handle runBridge with invalid options', () => {
      bridge.setPresetsDir(testPresetsDir);
      const result = bridge.runBridge({ models: [] });
      assert.strictEqual(result.status, 'active');
    });
  });

  describe('safe-restart module failures', () => {
    const safeRestart = require('../src/safe-restart');
    
    it('should handle setPendingRestart', () => {
      safeRestart.setStateDir(testStateDir);
      const result = safeRestart.setPendingRestart('test');
      assert.ok(result.timestamp);
      assert.strictEqual(result.reason, 'test');
    });
    
    it('should handle clearPendingRestart', () => {
      safeRestart.setStateDir(testStateDir);
      safeRestart.setPendingRestart('test');
      assert.strictEqual(safeRestart.hasPendingRestart(), true);
      safeRestart.clearPendingRestart();
      assert.strictEqual(safeRestart.hasPendingRestart(), false);
    });
    
    it('should handle getPendingRestart when none exists', () => {
      safeRestart.setStateDir(testStateDir);
      safeRestart.clearPendingRestart();
      const result = safeRestart.getPendingRestart();
      assert.strictEqual(result, null);
    });
    
    it('should handle isRequestInFlight with missing log', () => {
      safeRestart.setLogDir(testLogDir);
      const result = safeRestart.isRequestInFlight();
      assert.strictEqual(result, false);
    });
    
    it('should handle restartCCR with no PID file', () => {
      safeRestart.setStateDir(testStateDir);
      const result = safeRestart.restartCCR();
      assert.strictEqual(result.success, true);
    });
    
    it('should handle verifyCCRHealth connection refused', async () => {
      const result = await safeRestart.verifyCCRHealth(59999, 100);
      assert.strictEqual(result.healthy, false);
    });
    
    it('should handle safeRestart with pending restart', async () => {
      safeRestart.setStateDir(testStateDir);
      safeRestart.setLogDir(testLogDir);
      safeRestart.setPendingRestart('test');
      const result = await safeRestart.safeRestart({ force: false });
      assert.strictEqual(result.status, 'restarted');
    });
    
    it('should handle safeRestart with force', async () => {
      safeRestart.setStateDir(testStateDir);
      const result = await safeRestart.safeRestart({ force: true, reason: 'test' });
      assert.strictEqual(result.status, 'restarted');
    });
  });

  describe('best-model module failures', () => {
    const bestModel = require('../src/best-model');
    
    it('should handle extractProviderKey with missing modelId', () => {
      assert.throws(() => bestModel.extractProviderKey(), /modelId is required/);
      assert.throws(() => bestModel.extractProviderKey(null), /modelId is required/);
    });
    
    it('should handle extractProviderKey with unknown model', () => {
      const result = bestModel.extractProviderKey('unknown-model-xyz');
      assert.strictEqual(result.provider, 'unknown');
      assert.strictEqual(result.keyName, 'API_KEY');
    });
    
    it('should handle selectByTaskType with empty array', () => {
      const result = bestModel.selectByTaskType([]);
      assert.strictEqual(result, null);
    });
    
    it('should handle selectByTaskType with invalid input', () => {
      assert.strictEqual(bestModel.selectByTaskType(null), null);
      assert.strictEqual(bestModel.selectByTaskType(undefined), null);
    });
    
    it('should handle readCache with no cache file', () => {
      bestModel.setCacheDir(testCacheDir);
      const result = bestModel.readCache('nonexistent-task');
      assert.strictEqual(result, null);
    });
    
    it('should handle readCache with stale cache', () => {
      bestModel.setCacheDir(testCacheDir);
      bestModel.setCacheTTL(1);
      bestModel.writeCache('test-task', 'test-model', { key: 'value' });
      return new Promise((resolve) => {
        setTimeout(async () => {
          const result = await bestModel.readCache('test-task');
          assert.strictEqual(result, null);
          bestModel.setCacheTTL(1800000);
          resolve();
        }, 10);
      });
    });
    
    it('should handle clearCache', () => {
      bestModel.setCacheDir(testCacheDir);
      bestModel.writeCache('task1', 'model1', {});
      bestModel.clearCache();
      const result = bestModel.readCache('task1');
      assert.strictEqual(result, null);
    });
    
    it('should handle queryFreeModels', async () => {
      const result = await bestModel.queryFreeModels();
      assert.ok(Array.isArray(result));
      assert.ok(result.length > 0);
    });
    
    it('should handle getBestModel', async () => {
      bestModel.setCacheDir(testCacheDir);
      const result = await bestModel.getBestModel('test-task');
      assert.ok(result);
      assert.ok(result.id);
    });
    
    it('should handle refreshAll', async () => {
      bestModel.setCacheDir(testCacheDir);
      const result = await bestModel.refreshAll();
      assert.strictEqual(result.refreshed, true);
      assert.ok(result.modelCount > 0);
    });
  });

  describe('idle-watcher module failures', () => {
    const idleWatcher = require('../src/idle-watcher');
    
    it('should handle checkAndApplyPending with no pending', () => {
      idleWatcher.setStateDir(testStateDir);
      idleWatcher.clearPendingConfig();
      const result = idleWatcher.checkAndApplyPending();
      assert.strictEqual(result, null);
    });
    
    it('should handle checkAndApplyPending with pending config', () => {
      idleWatcher.setStateDir(testStateDir);
      idleWatcher.setPendingConfig({ test: 'value' });
      const result = idleWatcher.checkAndApplyPending();
      assert.strictEqual(result.action, 'config');
    });
    
    it('should handle rotateLogs with no log file', () => {
      idleWatcher.setLogDir(testLogDir);
      const result = idleWatcher.rotateLogs();
      assert.strictEqual(result.rotated, false);
      assert.strictEqual(result.reason, 'no log file');
    });
    
    it('should handle start twice', () => {
      idleWatcher.setStateDir(testStateDir);
      idleWatcher.stop();
      const result1 = idleWatcher.start({ pollInterval: 1000 });
      assert.strictEqual(result1.started, true);
      const result2 = idleWatcher.start({ pollInterval: 1000 });
      assert.strictEqual(result2.started, false);
      idleWatcher.stop();
    });
    
    it('should handle stop when not running', () => {
      idleWatcher.setStateDir(testStateDir);
      idleWatcher.stop();
      const result = idleWatcher.stop();
      assert.strictEqual(result.stopped, false);
    });
    
    it('should handle isRunning when not running', () => {
      idleWatcher.setStateDir(testStateDir);
      idleWatcher.stop();
      const result = idleWatcher.isRunning();
      assert.strictEqual(result, false);
    });
    
    it('should handle clearPendingConfig', () => {
      idleWatcher.setStateDir(testStateDir);
      idleWatcher.setPendingConfig({});
      idleWatcher.clearPendingConfig();
      const pending = idleWatcher.checkAndApplyPending();
      assert.strictEqual(pending, null);
    });
  });
});
