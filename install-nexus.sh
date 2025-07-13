#!/bin/bash

# Install Nexus globally
NEXUS_DIR="/Users/samoakes/Desktop/Projects/Manus-remake"
TARGET_DIR="/usr/local/bin"

echo "Installing Nexus globally..."

# Create nexus wrapper script
cat > /tmp/nexus << 'EOF'
#!/bin/bash
exec "/Users/samoakes/Desktop/Projects/Manus-remake/nexus" "$@"
EOF

# Make it executable
chmod +x /tmp/nexus

# Move to global location (requires sudo)
echo "Moving to $TARGET_DIR (requires sudo password)..."
sudo mv /tmp/nexus "$TARGET_DIR/nexus"

echo "✅ Nexus installed! You can now run 'nexus' from anywhere."
echo "Try it: nexus"