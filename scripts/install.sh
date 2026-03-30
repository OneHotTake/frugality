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
echo "✓ Python 3: $(python3 --version)"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is required but not installed."
    exit 1
fi
echo "✓ Node.js: $(node --version)"

# Check npm
if ! command -v npm &> /dev/null; then
    echo "Error: npm is required but not installed."
    exit 1
fi
echo "✓ npm: $(npm --version)"

echo ""
echo "=========================================="
echo "  Installing Dependencies"
echo "=========================================="
echo ""

# Install free-coding-models if not already installed
if ! command -v free-coding-models &> /dev/null; then
    echo "Installing free-coding-models..."
    npm install -g free-coding-models
    echo "✓ free-coding-models installed"
else
    echo "✓ free-coding-models already installed"
fi

# Install Claude Code Router if not already installed
if ! command -v ccr &> /dev/null; then
    echo "Installing Claude Code Router..."
    npm install -g @musistudio/claude-code-router
    echo "✓ Claude Code Router installed"
else
    echo "✓ Claude Code Router already installed"
fi

# Verify installations
echo ""
echo "=========================================="
echo "  Verifying Installations"
echo "=========================================="
echo ""

echo "free-coding-models: $(which free-coding-models)"
echo "ccr: $(which ccr)"

# Test free-coding-models
echo ""
echo "Testing free-coding-models..."
if free-coding-models --json --hide-unconfigured &> /dev/null; then
    echo "✓ free-coding-models is working"
else
    echo "⚠ Warning: free-coding-models may need configuration"
fi

# Create necessary directories
echo ""
echo "=========================================="
echo "  Creating Directories"
echo "=========================================="
echo ""

mkdir -p ~/.frugality/cache
mkdir -p ~/.frugality/logs
echo "✓ Created ~/.frugality/"

# Create bin symlinks in ~/bin/
echo ""
echo "=========================================="
echo "  Setting Up Command Wrappers"
echo "=========================================="
echo ""

# Create ~/bin/ if it doesn't exist
mkdir -p "$HOME/bin"

FRUGALITY_PY="$PROJECT_DIR/frugality.py"

# Generate frugal-claude wrapper with hardcoded path
cat > "$HOME/bin/frugal-claude" << 'WRAPPER_EOF'
#!/usr/bin/env bash

# Command line flags
FLAG_CONNECT=0
FLAG_RESTART=0
FLAG_REFRESH=0

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --connect)
            FLAG_CONNECT=1
            shift
            ;;
        --restart|--force)
            FLAG_RESTART=1
            shift
            ;;
        --refresh)
            FLAG_REFRESH=1
            shift
            ;;
        *)
            # Pass unknown arguments to claude
            break
            ;;
    esac
done

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not installed."
    echo "Please install Python 3 and try again."
    exit 1
fi

WRAPPER_EOF
echo "FRUGALITY_PY=\"$FRUGALITY_PY\"" >> "$HOME/bin/frugal-claude"
cat >> "$HOME/bin/frugal-claude" << 'WRAPPER_EOF'

if [ ! -f "$FRUGALITY_PY" ]; then
    echo "Error: frugality.py not found at $FRUGALITY_PY"
    echo "Please ensure Frugality is installed correctly."
    exit 1
fi

# Check if CCR is running
CCR_RUNNING=0
if command -v ccr &> /dev/null; then
    CCR_STATUS=$(ccr status 2>/dev/null)
    if echo "$CCR_STATUS" | grep -q "running\|started"; then
        CCR_RUNNING=1
    fi
fi

# Check config age to bias recommendation
CONFIG_AGE_MINUTES=999
if [ -f "$HOME/.claude-code-router/config.json" ]; then
    CONFIG_MTIME=$(stat -c %Y "$HOME/.claude-code-router/config.json" 2>/dev/null || echo "0")
    CURRENT_TIME=$(date +%s)
    CONFIG_AGE_SEC=$((CURRENT_TIME - CONFIG_MTIME))
    CONFIG_AGE_MINUTES=$((CONFIG_AGE_SEC / 60))
fi

# Decision logic
if [ $FLAG_CONNECT -eq 1 ]; then
    # Connect mode: skip config generation
    echo "Connecting to existing CCR instance..."
elif [ $FLAG_RESTART -eq 1 ]; then
    # Restart mode: update config and restart
    echo "Updating configuration and restarting CCR..."
    FRUGALITY_ARGS=""
    [ $FLAG_REFRESH -eq 1 ] && FRUGALITY_ARGS="--refresh"
    python3 "$FRUGALITY_PY" $FRUGALITY_ARGS
    if [ $? -ne 0 ]; then
        echo "Error: Configuration update failed."
        exit 1
    fi
    ccr restart &
    RESTART_PID=$!
    wait $RESTART_PID 2>/dev/null
