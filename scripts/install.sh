#!/usr/bin/env bash

set -e

FRUG_DIR="${FRUG_DIR:-$HOME/.frugality}"
FRUG_BIN="$FRUG_DIR/bin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════╗"
echo "║         Frugality Installer v0.2.0                 ║"
echo "║    Cost-Optimized AI Development Setup            ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

install_frug() {
  log_info "Creating Frugality directory..."
  mkdir -p "$FRUG_DIR"
  mkdir -p "$FRUG_DIR/bin"
  mkdir -p "$FRUG_DIR/state"
  mkdir -p "$FRUG_DIR/cache"
  mkdir -p "$FRUG_DIR/logs"
  
  FRUG_SCRIPT="# Frugality - Cost-Optimized AI Development
export FRUG_DIR=\"$FRUG_DIR\"
export PATH=\"\$FRUG_DIR/bin:\$PATH\"

# Aliases for quick access
alias frug='node \$FRUG_DIR/bin/frug.js'
alias frug-start='frug start'
alias frug-stop='frug stop'
alias frug-status='frug status'
alias frug-agent='frug agent'
alias frug-now='frug start --agentic'
alias frug-doctor='frug doctor'

# Quick: start coding
alias code='frug-now'
"
  
  log_info "Adding to shell configuration..."
  
  for rc_file in "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.profile"; do
    if [ -f "$rc_file" ]; then
      if ! grep -q "Frugality" "$rc_file" 2>/dev/null; then
        echo "$FRUG_SCRIPT" >> "$rc_file"
        log_success "Added to $rc_file"
        break
      fi
    fi
  done
  
  if [ -f "$HOME/.zshrc" ]; then
    if ! grep -q "Frugality" "$HOME/.zshrc" 2>/dev/null; then
      echo "$FRUG_SCRIPT" >> "$HOME/.zshrc"
      log_success "Added to ~/.zshrc"
    fi
  fi
  
  log_info "Installing frug binary..."
  cp "$PROJECT_DIR/bin/frug.js" "$FRUG_DIR/bin/frug.js"
  chmod +x "$FRUG_DIR/bin/frug.js"
  
  log_success "Frugality installed successfully!"
  echo ""
  echo -e "${GREEN}Quick start:${NC}"
  echo "  source ~/.bashrc    # or ~/.zshrc"
  echo "  frug start --agentic"
  echo ""
  echo -e "${YELLOW}Or use directly:${NC}"
  echo "  node $FRUG_DIR/bin/frug.js start --agentic"
}

uninstall_frug() {
  log_info "Removing Frugality..."
  
  for rc_file in "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.profile" "$HOME/.zshrc"; do
    if [ -f "$rc_file" ]; then
      sed -i '/^# Frugality/,/^code$/d' "$rc_file" 2>/dev/null || true
    fi
  done
  
  rm -rf "$FRUG_DIR"
  rm -f "$HOME/.config/autostart/frugality.desktop"
  
  log_success "Frugality uninstalled!"
}

setup_auto_start() {
  log_info "Setting up auto-start..."
  
  mkdir -p "$HOME/.config/autostart"
  
  cat > "$HOME/.config/autostart/frugality.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Frugality
Comment=Cost-Optimized AI Development
Exec=node $FRUG_DIR/bin/frug.js start --agentic
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
  
  log_success "Auto-start configured!"
}

show_status() {
  echo -e "${BLUE}Current Status:${NC}"
  echo "  FRUG_DIR: $FRUG_DIR"
  echo "  Binary: $FRUG_DIR/bin/frug.js"
  
  if [ -f "$FRUG_DIR/state/agentic-mode" ]; then
    MODE=$(cat "$FRUG_DIR/state/agentic-mode" | grep -o '"mode":"[^"]*"' | cut -d'"' -f4)
    STARTED=$(cat "$FRUG_DIR/state/agentic-mode" | grep -o '"startedAt":"[^"]*"' | cut -d'"' -f4)
    echo -e "  ${GREEN}Status: Running ($MODE mode)${NC}"
    echo "  Started: $STARTED"
  elif pgrep -f "frug.js" > /dev/null 2>&1; then
    echo -e "  ${GREEN}Status: Running (proxy mode)${NC}"
  else
    echo -e "  ${YELLOW}Status: Stopped${NC}"
  fi
  
  if [ -d "$FRUG_DIR/cache" ]; then
    CACHE_COUNT=$(ls "$FRUG_DIR/cache" 2>/dev/null | wc -l)
    echo "  Cache files: $CACHE_COUNT"
  fi
}

case "${1:-install}" in
  install)
    install_frug
    ;;
  uninstall|remove)
    uninstall_frug
    ;;
  autostart)
    setup_auto_start
    ;;
  status)
    show_status
    ;;
  *)
    echo "Usage: $0 {install|uninstall|autostart|status}"
    exit 1
    ;;
esac
