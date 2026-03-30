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

echo "Running Frugality configuration..."
python3 "$FRUGALITY_PY"
FRUGALITY_EXIT=$?

if [ $FRUGALITY_EXIT -ne 0 ]; then
    echo "Error: Frugality configuration failed."
    exit $FRUGALITY_EXIT
fi

if command -v ccr &> /dev/null; then
    CCR_STATUS=$(ccr status 2>/dev/null)

    if echo "$CCR_STATUS" | grep -q "running\|started"; then
        echo "Restarting CCR with new model config..."
        ccr restart &
        RESTART_PID=$!

        for i in {1..8}; do
            sleep 2
            if curl -s http://localhost:3456 > /dev/null 2>&1; then
                echo "CCR restarted with new model config."
                break
            fi
            if [ $i -eq 8 ]; then
                echo "Warning: CCR restart timed out. Config updated but routing may use old models until CCR recovers."
            fi
        done
    else
        echo "Starting CCR..."
        ccr start &
        RESTART_PID=$!

        for i in {1..5}; do
            sleep 2
            if curl -s http://localhost:3456 > /dev/null 2>&1; then
                echo "CCR started successfully."
                break
            fi
            if [ $i -eq 5 ]; then
                echo "Warning: CCR failed to start. You may need to start it manually."
            fi
        done
    fi
fi

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

# Run initial configuration
echo ""
echo "=========================================="
echo " Running Initial Configuration"
echo "=========================================="
echo ""

cd "$PROJECT_DIR"
python3 frugality.py

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
