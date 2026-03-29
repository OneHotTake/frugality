# Frugality Backlog

## Project Vision

Cost-optimized AI development using free-tier models. The primary program (either OpenCode or Claude Code) handles thinking and orchestrating, while subtasks/agents use the best available free models.

---

## Operating Modes

### Mode 1: Fully Free Mode (Default)
- Uses only free-tier models for everything
- No paid models ever
- For OpenCode: Launch with free-coding-models and flags
- For Claude Code: Launch with CCR + claudish + free models

### Mode 2: Fully Free Agentic Mode
- Main program (Claude Code) does thinking/orchestrating
- Subtasks/agents use free models
- Requires CCR + claudish + free-coding-models integration

### Mode 3: Hybrid Mode
- Main program (Claude Code or OpenCode) uses Anthropic models for great context and planning
- Subtasks/agents use free models where appropriate
- Best of both worlds: powerful reasoning + cost optimization
- Flag: `--hybrid`

---

## Implementation Tasks

### Priority 1: CLI Enhancement

#### Add `--hybrid` flag to start command
```
frug start --hybrid          # Claude Code hybrid mode
frug start --opencode        # OpenCode fully free mode (default)
frug start --opencode --hybrid # OpenCode hybrid mode
```

#### Add mode detection
- Detect which mode user wants: `free`, `agentic`, or `hybrid`
- Store mode in state file for status commands

#### Update status command
- Show current mode (free/agentic/hybrid)
- Show which models are being used for main vs agents

### Priority 2: Pre-filled Agent Configuration

#### Create hybrid agent .md template
- Location: `~/.frugality/hybrid-agent.md`
- Template that users can copy to their project
- Contains:
  - Main model: Anthropic (for thinking)
  - Agent model: free model from cache
  - Task routing rules
  - Delegation thresholds

#### Create easy initialization command
```
frug init --hybrid          # Create hybrid config
frug init --opencode        # Create OpenCode config
frug init --free            # Create fully free config
```

### Priority 3: Model Routing Logic

#### For Hybrid Mode
```
Main Program (thinking/orchestrating):
  → Claude Sonnet 4 (or latest Anthropic)

Subtasks/Agents:
  → Read from ~/.frugality/cache/best-model-*.txt
  → Use free model based on task type
```

#### Task Type Detection
- BOILERPLATE → fast free model
- TESTS → fast free model  
- DOCS → fast free model
- ANALYSIS → analysis free model
- REASONING → reasoning free model
- ARCHITECTURE → Anthropic (keep with main)

### Priority 4: OpenCode Integration

#### Ensure OpenCode fully free mode works out of box
- `frug start --opencode` should:
  1. Query free-coding-models
  2. Cache best models
  3. Create OPENCODE.md if not exists
  4. Start idle watcher

#### Ensure OpenCode hybrid mode works
- `frug start --opencode --hybrid` should:
  1. Same as above
  2. Also configure main prompts to use Anthropic
  3. Configure Task tool to use free models

### Priority 5: Claude Code Integration

#### Ensure CCR + claudish + free models works
- `frug start --agentic` should:
  1. Configure CCR to use free models for subtasks
  2. Configure claudish to spawn with free models
  3. Main Claude uses Anthropic

#### Hybrid mode with Claude Code
- `frug start --hybrid` should:
  1. Configure CCR appropriately
  2. Main Claude: Anthropic (for thinking)
  3. Subtasks: free models via claudish

---

## State Files

| File | Purpose |
|------|---------|
| `~/.frugality/state/opencode-mode` | OpenCode mode config |
| `~/.frugality/state/agentic-mode` | Claude Code agentic mode |
| `~/.frugality/state/hybrid-mode` | Hybrid mode config |
| `~/.frugality/cache/best-model-*.txt` | Cached free models |
| `~/.frugality/hybrid-agent.md` | Hybrid agent template |

---

## Configuration Variables

### New Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `FRUGALITY_MODE` | free | Operating mode: free, agentic, hybrid |
| `FRUGALITY_MAIN_MODEL` | - | Model for main thinking (hybrid) |
| `FRUGALITY_AGENT_MODEL` | - | Model for agents (hybrid) |
| `OPENCODE_PRESETS_DIR` | ~/.opencode/presets | OpenCode presets |
| `CCR_PRESETS_DIR` | ~/.claude-code-router/presets | CCR presets |

---

## User Stories

### Story 1: Fully Free OpenCode
> As a user, I want to run OpenCode with only free models so that I can code cost-effectively.

**Steps:**
1. Run `frug start --opencode`
2. OpenCode launches with free models
3. All agents use free models from cache

### Story 2: Fully Free Claude Code
> As a user, I want to run Claude Code with only free models so that I can code cost-effectively.

**Steps:**
1. Run `frug start --agentic`
2. CCR + claudish configured with free models
3. All subtasks use free models

### Story 3: Hybrid Claude Code
> As a user, I want Claude Code to think with Anthropic models but use free models for subtasks.

**Steps:**
1. Run `frug start --hybrid`
2. Main Claude: Anthropic (great context/planning)
3. Subtasks: free models via claudish
4. Get best of both: reasoning + cost savings

### Story 4: Hybrid OpenCode
> As a user, I want OpenCode to think with Anthropic models but use free models for agents.

**Steps:**
1. Run `frug start --opencode --hybrid`
2. Main OpenCode: Anthropic (great context/planning)
3. Agents: free models from cache
4. Get best of both: reasoning + cost savings

---

## Acceptance Criteria

- [ ] `frug start` (no flags) defaults to fully free mode
- [ ] `frug start --opencode` works seamlessly with free models
- [ ] `frug start --agentic` works with CCR + claudish + free models
- [ ] `frug start --hybrid` enables hybrid mode
- [ ] `frug init --hybrid` creates template config
- [ ] Status command shows current mode
- [ ] Cache updates work for all modes
- [ ] Documentation updated for all modes

---

## Future Considerations

- [ ] Web UI for mode selection
- [ ] Model performance analytics
- [ ] Automatic model switching based on health
- [ ] Preset sharing community
