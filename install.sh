#!/bin/bash
"""
Nexus Agent Installation Script
Makes Nexus available as a global command like Claude Code
"""

set -e

echo "🚀 Installing Nexus Agent CLI..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEXUS_SCRIPT="$SCRIPT_DIR/nexus"

# Check if nexus script exists
if [[ ! -f "$NEXUS_SCRIPT" ]]; then
    echo "❌ Error: nexus script not found at $NEXUS_SCRIPT"
    exit 1
fi

# Make nexus script executable
chmod +x "$NEXUS_SCRIPT"

# Determine installation method based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    INSTALL_DIR="/usr/local/bin"
    if [[ -w "$INSTALL_DIR" ]]; then
        ln -sf "$NEXUS_SCRIPT" "$INSTALL_DIR/nexus"
        echo "✅ Nexus installed to $INSTALL_DIR/nexus"
    else
        echo "🔒 Need sudo access to install to $INSTALL_DIR"
        sudo ln -sf "$NEXUS_SCRIPT" "$INSTALL_DIR/nexus"
        echo "✅ Nexus installed to $INSTALL_DIR/nexus"
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    INSTALL_DIR="/usr/local/bin"
    if [[ -w "$INSTALL_DIR" ]]; then
        ln -sf "$NEXUS_SCRIPT" "$INSTALL_DIR/nexus"
        echo "✅ Nexus installed to $INSTALL_DIR/nexus"
    else
        echo "🔒 Need sudo access to install to $INSTALL_DIR"
        sudo ln -sf "$NEXUS_SCRIPT" "$INSTALL_DIR/nexus"
        echo "✅ Nexus installed to $INSTALL_DIR/nexus"
    fi
else
    # Windows/Other - add to user's local bin
    LOCAL_BIN="$HOME/.local/bin"
    mkdir -p "$LOCAL_BIN"
    ln -sf "$NEXUS_SCRIPT" "$LOCAL_BIN/nexus"
    echo "✅ Nexus installed to $LOCAL_BIN/nexus"
    
    # Check if PATH includes ~/.local/bin
    if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
        echo "⚠️  Add $LOCAL_BIN to your PATH:"
        echo "   export PATH=\"\$PATH:$LOCAL_BIN\""
        echo "   Add this to your ~/.bashrc or ~/.zshrc"
    fi
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Quick test:"
echo "  nexus --test"
echo ""
echo "Usage examples:"
echo "  nexus \"What's the current date?\""
echo "  nexus --interactive"
echo "  nexus \"Create a hello world script\""
echo ""
echo "📚 Documentation:"
echo "  nexus --help"
echo "  Read QUICK_START.md for setup"
echo ""