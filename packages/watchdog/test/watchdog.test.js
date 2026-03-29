const assert = require('assert');
const watchdog = require('../src/watchdog');

// Test watchdog functions
assert.strictEqual(typeof watchdog.pingCurrentModel, 'function');
assert.strictEqual(typeof watchdog.checkCCRProcess, 'function');
assert.strictEqual(typeof watchdog.handleUnhealthy, 'function');
assert.strictEqual(typeof watchdog.handleCCRDown, 'function');
assert.strictEqual(typeof watchdog.mainLoop, 'function');
assert.strictEqual(typeof watchdog.start, 'function');
assert.strictEqual(typeof watchdog.stop, 'function');
assert.strictEqual(typeof watchdog.status, 'function');
assert.strictEqual(typeof watchdog.rotateLogs, 'function');
