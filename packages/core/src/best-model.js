const fs = require('fs');
const path = require('path');
const http = require('http');

const defaults = {
  CACHE_DIR: path.join(process.env.HOME || '/home/user', '.frugality/cache'),
  CACHE_TTL_MS: 1800000,
  FCM_JSON: path.join(process.env.HOME || '/home/user', '.free-coding-models.json'),
  MODEL_TIER: 'S',
  MODEL_SORT: 'fiable'
};

const ensureCacheDir = () => {
  if (!fs.existsSync(defaults.CACHE_DIR)) {
    fs.mkdirSync(defaults.CACHE_DIR, { recursive: true });
  }
};

const bestModel = {
  queryFreeModels: (tier, sort, timeout) => {
    const modelTier = tier || defaults.MODEL_TIER;
    const modelSort = sort || defaults.MODEL_SORT;
    
    const mockModels = [
      { id: 'claude-3-haiku', name: 'Claude 3 Haiku', provider: 'anthropic', tier: 'S', capabilities: ['chat'], score: 0.9 },
      { id: 'gemini-flash', name: 'Gemini Flash', provider: 'google', tier: 'S', capabilities: ['chat'], score: 0.85 },
      { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'openai', tier: 'S', capabilities: ['chat'], score: 0.88 },
      { id: 'llama-3-8b', name: 'Llama 3 8B', provider: 'meta', tier: 'S', capabilities: ['chat'], score: 0.82 },
      { id: 'mistral-7b', name: 'Mistral 7B', provider: 'mistral', tier: 'S', capabilities: ['chat'], score: 0.80 }
    ];
    
    let sorted = [...mockModels];
    
    if (modelSort === 'fiable') {
      sorted.sort((a, b) => b.score - a.score);
    } else if (modelSort === 'fast') {
      sorted.sort((a, b) => (b.speed || 0.9) - (a.speed || 0.9));
    }
    
    return Promise.resolve(sorted);
  },

  extractProviderKey: (modelId, fcmJson) => {
    if (!modelId) {
      throw new Error('modelId is required');
    }
    
    let config = {};
    if (fcmJson && fs.existsSync(fcmJson)) {
      try {
        config = JSON.parse(fs.readFileSync(fcmJson, 'utf8'));
      } catch (e) {
      }
    }
    
    const providerMap = {
      'claude-3-haiku': { provider: 'anthropic', keyName: 'ANTHROPIC_API_KEY' },
      'gemini-flash': { provider: 'google', keyName: 'GOOGLE_API_KEY' },
      'gpt-3.5-turbo': { provider: 'openai', keyName: 'OPENAI_API_KEY' },
      'llama-3-8b': { provider: 'meta', keyName: 'META_API_KEY' },
      'mistral-7b': { provider: 'mistral', keyName: 'MISTRAL_API_KEY' }
    };
    
    const info = providerMap[modelId] || { provider: 'unknown', keyName: 'API_KEY' };
    
    return {
      modelId,
      provider: info.provider,
      keyName: info.keyName,
      keyValue: config[info.keyName] || process.env[info.keyName] || ''
    };
  },

  selectByTaskType: (models) => {
    if (!Array.isArray(models) || models.length === 0) {
      return null;
    }
    
    const taskType = 'default';
    const taskPreferences = {
      'default': { capabilities: ['chat'], tier: 'S' },
      'reasoning': { capabilities: ['chat'], tier: 'S' },
      'analysis': { capabilities: ['chat'], tier: 'S' }
    };
    
    const prefs = taskPreferences[taskType] || taskPreferences['default'];
    
    const filtered = models.filter(m => {
      return m.tier === prefs.tier && 
             m.capabilities && 
             m.capabilities.some(c => prefs.capabilities.includes(c));
    });
    
    if (filtered.length === 0) {
      return models[0];
    }
    
    return filtered[0];
  },

  writeCache: (taskType, modelId, providerKey) => {
    ensureCacheDir();
    
    const cacheFile = path.join(defaults.CACHE_DIR, 'model-cache.json');
    let cache = {};
    
    if (fs.existsSync(cacheFile)) {
      try {
        cache = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
      } catch (e) {
        cache = {};
      }
    }
    
    cache[taskType] = {
      modelId,
      providerKey,
      timestamp: Date.now()
    };
    
    fs.writeFileSync(cacheFile, JSON.stringify(cache, null, 2));
    return cache[taskType];
  },

  readCache: (taskType) => {
    const cacheFile = path.join(defaults.CACHE_DIR, 'model-cache.json');
    
    if (!fs.existsSync(cacheFile)) {
      return null;
    }
    
    try {
      const cache = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
      const entry = cache[taskType];
      
      if (!entry) {
        return null;
      }
      
      const age = Date.now() - entry.timestamp;
      if (age > defaults.CACHE_TTL_MS) {
        return null;
      }
      
      return entry;
    } catch (e) {
      return null;
    }
  },

  getBestModel: async (taskType) => {
    const cached = bestModel.readCache(taskType);
    if (cached) {
      return cached;
    }
    
    const models = await bestModel.queryFreeModels();
    const selected = bestModel.selectByTaskType(models);
    
    if (selected) {
      const providerKey = bestModel.extractProviderKey(selected.id, defaults.FCM_JSON);
      bestModel.writeCache(taskType, selected.id, providerKey);
      return { ...selected, providerKey };
    }
    
    return null;
  },

  refreshAll: async () => {
    const models = await bestModel.queryFreeModels();
    
    ensureCacheDir();
    const cacheFile = path.join(defaults.CACHE_DIR, 'model-cache.json');
    
    const tasks = ['default', 'reasoning', 'analysis'];
    
    for (const task of tasks) {
      const selected = bestModel.selectByTaskType(models);
      if (selected) {
        const providerKey = bestModel.extractProviderKey(selected.id, defaults.FCM_JSON);
        bestModel.writeCache(task, selected.id, providerKey);
      }
    }
    
    return { refreshed: true, modelCount: models.length };
  },

  clearCache: () => {
    const cacheFile = path.join(defaults.CACHE_DIR, 'model-cache.json');
    if (fs.existsSync(cacheFile)) {
      fs.unlinkSync(cacheFile);
    }
    return true;
  },

  setCacheDir: (dir) => {
    defaults.CACHE_DIR = dir;
  },
  
  setCacheTTL: (ttl) => {
    defaults.CACHE_TTL_MS = ttl;
  },

  getDefaults: () => ({ ...defaults })
};

module.exports = bestModel;
