'use strict';

const test = require('node:test');
const assert = require('node:assert');
const bestModel = require('../src/best-model');

test('selectByTaskType selects model for fast task', () => {
  const models = [
    { modelId: 'model-a', tier: 'A+', sweScore: '85.0' },
    { modelId: 'model-b', tier: 'S', sweScore: '80.0' }
  ];
  const result = bestModel.selectByTaskType(models, 'fast');
  assert.ok(result);
  assert.equal(result.modelId, 'model-a');
});

test('selectByTaskType selects model for reasoning task', () => {
  const models = [
    { modelId: 'model-a', tier: 'A', sweScore: '85.0' },
    { modelId: 'model-b', tier: 'S+', sweScore: '88.0' }
  ];
  const result = bestModel.selectByTaskType(models, 'reasoning');
  assert.ok(result);
  assert.equal(result.modelId, 'model-b');
});
