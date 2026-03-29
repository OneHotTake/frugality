'use strict';

const test = require('node:test');
const assert = require('node:assert');
const watchdog = require('../src/watchdog');

test('watchdog.status returns current state', () => {
  const status = watchdog.status();
  assert.ok(typeof status === 'object');
  assert.ok('running' in status);
  assert.ok('pid' in status);
});
