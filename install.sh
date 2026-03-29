#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="/usr/local/lib/frugality"

echo "Installing Frugality..."

# Install entire project to /usr/local/lib/frugality
sudo mkdir -p "$LIB_DIR"
sudo cp -r "$SCRIPT_DIR"/* "$LIB_DIR/"

# Create wrapper scripts in /usr/local/bin
create_wrapper() {
  local name="$1"
  local script="$2"

  cat > "/tmp/$name" << 'WRAPPER'
#!/bin/bash
exec node /usr/local/lib/frugality/bin/SCRIPT_NAME.js "$@"
WRAPPER

  sed -i "s|SCRIPT_NAME|$script|" "/tmp/$name"
  sudo mv "/tmp/$name" "/usr/local/bin/$name"
  sudo chmod +x "/usr/local/bin/$name"
}

create_wrapper "frug" "frug"
create_wrapper "frug-claude" "frug-claude"
create_wrapper "frug-opencode" "frug-opencode"

# Create state/cache directories
mkdir -p ~/.frugality/state
mkdir -p ~/.frugality/cache
mkdir -p ~/.frugality/logs

echo "✓ Installed to $LIB_DIR"
echo "✓ Created wrapper scripts in /usr/local/bin"
echo "✓ Created ~/.frugality directories"
echo ""
echo "Quick start:"
echo "  frug-claude              # Start Claude Code in hybrid mode"
echo "  frug-opencode            # Start OpenCode in hybrid mode"
echo "  frug status              # Check system status"
