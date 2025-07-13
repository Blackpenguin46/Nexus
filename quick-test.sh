#!/bin/bash

# Quick Test Script for Nexus Agent
echo "🚀 Nexus Agent Quick Test Setup"
echo "================================"

# Install required packages
echo "📦 Installing minimal required packages..."
pip3 install --user pydantic pydantic-settings python-dotenv rich fastapi uvicorn

echo ""
echo "🧪 Testing agent import..."
if python3 -c "import manus; print('✅ Import successful')"; then
    echo ""
    echo "🎯 Running simple task test..."
    echo "Task: Hello! Please introduce yourself and show me what you can do."
    echo ""
    python3 -m manus.cli --task "Hello! Please introduce yourself and show me what you can do." --debug
else
    echo "❌ Import failed. Checking missing dependencies..."
    python3 -c "
try:
    import pydantic
    print('✅ pydantic available')
except ImportError:
    print('❌ pydantic missing')

try:
    import rich
    print('✅ rich available')  
except ImportError:
    print('❌ rich missing')

try:
    import fastapi
    print('✅ fastapi available')
except ImportError:
    print('❌ fastapi missing')
"
fi