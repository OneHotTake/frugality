#!/usr/bin/env node

'use strict';

const { spawnSync } = require('child_process');
const frug = require('./frug');

async function main() {
  process.stderr.write('[frugality] Starting hybrid mode...\n');
  await frug.run(['start', '--hybrid']);

  const args = process.argv.slice(2);
  const result = spawnSync('claude', args, { stdio: 'inherit' });
  process.exit(result.status ?? 0);
}

main().catch(err => {
  process.stderr.write('[frugality] Error: ' + err.message + '\n');
  // Still try to launch claude even if frugality init fails
  const args = process.argv.slice(2);
  const result = spawnSync('claude', args, { stdio: 'inherit' });
  process.exit(result.status ?? 0);
});
