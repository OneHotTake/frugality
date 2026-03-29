# API Reference

## Core Modules

### bridge

Manages model presets and configurations.

```javascript
const bridge = require('packages/core/src/bridge');
```

#### buildProviderConfig(modelId, providerKeyName, baseUrl)

Builds a provider configuration object.

**Parameters:**
- `modelId` (string): Model identifier
- `providerKeyName` (string): API key environment variable name
- `baseUrl` (string, optional): Base URL for API

**Returns:** Object with model configuration

**Example:**
```javascript
const config = bridge.buildProviderConfig('claude-3-haiku', 'ANTHROPIC_API_KEY');
// { modelId: 'claude-3-haiku', providerKeyName: 'ANTHROPIC_API_KEY', baseUrl: '...', config: {} }
```

#### buildManifest(models)

Creates a manifest from an array of models.

**Parameters:**
- `models` (Array): Array of model objects

**Returns:** Manifest object with version and models

**Example:**
```javascript
const manifest = bridge.buildManifest([
  { id: 'claude-3-haiku', provider: 'anthropic', tier: 'S' }
]);
```

#### writeManifest(manifest, presetName, staging)

Writes a manifest to the presets directory.

**Parameters:**
- `manifest` (Object): Manifest to write
- `presetName` (string): Preset name
- `staging` (boolean, optional): Write to staging directory

**Returns:** Path to written manifest

#### promoteStaged(presetName)

Promotes a staged preset to active.

**Parameters:**
- `presetName` (string): Preset name

**Returns:** Path to active preset directory

#### installPreset(presetName)

Installs a new preset.

**Parameters:**
- `presetName` (string): Preset name

**Returns:** Path to preset directory

#### runBridge(opts)

Runs the bridge with options.

**Parameters:**
- `opts` (Object): Options object
  - `preset` (string): Preset name
  - `models` (Array): Model array
  - `staging` (boolean): Use staging

**Returns:** Result object with status

---

### safe-restart

Handles safe restarts of the CCR.

```javascript
const safeRestart = require('packages/core/src/safe-restart');
```

#### getActiveConnections(port)

Checks for active connections on CCR port.

**Parameters:**
- `port` (number, optional): Port to check

**Returns:** Promise resolving to { count, healthy }

#### isRequestInFlight(logPath, timeoutSeconds)

Checks if a request is in flight based on log file age.

**Parameters:**
- `logPath` (string, optional): Path to log file
- `timeoutSeconds` (number, optional): Timeout in seconds

**Returns:** Boolean

#### isIdle()

Checks if the system is idle.

**Returns:** Promise resolving to boolean

#### setPendingRestart(reason)

Sets a pending restart.

**Parameters:**
- `reason` (string): Restart reason

**Returns:** Restart data object

#### clearPendingRestart()

Clears pending restart.

**Returns:** Boolean

#### hasPendingRestart()

Checks if there's a pending restart.

**Returns:** Boolean

#### getPendingRestart()

Gets pending restart data.

**Returns:** Restart data object or null

#### restartCCR()

Initiates CCR restart.

**Returns:** Result object { success, message/error }

#### verifyCCRHealth(port, timeout)

Verifies CCR health.

**Parameters:**
- `port` (number, optional): Port to check
- `timeout` (number, optional): Timeout in ms

**Returns:** Promise resolving to { healthy, statusCode/error }

#### safeRestart(opts)

Performs a safe restart.

**Parameters:**
- `opts` (Object): Options
  - `force` (boolean): Force restart
  - `reason` (string): Restart reason

**Returns:** Result object { status, reason/error }

---

### best-model

Model selection and caching.

```javascript
const bestModel = require('packages/core/src/best-model');
```

#### queryFreeModels(tier, sort, timeout)

Queries available free models.

**Parameters:**
- `tier` (string, optional): Model tier
- `sort` (string, optional): Sort order
- `timeout` (number, optional): Timeout in ms

**Returns:** Promise resolving to model array

#### extractProviderKey(modelId, fcmJson)

Extracts provider key for a model.

**Parameters:**
- `modelId` (string): Model ID
- `fcmJson` (string, optional): Path to fcm.json

**Returns:** Object with provider, keyName, keyValue

#### selectByTaskType(models)

Selects the best model for the current task type.

**Parameters:**
- `models` (Array): Model array

**Returns:** Selected model or null

#### writeCache(taskType, modelId, providerKey)

Writes model to cache.

**Parameters:**
- `taskType` (string): Task type
- `modelId` (string): Model ID
- `providerKey` (Object): Provider key info

**Returns:** Cached entry

#### readCache(taskType)

Reads model from cache.

**Parameters:**
- `taskType` (string): Task type

**Returns:** Cached entry or null

#### getBestModel(taskType)

Gets the best model for a task.

