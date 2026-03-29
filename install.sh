#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing Frugality..."

# Copy binaries to /usr/local/bin
sudo cp "$SCRIPT_DIR/bin/frug.js" /usr/local/bin/frug
sudo cp "$SCRIPT_DIR/bin/frug-claude.js" /usr/local/bin/frug-claude
sudo cp "$SCRIPT_DIR/bin/frug-opencode.js" /usr/local/bin/frug-opencode

sudo chmod +x /usr/local/bin/frug /usr/local/bin/frug-claude /usr/local/bin/frug-opencode

# Create state/cache directories
mkdir -p ~/.frugality/state
mkdir -p ~/.frugality/cache
mkdir -p ~/.frugality/logs

echo "✓ Installed frug, frug-claude, frug-opencode to /usr/local/bin"
echo "✓ Created ~/.frugality directories"
echo ""
echo "Quick start:"
echo "  frug-claude              # Start Claude Code in hybrid mode"
echo "  frug-opencode            # Start OpenCode in hybrid mode"
echo "  frug status              # Check system status"
