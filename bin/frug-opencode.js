#!/usr/bin/env node

'use strict';

const { spawnSync } = require('child_process');
const frug = require('./frug');

async function main() {
  process.stderr.write('[frugality] Initializing...\n');
  try {
    await frug.run(['init']);
  } catch (err) {
    process.stderr.write('[frugality] Init error (continuing): ' + err.message + '\n');
  }

  process.stderr.write('[frugality] Starting hybrid mode for OpenCode...\n');
  await frug.run(['start', '--opencode', '--hybrid']);

  const args = process.argv.slice(2);
  const result = spawnSync('opencode', args, { stdio: 'inherit' });
  process.exit(result.status ?? 0);
}

main().catch(err => {
  process.stderr.write('[frugality] Error: ' + err.message + '\n');
  // Still try to launch opencode even if frugality init fails
  const args = process.argv.slice(2);
  const result = spawnSync('opencode', args, { stdio: 'inherit' });
  process.exit(result.status ?? 0);
});
