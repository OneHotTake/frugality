'use strict';

const test = require('node:test');
const assert = require('node:assert');
const watchdog = require('../src/watchdog');

test('status - returns object with running and pid', () => {
  const status = watchdog.status();
  assert.ok(typeof status === 'object');
  assert.ok('running' in status);
  assert.ok('pid' in status);
  assert.ok('failureCount' in status);
});

test('isRunning - returns boolean', () => {
  const running = watchdog.isRunning();
  assert.equal(typeof running, 'boolean');
});

test('stop - gracefully stops watchdog', () => {
  const result = watchdog.stop();
  assert.ok(result.stopped === true);
});

test('pingCurrentModel - returns object with health status', () => {
  const result = watchdog.pingCurrentModel();
  assert.ok(typeof result === 'object');
  assert.ok('healthy' in result);
  assert.ok('latencyMs' in result);
  assert.equal(typeof result.latencyMs, 'number');
});

test('checkCCRProcess - returns object with healthy status', () => {
  const result = watchdog.checkCCRProcess();
  assert.ok(typeof result === 'object');
  assert.ok('healthy' in result);
  assert.equal(typeof result.healthy, 'boolean');
});

test('getLastUpdate - returns null or number', () => {
  const result = watchdog.getLastUpdate();
  assert.ok(result === null || typeof result === 'number');
});

