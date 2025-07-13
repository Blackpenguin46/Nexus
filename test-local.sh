#!/bin/bash

# Local Testing Script (without Docker)
set -e

echo "🚀 Testing Nexus Agent locally (without Docker)..."

# Check Python version
echo "🐍 Checking Python version..."
python3 --version

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
else
    echo "🔄 Using existing virtual environment..."
    source venv/bin/activate
fi

# Create necessary directories
echo "📁 Ensuring directories exist..."
mkdir -p data logs

MODE=${1:-status}

case $MODE in
    "status")
        echo "📊 Checking agent status..."
        python -m manus.cli --status
        ;;
    
    "task")
        TASK=${2:-"Hello! Please introduce yourself and show me what you can do."}
        echo "⚡ Running single task: $TASK"
        python -m manus.cli --task "$TASK" --debug
        ;;
    
    "interactive")
        echo "💬 Starting interactive mode..."
        echo "💡 You can chat directly with the agent"
        echo "🛑 Type 'exit' to quit"
        python -m manus.cli --interactive --debug
        ;;
    
    "web")
        echo "🌐 Starting web server..."
        echo "📍 Web interface will be available at: http://localhost:8000"
        echo "🛑 Press Ctrl+C to stop"
        python -m manus.cli --web --host 127.0.0.1 --port 8000 --debug
        ;;
    
    *)
        echo "Available commands:"
        echo "  status       - Check agent status"
        echo "  task [msg]   - Run a single task"
        echo "  interactive  - Start interactive chat mode"
        echo "  web          - Start web interface"
        echo ""
        echo "Examples:"
        echo "  ./test-local.sh status"
        echo "  ./test-local.sh task \"List files in current directory\""
        echo "  ./test-local.sh interactive"
        echo "  ./test-local.sh web"
        ;;
esac