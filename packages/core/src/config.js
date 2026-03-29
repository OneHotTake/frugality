const fs = require('fs');
const path = require('path');
const os = require('os');

const defaults = {
  CONFIG_DIR: path.join(process.env.HOME || os.homedir(), '.frugality'),
  CONFIG_FILE: 'config.json'
};

const defaultConfig = {
  version: '0.2.0',
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
      return { ...defaultConfig, ...loaded, _path: configPath, _isDefault: false };
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
  }
};

module.exports = config;
