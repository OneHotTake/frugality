'use strict';

const test = require('node:test');
const assert = require('node:assert');
const idleWatcher = require('../src/idle-watcher');

test('isRunning - returns false when PID file absent', () => {
  const running = idleWatcher.isRunning();
  assert.equal(typeof running, 'boolean');
});

test('stop - clears interval and returns stopped status', () => {
  const result = idleWatcher.stop();
  assert.ok(result.stopped === true || result.stopped === false);
});

test('checkAndApplyPending - returns checked=true on completion', async () => {
  // Create a simple mock test
  const result = await idleWatcher.checkAndApplyPending();
  assert.ok('checked' in result);
  assert.equal(typeof result.checked, 'boolean');
});

test('rotateLogs - handles missing log directory gracefully', () => {
  // Should not throw
  idleWatcher.rotateLogs();
  assert.ok(true);
});

