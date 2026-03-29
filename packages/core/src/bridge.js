const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const defaults = {
  CCR_PRESETS_DIR: path.join(process.env.HOME || '/home/user', '.claude-code-router/presets'),
  CCR_CONFIG: path.join(process.env.HOME || '/home/user', '.claude-code-router/config.json'),
  MODEL_TIER: 'S',
  MODEL_SORT: 'fiable'
};

const bridge = {
  buildProviderConfig: (modelId, providerKeyName, baseUrl) => {
    if (!modelId) {
      throw new Error('modelId is required');
    }
    if (!providerKeyName) {
      throw new Error('providerKeyName is required');
    }
    
    return {
      modelId,
      providerKeyName,
      baseUrl: baseUrl || 'https://api.example.com',
      config: {}
    };
  },

  buildManifest: (models) => {
    if (!Array.isArray(models)) {
      throw new Error('models must be an array');
    }
    
    const manifest = {
      version: '1.0',
      models: models.map(m => ({
        id: m.id || m.modelId,
        name: m.name || m.id || m.modelId,
        provider: m.provider,
        tier: m.tier || defaults.MODEL_TIER,
        capabilities: m.capabilities || ['chat'],
        metadata: m.metadata || {}
      })),
      createdAt: new Date().toISOString()
    };
    
    return manifest;
  },

  writeManifest: (manifest, presetName, staging = false) => {
    if (!manifest) {
      throw new Error('manifest is required');
    }
    if (!presetName) {
      throw new Error('presetName is required');
    }
    
    const presetsDir = defaults.CCR_PRESETS_DIR;
    
    if (!fs.existsSync(presetsDir)) {
      fs.mkdirSync(presetsDir, { recursive: true });
    }
    
    const targetDir = staging 
      ? path.join(presetsDir, presetName, 'staging')
      : path.join(presetsDir, presetName);
    
    fs.mkdirSync(targetDir, { recursive: true });
    
    const manifestPath = path.join(targetDir, 'manifest.json');
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    
    return manifestPath;
  },

  promoteStaged: (presetName) => {
    if (!presetName) {
      throw new Error('presetName is required');
    }
    
    const presetsDir = defaults.CCR_PRESETS_DIR;
    const stagingDir = path.join(presetsDir, presetName, 'staging');
    const activeDir = path.join(presetsDir, presetName);
    
    if (!fs.existsSync(stagingDir)) {
      throw new Error(`Staging directory does not exist: ${stagingDir}`);
    }
    
    const stagedManifest = path.join(stagingDir, 'manifest.json');
    if (!fs.existsSync(stagedManifest)) {
      throw new Error('Staged manifest not found');
    }
    
    if (fs.existsSync(activeDir)) {
      const backupDir = path.join(presetsDir, presetName, `backup-${Date.now()}`);
      fs.renameSync(activeDir, backupDir);
    }
    
    fs.renameSync(stagingDir, activeDir);
    
    return activeDir;
  },

  installPreset: (presetName) => {
    if (!presetName) {
      throw new Error('presetName is required');
    }
    
    const presetsDir = defaults.CCR_PRESETS_DIR;
    const presetPath = path.join(presetsDir, presetName);
    
    if (!fs.existsSync(presetPath)) {
      fs.mkdirSync(presetPath, { recursive: true });
    }
    
    const manifestPath = path.join(presetPath, 'manifest.json');
    if (!fs.existsSync(manifestPath)) {
      const defaultManifest = {
        version: '1.0',
        models: [],
        installedAt: new Date().toISOString()
      };
      fs.writeFileSync(manifestPath, JSON.stringify(defaultManifest, null, 2));
    }
    
    return presetPath;
  },

  runBridge: (opts) => {
    const options = opts || {};
    const presetName = options.preset || 'default';
    const models = options.models || [];
    const staging = options.staging || false;
    
    const manifest = bridge.buildManifest(models);
    const manifestPath = bridge.writeManifest(manifest, presetName, staging);
    
    if (staging) {
      return {
        status: 'staged',
        manifestPath,
        presetName
      };
    }
    
    return {
      status: 'active',
      manifestPath,
      presetName
    };
  },

  getPresetsDir: () => defaults.CCR_PRESETS_DIR,
  
  setPresetsDir: (dir) => {
    defaults.CCR_PRESETS_DIR = dir;
  },
  
  getConfigPath: () => defaults.CCR_CONFIG,
  
  setConfigPath: (configPath) => {
    defaults.CCR_CONFIG = configPath;
  }
};

module.exports = bridge;
