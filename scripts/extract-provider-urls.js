#!/usr/bin/env node
const sources = require('/usr/lib/node_modules/free-coding-models/sources.js');
const providers = {};

// Extract providers that have URLs (exclude MODELS, gemini, rovo, etc.)
for (const [key, value] of Object.entries(sources)) {
  if (key !== 'MODELS' && value && value.url) {
    providers[key] = value.url;
  }
}

console.log(JSON.stringify(providers, null, 2));