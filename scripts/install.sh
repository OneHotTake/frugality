#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ── Welcome banner ───────────────────────────────────────────────
echo "🚀 Welcome to Frugality!"
echo "   Claude Code. Free models. Zero compromise."
echo ""

# ── Dependency check ──────────────────────────────────────────────
echo "📦 Checking dependencies..."

deps_ok=true
for dep in python3 node npm uv; do
  if ! command -v "$dep" &> /dev/null; then
    echo "❌ $dep is required but not installed"
    case "$dep" in
      python3) echo "   Install: https://python.org/downloads/" ;;
      node) echo "   Install: https://nodejs.org/" ;;
      npm) echo "   Install: comes with Node.js" ;;
      uv) echo "   Install: curl -LsSf https://astral.sh/uv/install.sh | sh" ;;
    esac
    deps_ok=false
  else
    echo "✅ $dep: $($dep --version 2>/dev/null || echo 'ok')"
  fi
done

if [[ "$deps_ok" == "false" ]]; then
  echo ""
  echo "💡 Install missing dependencies first, then run this script again."
  exit 1
fi

echo ""

# ── Install dependencies ──────────────────────────────────────────
echo "📥 Installing dependencies..."

# Install free-coding-models
if ! command -v free-coding-models &> /dev/null; then
  echo "• Installing free-coding-models..."
  npm install -g free-coding-models
else
  echo "✅ free-coding-models already installed"
fi

# Install free-claude-code
if ! uv tool list 2>/dev/null | grep -q "free-claude-code"; then
  echo "• Installing free-claude-code..."
  uv tool install git+https://github.com/Alishahryar1/free-claude-code.git
  fcc-init 2>/dev/null || echo "   ⚠️  fcc-init failed (run manually if needed)"
else
  echo "✅ free-claude-code already installed"
fi

echo ""

# ── Setup directories ─────────────────────────────────────────────
echo "📁 Setting up directories..."
mkdir -p ~/.frugality/{cache,logs}
mkdir -p "$HOME/bin" 2>/dev/null || true

# ── Create wrapper ────────────────────────────────────────────────
echo "🔧 Creating claude-frugal wrapper..."

FRUGALITY_PY="$PROJECT_DIR/frugality.py"

cat > "$HOME/bin/claude-frugal" << 'WRAPPER'
#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Frugality - Claude Code on Free Models"
echo ""

# ── Dependency check ──────────────────────────────────────────────
missing=()
for cmd in python3 node uv claude; do
  if ! command -v "$cmd" &>/dev/null; then
    missing+=("$cmd")
  fi
done

# Check free-claude-code
if ! uv tool list 2>/dev/null | grep -q "free-claude-code"; then
  missing+=("free-claude-code (uv tool install git+https://github.com/Alishahryar1/free-claude-code.git)")
fi

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "❌ Missing dependencies:"
  printf '  • %s\n' "${missing[@]}"
  echo ""
  echo "💡 Install missing deps:"
  echo "   npm install -g free-coding-models"
  echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "   uv tool install git+https://github.com/Alishahryar1/free-claude-code.git"
  echo ""
  exit 1
fi

# ── Model discovery ────────────────────────────────────────────────
if [[ "${1:-}" != "--check-keys" ]]; then
  echo "🔍 Discovering models..."
  python3 "$(dirname "$(realpath "$0")")/../frugality.py" "$@" || {
    echo "❌ Model discovery failed"
    echo "💡 Try: free-coding-models (to setup API keys)"
    exit 1
  }
fi

# ── Verify config ──────────────────────────────────────────────────
CC_NIM_ENV="$HOME/.config/free-claude-code/.env"
if [[ ! -f "$CC_NIM_ENV" ]]; then
  echo "❌ Config not found. Run: claude-frugal --refresh"
  exit 1
fi

# ── Show active models ─────────────────────────────────────────────
echo ""
echo "📋 Active Models:"
grep -E '^MODEL' "$CC_NIM_ENV" | sed 's/^/  /' | sed 's/="/ → /' | sed 's/"$//'

# ── Launch! ───────────────────────────────────────────────────────
echo ""
echo "🎯 Starting Claude Code..."
echo "   (Proxy: free-claude-code)"
echo ""

exec fcc "$@"
WRAPPER

# Make wrapper executable
chmod +x "$HOME/bin/claude-frugal"

echo ""
echo "✅ claude-frugal created in $HOME/bin/"

# ── Initial discovery ──────────────────────────────────────────────
echo ""
echo "🔍 Running initial model discovery..."
python3 "$PROJECT_DIR/frugality.py" 2>/dev/null || {
  echo "⚠️  Initial discovery failed"
  echo "   Run 'claude-frugal --refresh' after setting up API keys"
}

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Usage:"
echo "  claude-frugal        # Start coding with free models"
echo "  claude-frugal --help # Show all options"
echo ""
echo "💡 First time? Run 'free-coding-models' to setup API keys!"