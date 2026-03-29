#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_MODULES_BIN="$SCRIPT_DIR/node_modules/.bin"

echo "Installing Frugality..."

# Install dependencies
if [ -d "$SCRIPT_DIR/node_modules" ]; then
  echo "✓ Dependencies already installed"
else
  echo "Installing dependencies..."
  cd "$SCRIPT_DIR"
  npm install --production
fi

# Preferred method: npm link for development
# For production: copy to /usr/local/lib
if npm link 2>/dev/null; then
  echo "✓ Linked via npm (development mode)"
  echo ""
  echo "Quick start:"
  echo "  frug-claude              # Start Claude Code in hybrid mode"
  echo "  frug-opencode            # Start OpenCode in hybrid mode"
  echo "  frug status              # Check system status"
else
  # Fallback: system-wide install
  LIB_DIR="/usr/local/lib/frugality"

  # Install entire project to /usr/local/lib/frugality
  sudo mkdir -p "$LIB_DIR"
  sudo cp -r "$SCRIPT_DIR"/* "$LIB_DIR/"
  sudo cp -r "$SCRIPT_DIR/.git" "$LIB_DIR/" 2>/dev/null || true

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

  echo "✓ Installed to $LIB_DIR"
  echo "✓ Created wrapper scripts in /usr/local/bin"
fi

# Create state/cache directories
mkdir -p ~/.frugality/state
mkdir -p ~/.frugality/cache
mkdir -p ~/.frugality/logs

echo "✓ Created ~/.frugality directories"
echo ""
echo "To verify installation:"
echo "  which frug-claude"
echo "  frug doctor"