elif [ $CCR_RUNNING -eq 1 ]; then
    # CCR is running and no flags set - show prompt
    echo "========================================"
    echo "Claude Code Router is already running."
    echo "Config age: ${CONFIG_AGE_MINUTES} minutes"
    echo ""

    # Bias the prompt based on config age
    if [ $CONFIG_AGE_MINUTES -lt 5 ]; then
        echo "Your config is recent (<5 min old)."
        echo "Recommended: Connect to existing instance"
        DEFAULT_OPTION=1
        echo ""
    else
        echo "Your config may be stale (>5 min old)."
        echo "Recommended: Restart with updated configuration"
        DEFAULT_OPTION=2
        echo ""
    fi

    echo "Options:"
    echo "  1) Connect to existing instance (no restart)"
    echo "  2) Restart CCR with updated configuration"
    echo ""

    # Read user input with timeout
    read -t 5 -p "Select [1-2] (default: $DEFAULT_OPTION): " choice || true

    if [ -z "$choice" ]; then
        choice=$DEFAULT_OPTION  # Use default on timeout
    fi

    case $choice in
        1)
            echo "Connecting to existing instance..."
            ;;
        2|*)
            echo "Updating configuration and restarting CCR..."
            FRUGALITY_ARGS=""
            [ $FLAG_REFRESH -eq 1 ] && FRUGALITY_ARGS="--refresh"
            python3 "$FRUGALITY_PY" $FRUGALITY_ARGS
            if [ $? -ne 0 ]; then
                echo "Error: Configuration update failed."
                exit 1
            fi
            ccr restart &
            RESTART_PID=$!
            wait $RESTART_PID 2>/dev/null
            ;;
    esac
else
    # CCR not running - normal startup
    echo "Running Frugality configuration..."
    FRUGALITY_ARGS=""
    [ $FLAG_REFRESH -eq 1 ] && FRUGALITY_ARGS="--refresh"
    python3 "$FRUGALITY_PY" $FRUGALITY_ARGS
    FRUGALITY_EXIT=$?

    if [ $FRUGALITY_EXIT -ne 0 ]; then
        echo "Error: Frugality configuration failed."
        exit $FRUGALITY_EXIT
    fi

    if command -v ccr &> /dev/null; then
        CCR_STATUS=$(ccr status 2>/dev/null)
        if ! echo "$CCR_STATUS" | grep -q "running\|started"; then
            echo "Starting CCR..."
            ccr start &
            START_PID=$!
            wait $START_PID 2>/dev/null
        fi
    fi
fi

# Wait for CCR to be healthy
for i in {1..8}; do
    if curl -s http://localhost:3456 > /dev/null 2>&1; then
        break
    fi
    if [ $i -eq 8 ]; then
        echo "Warning: CCR failed to start or respond to health checks."
        echo "You may need to start it manually or check the logs."
    fi
    sleep 2
done

export ANTHROPIC_BASE_URL="http://127.0.0.1:3456"
exec claude "$@"
WRAPPER_EOF

# Generate frugal-opencode wrapper with hardcoded path
cat > "$HOME/bin/frugal-opencode" << 'WRAPPER_EOF'
#!/usr/bin/env bash

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not installed."
    echo "Please install Python 3 and try again."
    exit 1
fi

WRAPPER_EOF
echo "FRUGALITY_PY=\"$FRUGALITY_PY\"" >> "$HOME/bin/frugal-opencode"
cat >> "$HOME/bin/frugal-opencode" << 'WRAPPER_EOF'

if [ ! -f "$FRUGALITY_PY" ]; then
    echo "Error: frugality.py not found at $FRUGALITY_PY"
    echo "Please ensure Frugality is installed correctly."
    exit 1
fi

echo "Running Frugality configuration..."
python3 "$FRUGALITY_PY" --opencode
FRUGALITY_EXIT=$?

if [ $FRUGALITY_EXIT -ne 0 ]; then
    echo "Error: Frugality configuration failed."
    exit $FRUGALITY_EXIT
fi

exec opencode "$@"
WRAPPER_EOF

chmod +x "$HOME/bin/frugal-claude"
chmod +x "$HOME/bin/frugal-opencode"

echo "✓ Wrappers created in ~/bin/"

# Check if ~/bin is in PATH
if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
    echo ""
    echo "⚠ Warning: ~/bin is not in your PATH"
    echo ""
    echo "Add the following to your ~/.bashrc or ~/.zshrc:"
    echo ""
    echo " export PATH=\"\$PATH:$HOME/bin\""
    echo ""
    echo "Then run: source ~/.bashrc (or ~/.zshrc)"
fi

# Run free-coding-models to ensure model cache is populated
echo ""
echo "=========================================="
echo " Running Free-Coding-Models Discovery"
echo "=========================================="
echo ""

echo "Discovering available models..."
free-coding-models --json --hide-unconfigured > /dev/null
echo "✓ Model discovery complete"

# Run initial configuration with refresh to populate cert registry
echo ""
echo "=========================================="
echo " Running Initial Configuration"
echo "=========================================="
echo ""

cd "$PROJECT_DIR"
python3 frugality.py --refresh

# Start CCR if not running
echo ""
echo "Starting Claude Code Router..."
ccr start || echo "Note: CCR may already be running or installed differently"

echo ""
echo "=========================================="
echo "  Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Configure your API keys in ~/.free-coding-models.json"
echo "  2. Run 'frugal-claude' to start Claude Code with routing"
echo "  3. Or run 'frugal-opencode' to start OpenCode"
echo ""
echo "For more info, see: $PROJECT_DIR/README.md"
echo ""
