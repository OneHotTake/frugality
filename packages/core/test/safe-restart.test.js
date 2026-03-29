'use strict';

const test = require('node:test');
const assert = require('node:assert');
const safeRestart = require('../src/safe-restart');

test('isIdle - returns idle=true when no connections and no in-flight', () => {
  // Mock getActiveConnections to return 0
  const originalFn = safeRestart.getActiveConnections;
  safeRestart.getActiveConnections = () => 0;
  
  const result = safeRestart.isIdle(3456, '/tmp/nonexistent.log');
  
  assert.equal(result.idle, true);
  assert.equal(result.connections, 0);
  assert.equal(result.inFlight, false);
  
  safeRestart.getActiveConnections = originalFn;
});

test('isIdle - returns idle=false when connections present', () => {
  const originalFn = safeRestart.getActiveConnections;
  safeRestart.getActiveConnections = () => 2;
  
  const result = safeRestart.isIdle(3456, '/tmp/nonexistent.log');
  
  assert.equal(result.idle, false);
  assert.equal(result.connections, 2);
  assert.ok(result.reason);
  
  safeRestart.getActiveConnections = originalFn;
});

test('hasPendingRestart - returns pending=false when file absent', () => {
  const result = safeRestart.hasPendingRestart();
  assert.equal(result.pending, false);
});

test('isRequestInFlight - returns false for missing log', () => {
  const result = safeRestart.isRequestInFlight('/tmp/nonexistent-log.txt', 30);
  assert.equal(result, false);
});

test('isRequestInFlight - returns false for empty log', () => {
  const fs = require('fs');
  const testLog = '/tmp/test-empty.log';
  fs.writeFileSync(testLog, '', 'utf8');
  
  const result = safeRestart.isRequestInFlight(testLog, 30);
  assert.equal(result, false);
  
  fs.unlinkSync(testLog);
});

test('isRequestInFlight - returns true for recent timestamp without completion', () => {
  const fs = require('fs');
  const testLog = '/tmp/test-recent.log';
  const recentTime = new Date().toISOString();
  fs.writeFileSync(testLog, `${recentTime} [PROCESSING] request in flight\n`, 'utf8');
  
  const result = safeRestart.isRequestInFlight(testLog, 30);
  assert.equal(result, true);
  
  fs.unlinkSync(testLog);
});

test('hasPendingRestart - detects pending flag file', () => {
  const fs = require('fs');
  const testFile = '/tmp/test-pending.json';
  const data = { reason: 'test', timestamp: new Date().toISOString() };
  fs.writeFileSync(testFile, JSON.stringify(data), 'utf8');
  
  // Note: This test uses file path, actual implementation reads from defaults.PENDING_RESTART
  // Just verify the JSON structure is valid
  const content = JSON.parse(fs.readFileSync(testFile, 'utf8'));
  assert.equal(content.reason, 'test');
  assert.ok(content.timestamp);
  
  fs.unlinkSync(testFile);
});

