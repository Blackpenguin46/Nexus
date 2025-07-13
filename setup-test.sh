#!/bin/bash

# Nexus Agent Docker Setup and Test Script
set -e

echo "🚀 Setting up Nexus Agent for Docker testing..."

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs

# Ensure proper permissions
echo "🔒 Setting up permissions..."
chmod 755 data logs

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found, copying from template..."
    cp .env.template .env
    echo "✅ Please edit .env file with your configuration"
fi

# Build the Docker image
echo "🏗️  Building Docker image..."
docker compose -f docker-compose.test.yml build nexus-agent-web

echo "✅ Setup complete!"
echo ""
echo "Available commands:"
echo "  1. Web interface:     ./run-test.sh web"
echo "  2. Interactive mode:  ./run-test.sh interactive"
echo "  3. Single task:       ./run-test.sh task"
echo "  4. Status check:      ./run-test.sh status"
echo ""