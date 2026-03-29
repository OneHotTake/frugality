/**
 * hybrid.js — Hybrid mode support for Frugality.
 *
 * Hybrid mode lets the main Claude Code session run on an Anthropic
 * subscription while every delegated sub-agent uses the best available
 * free-tier model from the local cache.
 *
 * State file:  ~/.frugality/state/hybrid-mode  (JSON)
 * Template:    written to cwd/HYBRID.md on `frug init --hybrid`
 */

const fs = require('fs');
const path = require('path');

const defaults = {
  CACHE_DIR:    path.join(process.env.HOME || '/home/user', '.frugality/cache'),
  STATE_DIR:    path.join(process.env.HOME || '/home/user', '.frugality/state'),
  TEMPLATE_DIR: path.join(process.env.HOME || '/home/user', '.frugality'),
  FALLBACK_MODELS: {
    main:      'claude-sonnet-4-6',
    fast:      'claude-3-haiku',
    analysis:  'gemini-2.0-flash',
    reasoning: 'deepseek-chat',
    default:   'claude-3-haiku'
  }
};

const hybrid = {
  // The model used by the main orchestrator (subscription-backed).
  getMainModel: () => {
    return process.env.FRUGALITY_MAIN_MODEL || defaults.FALLBACK_MODELS.main;
  },

  // The best free model for a specific agent task type.
  // Falls back gracefully: typed cache → default cache → hardcoded fallback.
  getAgentModel: (taskType) => {
    const type = (taskType || 'default').toLowerCase();
    const cacheFile = path.join(defaults.CACHE_DIR, `best-model-${type}.txt`);

    if (fs.existsSync(cacheFile)) {
      try {
        const model = fs.readFileSync(cacheFile, 'utf8').trim();
        if (model) return model;
      } catch (e) {
        // fall through
      }
    }

    // Try the generic default cache before using hardcoded fallback
    const defaultFile = path.join(defaults.CACHE_DIR, 'best-model-default.txt');
    if (fs.existsSync(defaultFile)) {
      try {
        const model = fs.readFileSync(defaultFile, 'utf8').trim();
        if (model) return model;
      } catch (e) {
        // fall through
      }
    }

    return defaults.FALLBACK_MODELS[type] || defaults.FALLBACK_MODELS.fast;
  },

  // Build a complete hybrid configuration object (for display / state file).
  buildHybridConfig: () => {
    return {
      mode: 'hybrid',
      main: {
        model: hybrid.getMainModel(),
        source: process.env.FRUGALITY_MAIN_MODEL ? 'env' : 'default',
        note: 'Uses Anthropic subscription for thinking and orchestrating'
      },
      agents: {
        fast:      hybrid.getAgentModel('fast'),
        analysis:  hybrid.getAgentModel('analysis'),
        reasoning: hybrid.getAgentModel('reasoning'),
        default:   hybrid.getAgentModel('default'),
        note: 'Uses free-tier models from ~/.frugality/cache/ for all delegated tasks'
      },
      taskRouting: {
        BOILERPLATE:  'fast',
        TESTS:        'fast',
        DOCS:         'fast',
        ANALYSIS:     'analysis',
        REASONING:    'reasoning',
        ARCHITECTURE: 'main'   // keep architecture decisions with the main model
      }
    };
  },

  // Persist hybrid mode state to disk.
  writeHybridState: (opts) => {
    const options = opts || {};

    if (!fs.existsSync(defaults.STATE_DIR)) {
      fs.mkdirSync(defaults.STATE_DIR, { recursive: true });
    }

    const stateFile = path.join(defaults.STATE_DIR, 'hybrid-mode');
    const config = hybrid.buildHybridConfig();
    const state = {
      ...config,
      startedAt: new Date().toISOString(),
      version: options.version || '0.3.0'
    };

    fs.writeFileSync(stateFile, JSON.stringify(state, null, 2));
    return state;
  },

  readHybridState: () => {
    const stateFile = path.join(defaults.STATE_DIR, 'hybrid-mode');

    if (!fs.existsSync(stateFile)) {
      return null;
    }

    try {
      return JSON.parse(fs.readFileSync(stateFile, 'utf8'));
    } catch (e) {
      return null;
    }
  },

  clearHybridState: () => {
    const stateFile = path.join(defaults.STATE_DIR, 'hybrid-mode');
    if (fs.existsSync(stateFile)) {
      fs.unlinkSync(stateFile);
    }
    return true;
  },

  isHybridMode: () => {
    return fs.existsSync(path.join(defaults.STATE_DIR, 'hybrid-mode'));
  },

  // Generate a HYBRID.md document tailored to the current cache state.
  getHybridTemplate: () => {
    const mainModel     = hybrid.getMainModel();
    const fastModel     = hybrid.getAgentModel('fast');
    const analysisModel = hybrid.getAgentModel('analysis');
    const reasonModel   = hybrid.getAgentModel('reasoning');

    return `# Frugality — Hybrid Mode

You are running in **hybrid mode**:
- **You** (the main orchestrator) use your Anthropic subscription model (\`${mainModel}\`) for thinking, planning, and architecture.
- **Sub-agents** you spawn use the best available free-tier models for cost optimization.

## Current Agent Models

| Task Type | Model | When to Use |
|-----------|-------|-------------|
| Fast | \`${fastModel}\` | Boilerplate, tests, docs, <400 tokens |
| Analysis | \`${analysisModel}\` | Large files (>500 lines), logs, audits |
| Reasoning | \`${reasonModel}\` | Complex bugs, cross-file refactors, design |

## Task Routing Rules

### Keep With Your Subscription (Do Not Delegate)
- Architecture decisions affecting 2+ modules
- Root cause analysis for unknown bugs
- Cross-cutting refactors touching 3+ files
- Security review
- API design
- Final review before any commit

### Delegate to Free Agent (Immediate Delegation)
- Writing or updating tests (unit, integration, e2e)
- Writing documentation (JSDoc, README sections, inline comments)
- Generating boilerplate (CRUD, scaffolding, migration scripts)
- Single-file analysis or explanation
- Type generation, interface extraction
- Linting / formatting fixes
- Log file analysis
- Dependency audits

## Reading the Cache Before Spawning

Before spawning any sub-agent, read the current best models:

\`\`\`bash
FAST_MODEL=\$(cat ~/.frugality/cache/best-model-fast.txt 2>/dev/null || echo "${fastModel}")
ANALYSIS_MODEL=\$(cat ~/.frugality/cache/best-model-analysis.txt 2>/dev/null || echo "${analysisModel}")
REASON_MODEL=\$(cat ~/.frugality/cache/best-model-reasoning.txt 2>/dev/null || echo "${reasonModel}")
\`\`\`

Refresh the cache if stale (>30 min):

\`\`\`bash
frug update
\`\`\`

## Failure Recovery

| Failure | Action |
|---------|--------|
| Agent timeout | Retry once with faster model |
| Rate limit | Switch to next model tier |
| Cache stale | Run \`frug update\`, use hardcoded fallback |
| Network down | Queue task, retry on reconnect |

---

*Generated by Frugality — Cost-Optimized AI Development*
`;
  },

  // Write the hybrid template to a file (typically cwd/HYBRID.md).
  writeTemplate: (targetPath) => {
    const dir = path.dirname(targetPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(targetPath, hybrid.getHybridTemplate());
    return targetPath;
  },

  // ---- Test helpers ----

  setCacheDir: (dir) => {
    defaults.CACHE_DIR = dir;
  },

  setStateDir: (dir) => {
    defaults.STATE_DIR = dir;
  },

  getFallbackModels: () => ({ ...defaults.FALLBACK_MODELS }),

  getDefaults: () => ({ ...defaults })
};

module.exports = hybrid;