**Parameters:**
- `taskType` (string): Task type

**Returns:** Promise resolving to model object

#### refreshAll()

Refreshes all model caches.

**Returns:** Promise resolving to result object

#### clearCache()

Clears the model cache.

**Returns:** Boolean

---

### idle-watcher

Monitors for idle state and applies pending actions.

```javascript
const idleWatcher = require('packages/core/src/idle-watcher');
```

#### checkAndApplyPending()

Checks and applies pending restart/config.

**Returns:** Pending action object or null

#### rotateLogs()

Rotates log files if they exceed max size.

**Returns:** Result object { rotated, archivePath/error }

#### start(opts)

Starts the idle watcher.

**Parameters:**
- `opts` (Object): Options
  - `pollInterval` (number): Poll interval in ms

**Returns:** Result object { started, pollInterval }

#### stop()

Stops the idle watcher.

**Returns:** Result object { stopped, reason }

#### isRunning()

Checks if idle watcher is running.

**Returns:** Boolean

#### setPendingConfig(config)

Sets pending configuration.

**Parameters:**
- `config` (Object): Configuration data

**Returns:** Config data object

#### clearPendingConfig()

Clears pending configuration.

**Returns:** Boolean

---

### watchdog

Health monitoring for CCR.

```javascript
const watchdog = require('packages/watchdog/src/watchdog');
```

#### pingCurrentModel()

Pings the current model.

**Returns:** Promise resolving to { healthy, statusCode/error, timestamp }

#### checkCCRProcess()

Checks if CCR process is running.

**Returns:** Result object { running, pid/reason }

#### handleUnhealthy(reason)

Handles unhealthy model.

**Parameters:**
- `reason` (string): Unhealthy reason

**Returns:** Promise resolving to action result

#### handleCCRDown(attempt)

Handles CCR being down.

**Parameters:**
- `attempt` (number): Restart attempt number

**Returns:** Action result object

#### mainLoop()

Runs the main watchdog loop.

**Returns:** Promise resolving to status object

#### start(opts)

Starts the watchdog.

**Parameters:**
- `opts` (Object): Options
  - `interval` (number): Check interval in ms

**Returns:** Result object { started, interval }

#### stop()

Stops the watchdog.

**Returns:** Result object { stopped, reason }

#### status()

Gets watchdog status.

**Returns:** Status object

#### rotateLogs()

Rotates watchdog logs.

**Returns:** Result object { rotated, archivePath/error }

#### resetRestartAttempts()

Resets restart attempt counter.

**Returns:** Result object { reset }

---

### CLI

Main CLI interface.

```javascript
const frug = require('bin/frug');
```

#### run(args)

Runs a CLI command.

**Parameters:**
- `args` (Array): Command arguments

**Returns:** Promise resolving to command result

**Example:**
```javascript
const result = await frug.run(['status']);
console.log(result);

// Start hybrid mode
const r = await frug.run(['start', '--hybrid']);
// { success: true, mode: 'hybrid', mainModel: 'claude-sonnet-4-6', ... }
```

---

### hybrid

Hybrid mode support — subscription orchestrator + free-model agents.

```javascript
const hybrid = require('packages/core/src/hybrid');
```

#### getMainModel()

Returns the model for the main orchestrator. Reads `FRUGALITY_MAIN_MODEL` env var, falls back to `claude-sonnet-4-6`.

**Returns:** `string`

#### getAgentModel(taskType)

Returns the best free model for the given task type by reading `~/.frugality/cache/best-model-<taskType>.txt`. Falls back to the default cache file, then to hardcoded defaults.

**Parameters:**
- `taskType` (string): `'fast'` | `'analysis'` | `'reasoning'` | `'default'`

**Returns:** `string` — model identifier

**Example:**
```javascript
const fastModel = hybrid.getAgentModel('fast');
// 'claude-3-haiku'  (or whatever is in the cache)
```

#### buildHybridConfig()

Builds a complete hybrid config object showing main and agent models plus the task routing table.

**Returns:** Object with `mode`, `main`, `agents`, `taskRouting`

#### writeHybridState(opts)

Persists hybrid mode config to `~/.frugality/state/hybrid-mode`.

**Parameters:**
- `opts.version` (string, optional): Version string to embed

**Returns:** The state object written

#### readHybridState()

Reads the current hybrid state file.

**Returns:** State object or `null` if not in hybrid mode

#### clearHybridState()

Deletes the hybrid-mode state file.

#### isHybridMode()

**Returns:** `boolean` — true if the hybrid-mode state file exists

#### writeTemplate(targetPath)

Writes a populated `HYBRID.md` document to `targetPath`.

**Parameters:**
- `targetPath` (string): Absolute path to write to

**Returns:** `targetPath`

#### setCacheDir(dir) / setStateDir(dir)

Override cache/state directories (for testing).
