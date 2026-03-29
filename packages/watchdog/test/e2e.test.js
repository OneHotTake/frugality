const assert = require('assert');
const path = require('path');
const fs = require('fs');
const { describe, it, before, after } = require('node:test');

describe('Watchdog Package E2E Tests', () => {
  const testDir = path.join(process.env.HOME || '/home/user', '.frugality-watchdog-test');
  const testStateDir = path.join(testDir, 'state');
  const testLogDir = path.join(testDir, 'logs');
  
  before(() => {
    process.env.HOME = testDir;
  });
  
  after(() => {
    if (fs.existsSync(testDir)) {
      fs.rmSync(testDir, { recursive: true, force: true });
    }
  });
  
  describe('watchdog module', () => {
    const watchdog = require('../src/watchdog');
    
    it('should ping current model', async () => {
      const result = await watchdog.pingCurrentModel();
      assert.strictEqual(typeof result.healthy, 'boolean');
      assert.strictEqual(typeof result.timestamp, 'number');
    });
    
    it('should check CCR process', () => {
      watchdog.setStateDir(testStateDir);
      const result = watchdog.checkCCRProcess();
      assert.strictEqual(typeof result.running, 'boolean');
      assert.strictEqual(typeof result.reason, 'string');
    });
    
    it('should handle unhealthy model', async () => {
      const result = await watchdog.handleUnhealthy('test reason');
      assert.strictEqual(typeof result.action, 'string');
    });
    
    it('should handle CCR down', () => {
      const result = watchdog.handleCCRDown(1);
      assert.strictEqual(result.action, 'retry');
      assert.strictEqual(result.attempt, 2);
    });
    
    it('should run main loop', async () => {
      watchdog.setStateDir(testStateDir);
      const result = await watchdog.mainLoop();
      assert.strictEqual(typeof result.status, 'string');
    });
    
    it('should start and stop', () => {
      watchdog.setStateDir(testStateDir);
      const startResult = watchdog.start({ interval: 1000 });
      assert.strictEqual(startResult.started, true);
      
      const status = watchdog.status();
      assert.strictEqual(status.running, true);
      
      const stopResult = watchdog.stop();
      assert.strictEqual(stopResult.stopped, true);
    });
    
    it('should rotate logs', () => {
      watchdog.setLogDir(testLogDir);
      const result = watchdog.rotateLogs();
      assert.strictEqual(typeof result.rotated, 'boolean');
    });
    
    it('should reset restart attempts', () => {
      const result = watchdog.resetRestartAttempts();
      assert.strictEqual(result.reset, true);
    });
  });
});
