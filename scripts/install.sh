#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  Frugality Installation"
echo "=========================================="
echo ""

# Check dependencies
echo "Checking dependencies..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi
echo "OK  Python 3: $(python3 --version)"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is required but not installed."
    exit 1
fi
echo "OK  Node.js: $(node --version)"

# Check npm
if ! command -v npm &> /dev/null; then
    echo "Error: npm is required but not installed."
    exit 1
fi
echo "OK  npm: $(npm --version)"

# Check uv
if ! command -v uv &> /dev/null; then
    echo "Error: uv is required but not installed."
    echo "Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
echo "OK  uv: $(uv --version)"

echo ""
echo "=========================================="
echo "  Installing Dependencies"
echo "=========================================="
echo ""

# Install free-coding-models if not already installed
if ! command -v free-coding-models &> /dev/null; then
    echo "Installing free-coding-models..."
    npm install -g free-coding-models
    echo "OK  free-coding-models installed"
else
    echo "OK  free-coding-models already installed"
fi

# Install free-claude-code proxy
echo "Installing free-claude-code proxy..."
uv tool install git+https://github.com/Alishahryar1/free-claude-code.git

echo "Initializing free-claude-code config..."
fcc-init  # creates ~/.config/free-claude-code/.env from built-in template

echo "Verifying installation..."
fcc --version || { echo "free-claude-code install failed"; exit 1; }

# Verify installations
echo ""
echo "=========================================="
echo "  Verifying Installations"
echo "=========================================="
echo ""

echo "free-coding-models: $(which free-coding-models)"
echo "fcc: $(which fcc)"

# Test free-coding-models
echo ""
echo "Testing free-coding-models..."
if free-coding-models --json --hide-unconfigured &> /dev/null; then
    echo "OK  free-coding-models is working"
else
    echo "Warning: free-coding-models may need configuration"
fi

# Create necessary directories
echo ""
echo "=========================================="
echo "  Creating Directories"
echo "=========================================="
echo ""

mkdir -p ~/.frugality/cache
mkdir -p ~/.frugality/logs
echo "OK  Created ~/.frugality/"

# Create command wrappers in ~/bin/
echo ""
echo "=========================================="
echo "  Setting Up Command Wrappers"
echo "=========================================="
echo ""

mkdir -p "$HOME/bin"

FRUGALITY_PY="$PROJECT_DIR/frugality.py"

# Generate claude-frugal wrapper with hardcoded path
cat > "$HOME/bin/claude-frugal" << WRAPPER_HEADER
#!/usr/bin/env bash
set -euo pipefail

FRUGALITY_PY="$FRUGALITY_PY"
WRAPPER_HEADER

cat >> "$HOME/bin/claude-frugal" << 'WRAPPER_BODY'

# ── Dependency checks ──────────────────────────────────────────────
MISSING=()
for cmd in python3 node uv claude; do
  command -v "$cmd" &>/dev/null || MISSING+=("$cmd")
done

# fcc (free-claude-code) check — installed via uv tool
if ! uv tool list 2>/dev/null | grep -q "free-claude-code"; then
  MISSING+=("free-claude-code (run: uv tool install git+https://github.com/Alishahryar1/free-claude-code.git)")
fi

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "frugal-claude: missing dependencies:" >&2
  printf '  - %s\n' "${MISSING[@]}" >&2
  exit 1
fi

# ── Model discovery ────────────────────────────────────────────────
echo "frugal-claude: discovering models..."
python3 "$FRUGALITY_PY" || {
  echo "frugal-claude: model discovery failed. Aborting." >&2
  exit 1
}

# ── Verify cc-nim config was written ──────────────────────────────
CC_NIM_ENV="$HOME/.config/free-claude-code/.env"
if [[ ! -f "$CC_NIM_ENV" ]]; then
  echo "frugal-claude: $CC_NIM_ENV not found after discovery. Aborting." >&2
  exit 1
fi

# ── Print active model config ──────────────────────────────────────
echo "frugal-claude: active routing:"
grep -E '^MODEL' "$CC_NIM_ENV" | sed 's/^/  /'

# ── Launch cc-nim proxy + Claude Code ─────────────────────────────
exec fcc "$@"
WRAPPER_BODY

# Generate frugal-opencode wrapper
cat > "$HOME/bin/frugal-opencode" << WRAPPER_HEADER
#!/usr/bin/env bash
set -euo pipefail

FRUGALITY_PY="$FRUGALITY_PY"
WRAPPER_HEADER

cat >> "$HOME/bin/frugal-opencode" << 'WRAPPER_BODY'

# ── Dependency checks ──────────────────────────────────────────────
MISSING=()
for cmd in python3 node free-coding-models opencode; do
  command -v "$cmd" &>/dev/null || MISSING+=("$cmd")
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "frugal-opencode: missing dependencies:" >&2
  printf '  - %s\n' "${MISSING[@]}" >&2
  exit 1
fi

# ── Cache check ───────────────────────────────────────────────────
CACHE_DIR="$HOME/.frugality/cache"
if [[ ! -d "$CACHE_DIR" ]] || [[ $(find "$CACHE_DIR" -mmin +60 2>/dev/null) ]]; then
  echo "frugal-opencode: running model discovery..."
  python3 "$FRUGALITY_PY" || {
    echo "frugal-opencode: model discovery failed. Continuing with cached data..." >&2
  }
fi

# ── Launch OpenCode natively ─────────────────────────────────────
exec opencode "$@"
WRAPPER_BODY

chmod +x "$HOME/bin/claude-frugal"
chmod +x "$HOME/bin/frugal-opencode"
echo "OK  Created ~/bin/claude-frugal and ~/bin/frugal-opencode"

echo ""
echo "=========================================="
echo "  Running Initial Discovery"
echo "=========================================="
echo ""

# Run initial model discovery to populate env file
python3 "$PROJECT_DIR/frugality.py"
echo ""
echo "Installation complete!"
echo ""
echo "Usage:"
echo "  claude-frugal        # Launch Claude Code via cc-nim with free models"
echo "  frugal-opencode      # Launch OpenCode with free models"