const fs = require('fs');
const path = require('path');

const bestModel = {
  queryFreeModels: (tier, sort, timeout) => {
    // Implement queryFreeModels function
  },
  extractProviderKey: (modelId, fcmJson) => {
    // Implement extractProviderKey function
  },
  selectByTaskType: (models) => {
    // Implement selectByTaskType function
  },
  writeCache: (taskType, modelId, providerKey) => {
    // Implement writeCache function
  },
  readCache: (taskType) => {
    // Implement readCache function
  },
  getBestModel: (taskType) => {
    // Implement getBestModel function
  },
  refreshAll: () => {
    // Implement refreshAll function
  }
};

module.exports = bestModel;
