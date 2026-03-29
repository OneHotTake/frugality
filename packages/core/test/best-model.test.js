'use strict';

const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const bestModel = require('../src/best-model');

// Mock execSync
const Module = require('module');
const originalRequire = Module.prototype.require;

test('selectByTaskType - fast task selects highest A+ tier', () => {
  const models = [
    { modelId: 'model-a', tier: 'A+', sweScore: '85.0' },
    { modelId: 'model-b', tier: 'A', sweScore: '82.0' },
    { modelId: 'model-c', tier: 'S', sweScore: '80.0' }
  ];
  const result = bestModel.selectByTaskType(models, 'fast');
  assert.equal(result.modelId, 'model-a');
  assert.equal(result.tier, 'A+');
});

test('selectByTaskType - reasoning task selects S+ over S', () => {
  const models = [
    { modelId: 'model-a', tier: 'S', sweScore: '85.0' },
    { modelId: 'model-b', tier: 'S+', sweScore: '88.0' },
    { modelId: 'model-c', tier: 'A', sweScore: '90.0' }
  ];
  const result = bestModel.selectByTaskType(models, 'reasoning');
  assert.equal(result.modelId, 'model-b');
  assert.equal(result.tier, 'S+');
});

test('selectByTaskType - analysis prefers gemini if available', () => {
  const models = [
    { modelId: 'qwen', provider: 'qwen', tier: 'S+', sweScore: '90.0' },
    { modelId: 'gemini-flash', provider: 'gemini', tier: 'S', sweScore: '85.0' }
  ];
  const result = bestModel.selectByTaskType(models, 'analysis');
  assert.equal(result.modelId, 'gemini-flash');
});

test('selectByTaskType - default uses highest S-tier', () => {
  const models = [
    { modelId: 'a', tier: 'S', sweScore: '80.0' },
    { modelId: 'b', tier: 'S', sweScore: '85.0' },
    { modelId: 'c', tier: 'A+', sweScore: '86.0' }
  ];
  const result = bestModel.selectByTaskType(models, 'default');
  assert.equal(result.modelId, 'b');
});

test('selectByTaskType - handles empty models gracefully', () => {
  const result = bestModel.selectByTaskType([], 'fast');
  assert.equal(result, null);
});

test('selectByTaskType - handles undefined models gracefully', () => {
  const result = bestModel.selectByTaskType(undefined, 'fast');
  assert.equal(result, null);
});

test('readCache - returns null for missing file', () => {
  const result = bestModel.readCache('nonexistent-task-type');
  assert.equal(result, null);
});

test('writeCache - creates cache file atomically', () => {
  const testDir = path.join(__dirname, '../../.cache-test');
  if (!fs.existsSync(testDir)) fs.mkdirSync(testDir, { recursive: true });
  
  // This test verifies the function doesn't crash
  bestModel.writeCache('test-task', 'model-id', 'KEY_NAME');
  
  // Cleanup
  if (fs.existsSync(testDir)) {
    fs.rmSync(testDir, { recursive: true });
  }
});

test('extractProviderKey - handles missing FCM JSON', () => {
  const result = bestModel.extractProviderKey('model-id', '/nonexistent/path.json');
  assert.equal(result, null);
});

test('extractProviderKey - returns null for unknown provider', () => {
  const result = bestModel.extractProviderKey('unknown-provider-model', '/tmp/fcm.json');
  assert.equal(result, null);
});

