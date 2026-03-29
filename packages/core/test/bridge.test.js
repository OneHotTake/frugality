const assert = require('assert');
const bridge = require('../src/bridge');
const safeRestart = require('../src/safe-restart');
const bestModel = require('../src/best-model');
const idleWatcher = require('../src/idle-watcher');

// Test bridge functions
assert.strictEqual(typeof bridge.buildProviderConfig, 'function');
assert.strictEqual(typeof bridge.buildManifest, 'function');
assert.strictEqual(typeof bridge.writeManifest, 'function');
assert.strictEqual(typeof bridge.promoteStaged, 'function');
assert.strictEqual(typeof bridge.installPreset, 'function');
assert.strictEqual(typeof bridge.runBridge, 'function');

// Test safe-restart functions
assert.strictEqual(typeof safeRestart.getActiveConnections, 'function');
assert.strictEqual(typeof safeRestart.isRequestInFlight, 'function');
assert.strictEqual(typeof safeRestart.isIdle, 'function');
assert.strictEqual(typeof safeRestart.setPendingRestart, 'function');
assert.strictEqual(typeof safeRestart.clearPendingRestart, 'function');
assert.strictEqual(typeof safeRestart.hasPendingRestart, 'function');
assert.strictEqual(typeof safeRestart.restartCCR, 'function');
assert.strictEqual(typeof safeRestart.verifyCCRHealth, 'function');
assert.strictEqual(typeof safeRestart.safeRestart, 'function');

// Test best-model functions
assert.strictEqual(typeof bestModel.queryFreeModels, 'function');
assert.strictEqual(typeof bestModel.extractProviderKey, 'function');
assert.strictEqual(typeof bestModel.selectByTaskType, 'function');
assert.strictEqual(typeof bestModel.writeCache, 'function');
assert.strictEqual(typeof bestModel.readCache, 'function');
assert.strictEqual(typeof bestModel.getBestModel, 'function');
assert.strictEqual(typeof bestModel.refreshAll, 'function');

// Test idle-watcher functions
assert.strictEqual(typeof idleWatcher.checkAndApplyPending, 'function');
assert.strictEqual(typeof idleWatcher.rotateLogs, 'function');
assert.strictEqual(typeof idleWatcher.start, 'function');
assert.strictEqual(typeof idleWatcher.stop, 'function');
assert.strictEqual(typeof idleWatcher.isRunning, 'function');
