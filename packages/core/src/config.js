const fs = require('fs');
const path = require('path');
const os = require('os');

const defaults = {
  CONFIG_DIR: path.join(process.env.HOME || os.homedir(), '.frugality'),
  CONFIG_FILE: 'config.json'
};

const defaultConfig = {
  version: '0.3.0',
  mode: 'agentic',
  autoStart: false,
  notifications: true,
  watchdog: {
    enabled: true,
    intervalMs: 300000,
    maxRestartAttempts: 3
  },
  idleWatcher: {
    enabled: true,
    pollIntervalMs: 10000
  },
  cache: {
    ttlMs: 1800000,
    autoRefresh: true
  },
  models: {
    defaultTier: 'S',
    sortBy: 'fiable',
    fallbacks: {
      fast: 'zen@grok-code',
      analysis: 'g@gemini-3-pro-preview',
      reasoning: 'or@deepseek/deepseek-v3.2'
    }
  },
  // Hybrid mode: main orchestrator uses subscription; agents use free cache models
  hybrid: {
    enabled: false,
    mainModel: 'claude-sonnet-4-6',
    agentModels: {
      fast: null,      // null → read from ~/.frugality/cache/best-model-fast.txt
      analysis: null,  // null → read from ~/.frugality/cache/best-model-analysis.txt
      reasoning: null  // null → read from ~/.frugality/cache/best-model-reasoning.txt
    },
    writeTemplate: true
  },
  logging: {
    level: 'info',
    maxSizeBytes: 5242880
  }
};

const config = {
  load: () => {
    const configPath = path.join(defaults.CONFIG_DIR, defaults.CONFIG_FILE);

    if (!fs.existsSync(defaults.CONFIG_DIR)) {
      fs.mkdirSync(defaults.CONFIG_DIR, { recursive: true });
    }

    if (!fs.existsSync(configPath)) {
      fs.writeFileSync(configPath, JSON.stringify(defaultConfig, null, 2));
      return { ...defaultConfig, _path: configPath, _isDefault: true };
    }

    try {
      const loaded = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      // Deep-merge to pick up new defaultConfig keys added in later versions
      const merged = config._deepMerge(defaultConfig, loaded);
      return { ...merged, _path: configPath, _isDefault: false };
    } catch (e) {
      return { ...defaultConfig, _path: configPath, _isDefault: true, _error: e.message };
    }
  },

  save: (configData) => {
    const configPath = path.join(defaults.CONFIG_DIR, defaults.CONFIG_FILE);

    if (!fs.existsSync(defaults.CONFIG_DIR)) {
      fs.mkdirSync(defaults.CONFIG_DIR, { recursive: true });
    }

    const toSave = { ...configData };
    delete toSave._path;
    delete toSave._isDefault;
    delete toSave._error;

    fs.writeFileSync(configPath, JSON.stringify(toSave, null, 2));
    return { saved: true, path: configPath };
  },

  get: (key) => {
    const cfg = config.load();
    if (!key) return cfg;

    const keys = key.split('.');
    let value = cfg;
    for (const k of keys) {
      value = value?.[k];
    }
    return value;
  },

  set: (key, value) => {
    const cfg = config.load();
    const keys = key.split('.');

    let current = cfg;
    for (let i = 0; i < keys.length - 1; i++) {
      if (!current[keys[i]]) {
        current[keys[i]] = {};
      }
      current = current[keys[i]];
    }
    current[keys[keys.length - 1]] = value;

    return config.save(cfg);
  },

  reset: () => {
    return config.save(defaultConfig);
  },

  getPath: () => {
    return path.join(defaults.CONFIG_DIR, defaults.CONFIG_FILE);
  },

  exists: () => {
    return fs.existsSync(path.join(defaults.CONFIG_DIR, defaults.CONFIG_FILE));
  },

  init: (options = {}) => {
    const cfg = {
      ...defaultConfig,
      ...options,
      _initialized: true,
      _initTime: new Date().toISOString()
    };
    return config.save(cfg);
  },

  // Shallow-first deep merge: defaults are the base; loaded values override.
  // Ensures new top-level keys added to defaultConfig are always present.
  _deepMerge: (base, override) => {
    const result = { ...base };
    for (const key of Object.keys(override)) {
      if (
        override[key] !== null &&
        typeof override[key] === 'object' &&
        !Array.isArray(override[key]) &&
        typeof base[key] === 'object' &&
        base[key] !== null
      ) {
        result[key] = config._deepMerge(base[key], override[key]);
      } else {
        result[key] = override[key];
      }
    }
    return result;
  }
};

module.exports = config;
