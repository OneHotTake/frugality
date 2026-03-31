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

# Install Claudish if not already installed
if ! command -v claudish &> /dev/null; then
    echo "Installing Claudish..."
    npm install -g claudish
    echo "OK  Claudish installed"
else
    echo "OK  Claudish already installed"
fi

# Verify Claudish version
echo "Claudish version: $(claudish --version 2>/dev/null || echo 'unknown')"

# Auto-update provider URLs from free-coding-models
echo ""
echo "=========================================="
echo " Syncing Provider URLs"
echo "=========================================="
echo ""
echo "Extracting provider endpoints from free-coding-models..."
node "$SCRIPT_DIR/extract-provider-urls.js" > /tmp/provider-urls.json
if [ $? -eq 0 ]; then
    echo "OK  Extracted provider URLs"
    echo "Updating frugality.py..."
    python3 "$SCRIPT_DIR/update-provider-urls.py" /tmp/provider-urls.json
    if [ $? -eq 0 ]; then
        echo "OK  Updated provider URLs in frugality.py"
    else
        echo "Warning: Failed to update provider URLs"
    fi
else
    echo "Warning: Failed to extract provider URLs"
fi

# Verify installations
echo ""
echo "=========================================="
echo "  Verifying Installations"
echo "=========================================="
echo ""

echo "free-coding-models: $(which free-coding-models)"
echo "claudish: $(which claudish)"

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

# --- Dependency check (fail fast) ---
for cmd in python3 node claudish free-coding-models; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "Error: '$cmd' is required but not installed."
        case "$cmd" in
            python3)            echo "Install: https://www.python.org/downloads/" ;;
            node)               echo "Install: https://nodejs.org/" ;;
            claudish)           echo "Install: npm install -g claudish" ;;
            free-coding-models) echo "Install: npm install -g free-coding-models" ;;
        esac
        exit 1
    fi
done

ENV_FILE="$HOME/.frugality/current_env.sh"

# --- Run model discovery ---
echo "Running Frugality model discovery..."
python3 "$FRUGALITY_PY" "$@"
FRUGALITY_EXIT=$?

if [ $FRUGALITY_EXIT -ne 0 ]; then
    echo "Error: Frugality configuration failed (exit $FRUGALITY_EXIT)."
    exit $FRUGALITY_EXIT
fi

# --- Source the generated env file ---
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: Env file not found at $ENV_FILE"
    exit 1
fi

# shellcheck source=/dev/null
source "$ENV_FILE"

if [ -z "${FRUG_CLAUDISH_INVOCATION:-}" ]; then
    echo "Error: FRUG_CLAUDISH_INVOCATION not set in $ENV_FILE"
    exit 1
fi

# --- Launch claudish ---
echo "Launching Claudish..."
eval "$FRUG_CLAUDISH_INVOCATION --interactive" "$@"
WRAPPER_BODY

chmod +x "$HOME/bin/claude-frugal"
echo "OK  Created ~/bin/claude-frugal"

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
echo "  claude-frugal        # Launch Claude Code via Claudish with free models"
