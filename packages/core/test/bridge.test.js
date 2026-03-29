'use strict';

const test = require('node:test');
const assert = require('node:assert');
const bridge = require('../src/bridge');

test('buildProviderConfig - creates valid provider object', () => {
  const config = bridge.buildProviderConfig('model-id', 'API_KEY', 'https://api.example.com');
  
  assert.equal(config.id, 'model-id');
  assert.equal(config.name, 'model-id');
  assert.equal(config.base_url, 'https://api.example.com');
  assert.ok(config.auth);
  assert.ok(config.transformer);
});

test('buildProviderConfig - uses env var in auth key', () => {
  const config = bridge.buildProviderConfig('test-model', 'MY_KEY', 'https://api.example.com');
  assert.equal(config.auth.api_key, '${MY_KEY}');
});

test('buildManifest - creates valid Router config', () => {
  const models = {
    default: { id: 'model-a', config: {} },
    background: { id: 'model-b', config: {} },
    think: { id: 'model-c', config: {} },
    longContext: { id: 'model-d', config: {} }
  };
  
  const manifest = bridge.buildManifest(models);
  
  assert.equal(manifest.version, '1.0.0');
  assert.ok(manifest.Router);
  assert.ok(manifest.Router.default);
  assert.ok(manifest.Providers);
});

test('buildManifest - throws without default model', () => {
  const models = {
    background: { id: 'model-b', config: {} }
  };
  
  assert.throws(() => {
    bridge.buildManifest(models);
  }, /default required/);
});

test('buildManifest - includes Providers array', () => {
  const models = {
    default: { id: 'model-a', config: {} }
  };
  
  const manifest = bridge.buildManifest(models);
  
  assert.ok(Array.isArray(manifest.Providers));
  assert.ok(manifest.Providers.length > 0);
});

