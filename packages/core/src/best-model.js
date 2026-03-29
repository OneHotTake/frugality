'use strict';

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const defaults = require('../../../config/defaults');

const bestModel = {
  queryFreeModels: (tier, sort) => {
    try {
      const modelTier = tier || defaults.MODEL_TIER;
      const cmd = `free-coding-models --tier ${modelTier} --json 2>&1`;
      const output = execSync(cmd, { timeout: 30000, encoding: 'utf8' });
      const jsonMatch = output.match(/\[[\s\S]*\]/);
      if (!jsonMatch) throw new Error('No JSON output from free-coding-models');
      const models = JSON.parse(jsonMatch[0]);
      if (!Array.isArray(models) || models.length === 0) throw new Error('Empty model list');
      return models;
    } catch (err) {
      throw new Error(`Failed to query free-coding-models: ${err.message}`);
    }
  },

  extractProviderKey: (modelId, fcmJson) => {
    try {
      if (!fs.existsSync(fcmJson)) return null;
      const fcm = JSON.parse(fs.readFileSync(fcmJson, 'utf8'));
      if (!fcm.apiKeys) return null;
      
      const providerMap = {
        'nvidia': 'nvidia', 'groq': 'groq', 'cerebras': 'cerebras',
        'sambanova': 'sambanova', 'openrouter': 'openrouter'
      };

      let provider = null;
      for (const [key, val] of Object.entries(providerMap)) {
        if (modelId.toLowerCase().includes(key)) {
          provider = val;
          break;
        }
      }

      if (!provider) return null;
      const keyValue = fcm.apiKeys[provider];
      if (!keyValue) return null;
      return { keyName: provider.toUpperCase() + '_API_KEY', keyValue };
    } catch (err) {
      return null;
    }
  },

  selectByTaskType: (models, taskType) => {
    if (!models || models.length === 0) return null;
    const sorted = [...models].sort((a, b) => (b.sweScore || 0) - (a.sweScore || 0));
    
    switch (taskType) {
      case 'fast':
        return sorted.find(m => m.tier && (m.tier === 'A+' || m.tier === 'A')) || sorted[0];
      case 'analysis':
        const withGemini = sorted.find(m => m.provider && m.provider.includes('gemini'));
        return withGemini || sorted.find(m => m.tier === 'S') || sorted[0];
      case 'reasoning':
        return sorted.find(m => m.tier && (m.tier === 'S+' || m.tier === 'S')) || sorted[0];
      default:
        return sorted.find(m => m.tier === 'S') || sorted[0];
    }
  },

  writeCache: (taskType, modelId, providerKey) => {
    try {
      if (!fs.existsSync(defaults.CACHE_DIR)) {
        fs.mkdirSync(defaults.CACHE_DIR, { recursive: true });
      }
      const cacheFile = path.join(defaults.CACHE_DIR, `best-model-${taskType}.txt`);
      const tempFile = cacheFile + '.tmp';
      const content = providerKey ? `${modelId}\n${providerKey}` : modelId;
      fs.writeFileSync(tempFile, content, 'utf8');
      fs.renameSync(tempFile, cacheFile);
    } catch (err) {
      console.error(`Failed to write cache for ${taskType}: ${err.message}`);
    }
  },

  readCache: (taskType) => {
    try {
      const cacheFile = path.join(defaults.CACHE_DIR, `best-model-${taskType}.txt`);
      if (!fs.existsSync(cacheFile)) return null;
      const stat = fs.statSync(cacheFile);
      const age = Date.now() - stat.mtimeMs;
      if (age > defaults.CACHE_TTL_MS) return null;
      const content = fs.readFileSync(cacheFile, 'utf8').trim();
      return content || null;
    } catch (err) {
      return null;
    }
  },

  refreshAll: async () => {
    try {
      const models = bestModel.queryFreeModels();
      if (!models || models.length === 0) throw new Error('No models available');

      const taskTypes = ['default', 'fast', 'analysis', 'reasoning'];
      const results = {};

      for (const taskType of taskTypes) {
        const selected = bestModel.selectByTaskType(models, taskType);
        if (selected) {
          // Handle both modelId and id properties
          const modelId = selected.modelId || selected.id || JSON.stringify(selected).substring(0, 50);
          const providerKey = bestModel.extractProviderKey(modelId, defaults.FCM_JSON);
          bestModel.writeCache(taskType, modelId, providerKey ? providerKey.keyName : null);
          results[taskType] = modelId;
        }
      }
      return { success: true, updated: results };
    } catch (err) {
      throw err;
    }
  },

  getBestModel: (taskType) => {
    const cached = bestModel.readCache(taskType);
    if (cached) return cached;
    try {
      const models = bestModel.queryFreeModels();
      const selected = bestModel.selectByTaskType(models, taskType);
      if (selected) {
        // Handle both modelId and id properties
        const modelId = selected.modelId || selected.id || JSON.stringify(selected).substring(0, 50);
        const providerKey = bestModel.extractProviderKey(modelId, defaults.FCM_JSON);
        bestModel.writeCache(taskType, modelId, providerKey ? providerKey.keyName : null);
        return modelId;
      }
    } catch (err) {
      return null;
    }
    return null;
  }
};

module.exports = bestModel;
