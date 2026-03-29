const fs = require('fs');
const path = require('path');

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

    // Mock data with speed and reasoning_score for task-type routing.
    // Replace this with a real free-coding-models API call when available.
    const mockModels = [
      { id: 'claude-3-haiku',  name: 'Claude 3 Haiku',  provider: 'anthropic', tier: 'S', capabilities: ['chat'], score: 0.90, speed: 0.95, reasoning_score: 0.85 },
      { id: 'gemini-flash',    name: 'Gemini Flash',    provider: 'google',    tier: 'S', capabilities: ['chat'], score: 0.85, speed: 0.92, reasoning_score: 0.80 },
      { id: 'gpt-3.5-turbo',  name: 'GPT-3.5 Turbo',  provider: 'openai',    tier: 'S', capabilities: ['chat'], score: 0.88, speed: 0.88, reasoning_score: 0.82 },
      { id: 'llama-3-8b',     name: 'Llama 3 8B',      provider: 'meta',      tier: 'S', capabilities: ['chat'], score: 0.82, speed: 0.90, reasoning_score: 0.78 },
      { id: 'mistral-7b',     name: 'Mistral 7B',      provider: 'mistral',   tier: 'S', capabilities: ['chat'], score: 0.80, speed: 0.85, reasoning_score: 0.83 }
    ];

    let sorted = [...mockModels];

    if (modelSort === 'fiable') {
      sorted.sort((a, b) => b.score - a.score);
    } else if (modelSort === 'fast') {
      sorted.sort((a, b) => (b.speed || 0) - (a.speed || 0));
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
        // use empty config on parse failure
      }
    }

    const providerMap = {
      'claude-3-haiku': { provider: 'anthropic', keyName: 'ANTHROPIC_API_KEY' },
      'gemini-flash':   { provider: 'google',    keyName: 'GOOGLE_API_KEY'    },
      'gpt-3.5-turbo': { provider: 'openai',     keyName: 'OPENAI_API_KEY'    },
      'llama-3-8b':    { provider: 'meta',        keyName: 'META_API_KEY'      },
      'mistral-7b':    { provider: 'mistral',     keyName: 'MISTRAL_API_KEY'   }
    };

    const info = providerMap[modelId] || { provider: 'unknown', keyName: 'API_KEY' };

    return {
      modelId,
      provider: info.provider,
      keyName: info.keyName,
      keyValue: config[info.keyName] || process.env[info.keyName] || ''
    };
  },

  // Select the best model for a given task type.
  // taskType: 'fast' | 'boilerplate' | 'tests' | 'docs' | 'analysis' | 'reasoning' | 'default'
  selectByTaskType: (models, taskType) => {
    if (!Array.isArray(models) || models.length === 0) {
      return null;
    }

    const type = (taskType || 'default').toLowerCase();
    const sTier = models.filter(m => m.tier === 'S');
    const pool = sTier.length > 0 ? sTier : models;

    if (['fast', 'boilerplate', 'tests', 'docs'].includes(type)) {
      // Fastest model wins — minimise latency for cheap tasks
      return [...pool].sort((a, b) => (b.speed || b.score || 0) - (a.speed || a.score || 0))[0];
    }

    if (type === 'analysis') {
      // Highest overall quality for large-file / audit work
      return [...pool].sort((a, b) => (b.score || 0) - (a.score || 0))[0];
    }

    if (type === 'reasoning') {
      // Best reasoning capability for complex bugs / design decisions
      return [...pool].sort((a, b) => (b.reasoning_score || b.score || 0) - (a.reasoning_score || a.score || 0))[0];
    }

    // default: top score
    return [...pool].sort((a, b) => (b.score || 0) - (a.score || 0))[0];
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
    const selected = bestModel.selectByTaskType(models, taskType);

    if (selected) {
      const providerKey = bestModel.extractProviderKey(selected.id, defaults.FCM_JSON);
      bestModel.writeCache(taskType, selected.id, providerKey);
      return { ...selected, providerKey };
    }

    return null;
  },

  // Refresh all task-type caches, selecting the best model for each type.
  refreshAll: async () => {
    const models = await bestModel.queryFreeModels();

    ensureCacheDir();

    const tasks = ['default', 'fast', 'analysis', 'reasoning'];

    for (const task of tasks) {
      const selected = bestModel.selectByTaskType(models, task);
      if (selected) {
        const providerKey = bestModel.extractProviderKey(selected.id, defaults.FCM_JSON);
        bestModel.writeCache(task, selected.id, providerKey);
        fs.writeFileSync(path.join(defaults.CACHE_DIR, `best-model-${task}.txt`), selected.id);
      }
    }

    // Permanent fallback — never changes
    fs.writeFileSync(path.join(defaults.CACHE_DIR, 'best-model-fallback.txt'), 'zen@grok-code');

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
