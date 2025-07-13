#!/bin/bash

# Nexus Agent Test Runner Script
set -e

MODE=${1:-web}

case $MODE in
    "web")
        echo "🌐 Starting Nexus Agent in Web Mode..."
        echo "📍 Web interface will be available at: http://localhost:8080"
        echo "🛑 Press Ctrl+C to stop"
        echo ""
        docker compose -f docker-compose.test.yml up nexus-agent-web
        ;;
    
    "interactive")
        echo "💬 Starting Nexus Agent in Interactive Mode..."
        echo "💡 You can chat directly with the agent"
        echo "🛑 Type 'exit' to quit"
        echo ""
        docker compose -f docker-compose.test.yml run --rm nexus-agent-interactive
        ;;
    
    "task")
        TASK=${2:-"Hello! Please introduce yourself and show me what you can do."}
        echo "⚡ Running single task: $TASK"
        echo ""
        docker compose -f docker-compose.test.yml run --rm nexus-agent-task python -m manus.cli --task "$TASK" --debug
        ;;
    
    "status")
        echo "📊 Checking agent status..."
        docker compose -f docker-compose.test.yml run --rm nexus-agent-task python -m manus.cli --status
        ;;
    
    "logs")
        echo "📝 Showing recent logs..."
        docker compose -f docker-compose.test.yml logs --tail=50 -f
        ;;
    
    "stop")
        echo "🛑 Stopping all services..."
        docker compose -f docker-compose.test.yml down
        ;;
    
    "clean")
        echo "🧹 Cleaning up containers and volumes..."
        docker compose -f docker-compose.test.yml down -v
        docker system prune -f
        ;;
    
    "build")
        echo "🏗️  Rebuilding Docker image..."
        docker compose -f docker-compose.test.yml build --no-cache
        ;;
    
    *)
        echo "❌ Unknown mode: $MODE"
        echo ""
        echo "Available commands:"
        echo "  web          - Start web interface (http://localhost:8080)"
        echo "  interactive  - Start interactive chat mode"
        echo "  task [msg]   - Run a single task"
        echo "  status       - Check agent status"
        echo "  logs         - Show recent logs"
        echo "  stop         - Stop all services"
        echo "  clean        - Clean up containers and volumes"
        echo "  build        - Rebuild Docker image"
        echo ""
        echo "Examples:"
        echo "  ./run-test.sh web"
        echo "  ./run-test.sh task \"Create a Python hello world script\""
        echo "  ./run-test.sh interactive"
        exit 1
        ;;
esac