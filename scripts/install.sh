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

# Create bin symlinks or add to PATH
echo ""
echo "=========================================="
echo "  Setting Up Command Wrappers"
echo "=========================================="
echo ""

# Check if we can create symlinks (likely if /usr/local/bin is writable)
if [ -w /usr/local/bin ] || [ "$EUID" = 0 ]; then
    echo "Creating symlinks in /usr/local/bin..."
    ln -sf "$PROJECT_DIR/bin/frugal-claude" /usr/local/bin/frugal-claude
    ln -sf "$PROJECT_DIR/bin/frugal-opencode" /usr/local/bin/frugal-opencode
    echo "✓ Symlinks created"
    echo ""
    echo "Commands available: frugal-claude, frugal-opencode"
else
    echo "Cannot write to /usr/local/bin (permission denied)"
    echo ""
    echo "Add the following to your ~/.bashrc or ~/.zshrc:"
    echo ""
    echo "  export PATH=\"\$PATH:$PROJECT_DIR/bin\""
    echo ""
    echo "Then run: source ~/.bashrc (or ~/.zshrc)"
fi

# Run initial configuration
echo ""
echo "=========================================="
echo "  Running Initial Configuration"
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
