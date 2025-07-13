# 💻 How to Use Nexus Agent CLI

This comprehensive guide covers all CLI usage patterns for the Nexus autonomous agent framework.

## 🚀 Quick Start

```bash
# Install dependencies first
pip3 install --user pydantic pydantic-settings python-dotenv rich fastapi uvicorn aiohttp selenium webdriver-manager PyYAML cryptography validators structlog psutil json5 aiofiles

# Quick test
python3 run-nexus.py --test

# Interactive mode
python3 run-nexus.py --interactive

# Single task
python3 run-nexus.py --task "Create a hello world script"

# Web interface
python3 run-nexus.py --web
```

## 📖 Command Reference

### Main CLI Runner
```bash
python3 run-nexus.py [OPTIONS]
```

### Available Options

| Option | Description | Example |
|--------|-------------|---------|
| `--test` | Run demo test scenarios | `python3 run-nexus.py --test` |
| `--interactive` | Start interactive chat mode | `python3 run-nexus.py --interactive` |
| `--task "message"` | Execute single task | `python3 run-nexus.py --task "List files"` |
| `--web` | Start web interface | `python3 run-nexus.py --web` |
| `--port 8080` | Set web server port | `python3 run-nexus.py --web --port 8080` |
| `--config path` | Use custom config file | `python3 run-nexus.py --config ./config.yaml` |
| `--debug` | Enable debug logging | `python3 run-nexus.py --debug --interactive` |
| `--help` | Show help message | `python3 run-nexus.py --help` |

## 🎯 Usage Modes

### 1. Demo Test Mode
**Purpose**: Quick functionality verification
```bash
python3 run-nexus.py --test
```

**What it does:**
- Runs predefined test scenarios
- Tests agent initialization
- Verifies tool execution
- Demonstrates reasoning capabilities

**Example output:**
```
🎯 Task: Hello! Please introduce yourself
============================================================
🤖 Agent Response:
Let me check our current environment and working directory to understand the context better.

🔧 Executing 1 tool(s):
  1. shell_pwd({})
     ✅ Result: /Users/your-path/Nexus/data...

🎯 Task: List available tools
============================================================
🤖 Agent Response:
I'll gather information about the current environment to better understand your request.

🔧 Executing 1 tool(s):
  1. file_list({'directory': '.'})
     ✅ Result: [{'name': 'hello_world.py', 'type': 'file'...}]
```

### 2. Interactive Mode
**Purpose**: Conversational interaction with the agent
```bash
python3 run-nexus.py --interactive
```

**Features:**
- Multi-turn conversations
- Context preservation
- Real-time responses
- Graceful exit handling

**Example session:**
```
🤖 Nexus Agent Interactive Mode
Type 'exit', 'quit', or press Ctrl+C to stop.

Manus> hello
🤖 Agent Response: Let me check our current environment and working directory to understand the context better.
🔧 Executing 1 tool(s):
  1. shell_pwd({})
     ✅ Result: /Users/your-path/Nexus/data

Manus> create a python script
🤖 Agent Response: I'll create a Python script template for you with a proper structure.
🔧 Executing 1 tool(s):
  1. file_write({'path': 'script.py', 'content': '#!/usr/bin/env python3...'})
     ✅ Result: Successfully wrote 156 characters to script.py

Manus> list files
🤖 Agent Response: I'll list the files in the current directory for you.
🔧 Executing 1 tool(s):
  1. file_list({'directory': '.'})
     ✅ Result: [{'name': 'script.py', 'type': 'file', 'size': 156}...]

Manus> exit
👋 Goodbye! Agent session ended.
```

**Interactive Commands:**
- `help` - Show available commands
- `status` - Show agent status
- `tools` - List available tools
- `history` - Show conversation history
- `clear` - Clear conversation history
- `exit` / `quit` - Exit interactive mode

### 3. Single Task Mode
**Purpose**: Execute one specific task and exit
```bash
python3 run-nexus.py --task "Your task description"
```

**Examples:**

**File Operations:**
```bash
python3 run-nexus.py --task "Create a README.md file"
python3 run-nexus.py --task "List all files in this directory"
python3 run-nexus.py --task "Read the contents of config.json"
```

**System Information:**
```bash
python3 run-nexus.py --task "What's the current date and time?"
python3 run-nexus.py --task "Show system information"
python3 run-nexus.py --task "List running processes"
```

**Development Tasks:**
```bash
python3 run-nexus.py --task "Create a Python hello world script"
python3 run-nexus.py --task "Generate a requirements.txt file"
python3 run-nexus.py --task "Create a project structure for a web app"
```

**Complex Multi-step Tasks:**
```bash
python3 run-nexus.py --task "First check the date, then create a log file with current time, and finally list all files"
python3 run-nexus.py --task "Analyze this project and create a comprehensive documentation file"
```

### 4. Web Interface Mode
**Purpose**: Browser-based interface for the agent
```bash
python3 run-nexus.py --web
```

**Options:**
```bash
# Custom port
python3 run-nexus.py --web --port 8080

# Debug mode
python3 run-nexus.py --web --debug

# Custom host binding
python3 run-nexus.py --web --host 0.0.0.0 --port 8080
```

**Access:**
- Open browser to `http://localhost:8080`
- RESTful API available at `/api/`
- Health check at `/health`
- Metrics at `/metrics`

## 🛠️ Advanced CLI Usage

### Configuration Override
```bash
# Use custom config file
python3 run-nexus.py --config ./my-config.yaml --interactive

# Override environment variables
LLM__PROVIDER=mock DEBUG_MODE=true python3 run-nexus.py --interactive

# Set working directory
MANUS_WORKING_DIR=/tmp/nexus python3 run-nexus.py --task "List files"
```

### Debug Mode
```bash
# Enable debug logging
python3 run-nexus.py --debug --interactive

# Verbose output
python3 run-nexus.py --debug --task "Create a file" 2>&1 | tee debug.log
```

### Batch Processing
```bash
# Process multiple tasks
for task in "Create file1.txt" "Create file2.txt" "List files"; do
    python3 run-nexus.py --task "$task"
done

# From file
cat tasks.txt | while read task; do
    python3 run-nexus.py --task "$task"
done
```

### Piping and Redirection
```bash
# Save output to file
python3 run-nexus.py --task "Show system info" > system_report.txt

# Process output
python3 run-nexus.py --task "List files" | grep "\.py"

# Error handling
python3 run-nexus.py --task "Invalid task" 2>error.log
```

## 📋 Task Categories & Examples

### File Management
```bash
# Create files
python3 run-nexus.py --task "Create a config.json with default settings"
python3 run-nexus.py --task "Write a hello world script in Python"
python3 run-nexus.py --task "Generate a markdown documentation file"

# Read files
python3 run-nexus.py --task "Show me the contents of README.md"
python3 run-nexus.py --task "Read the first 10 lines of log.txt"

# List and explore
python3 run-nexus.py --task "List all Python files in this directory"
python3 run-nexus.py --task "Show file sizes and details"
python3 run-nexus.py --task "Find the largest files"
```

### System Administration
```bash
# System information
python3 run-nexus.py --task "Show operating system details"
python3 run-nexus.py --task "Check current memory usage"
python3 run-nexus.py --task "Display running processes"

# Environment
python3 run-nexus.py --task "Show environment variables"
python3 run-nexus.py --task "Check current working directory"
python3 run-nexus.py --task "Display system uptime"
```

### Development Tasks
```bash
# Project setup
python3 run-nexus.py --task "Create a Python project structure"
python3 run-nexus.py --task "Generate a basic Flask application"
python3 run-nexus.py --task "Create a Docker configuration"

# Code analysis
python3 run-nexus.py --task "Analyze Python files in this directory"
python3 run-nexus.py --task "Count lines of code in all files"
python3 run-nexus.py --task "List all TODO comments"
```

### Data Processing
```bash
# Analysis
python3 run-nexus.py --task "Create a summary of all text files"
python3 run-nexus.py --task "Count words in all markdown files"
python3 run-nexus.py --task "Generate a file type report"

# Reporting
python3 run-nexus.py --task "Create a project overview document"
python3 run-nexus.py --task "Generate a changelog from git history"
```

## 🎮 Interactive Features

### Commands Available in Interactive Mode

| Command | Description | Example |
|---------|-------------|---------|
| `help` | Show available commands | `help` |
| `status` | Agent status and stats | `status` |
| `tools` | List available tools | `tools` |
| `history` | Show conversation | `history` |
| `clear` | Clear conversation | `clear` |
| `save <file>` | Save session to file | `save session.log` |
| `load <file>` | Load previous session | `load session.log` |
| `config` | Show current config | `config` |
| `debug on/off` | Toggle debug mode | `debug on` |

### Special Interactive Syntax
```bash
# Multi-line input (end with empty line)
Manus> Create a Python script that:
     > - Reads a CSV file
     > - Processes the data
     > - Outputs results
     > 

# Command chaining
Manus> create file1.txt && list files && read file1.txt

# Variable substitution
Manus> set filename=test.py
Manus> create $filename with hello world
```

### Session Management
```bash
# Save current session
Manus> save my_session.json

# Load previous session
python3 run-nexus.py --interactive --load my_session.json

# Export conversation
Manus> export conversation.md
```

## 🔧 Environment Configuration

### Essential Environment Variables
```bash
# Core configuration
export LLM__PROVIDER=mock
export AGENT__NAME=nexus-cli
export DEBUG_MODE=false

# Paths
export MANUS_WORKING_DIR=./data
export LOG_DIR=./logs

# Security
export SECURITY__ALLOWED_DOMAINS=localhost
export SECURITY__MAX_FILE_SIZE_MB=100

# Performance
export MAX_ITERATIONS=1000
export TIMEOUT_SECONDS=300
```

### Configuration File
Create `.env` file:
```bash
LLM__PROVIDER=mock
AGENT__NAME=nexus-local
DEBUG_MODE=true
MANUS_WORKING_DIR=./data
SECURITY__ALLOWED_DOMAINS=localhost,127.0.0.1
MAX_ITERATIONS=1000
TIMEOUT_SECONDS=300
```

### Custom Configuration
Create `config.yaml`:
```yaml
llm:
  provider: mock
  model: gpt-3.5-turbo
  temperature: 0.7

agent:
  name: nexus-custom
  max_iterations: 1000
  timeout_seconds: 300

security:
  allowed_domains:
    - localhost
    - 127.0.0.1
  max_file_size_mb: 100
```

Use with:
```bash
python3 run-nexus.py --config config.yaml --interactive
```

## 📊 Monitoring & Debugging

### Logging Levels
```bash
# Info level (default)
python3 run-nexus.py --interactive

# Debug level
python3 run-nexus.py --debug --interactive

# Quiet mode
python3 run-nexus.py --quiet --task "Create file"
```

### Performance Monitoring
```bash
# Time execution
time python3 run-nexus.py --task "Complex analysis task"

# Memory usage
/usr/bin/time -v python3 run-nexus.py --interactive

# Profile execution
python3 -m cProfile run-nexus.py --task "Create files"
```

### Output Formats
```bash
# JSON output
python3 run-nexus.py --task "List files" --format json

# Plain text
python3 run-nexus.py --task "List files" --format text

# Markdown
python3 run-nexus.py --task "Create report" --format markdown
```

## 🚨 Error Handling

### Common Error Scenarios
```bash
# Handle permission errors
python3 run-nexus.py --task "Create file in /root/" 2>&1 | grep "Permission denied"

# Timeout handling
timeout 30s python3 run-nexus.py --task "Long running task"

# Graceful interruption
python3 run-nexus.py --interactive  # Press Ctrl+C to exit gracefully
```

### Recovery Commands
```bash
# Reset agent state
python3 run-nexus.py --reset --interactive

# Clear working directory
python3 run-nexus.py --task "Clean up temporary files"

# Validate configuration
python3 run-nexus.py --validate-config
```

## 📱 Keyboard Shortcuts

### Interactive Mode Shortcuts
- `Ctrl+C` - Graceful exit
- `Ctrl+D` - EOF exit
- `Ctrl+L` - Clear screen
- `Tab` - Command completion (if available)
- `↑/↓` - Command history (if available)

### Terminal Integration
```bash
# Add to bash aliases
alias nexus='python3 /path/to/Nexus/run-nexus.py'
alias ni='nexus --interactive'
alias nt='nexus --task'
alias nw='nexus --web'

# Add to PATH
export PATH="$PATH:/path/to/Nexus"
```

## 🔄 Automation & Scripting

### Shell Scripts
Create `nexus_tasks.sh`:
```bash
#!/bin/bash

# Daily tasks
python3 run-nexus.py --task "Create daily log file"
python3 run-nexus.py --task "Check system status"
python3 run-nexus.py --task "Backup important files"

# Development tasks
python3 run-nexus.py --task "Update project documentation"
python3 run-nexus.py --task "Run code analysis"
```

### Cron Jobs
```bash
# Add to crontab
crontab -e

# Daily at 9 AM
0 9 * * * cd /path/to/Nexus && python3 run-nexus.py --task "Generate daily report"

# Hourly system check
0 * * * * cd /path/to/Nexus && python3 run-nexus.py --task "Check system health"
```

### Integration with Other Tools
```bash
# Git hooks
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
cd /path/to/Nexus
python3 run-nexus.py --task "Analyze code changes"
EOF

# CI/CD integration
python3 run-nexus.py --task "Run deployment checks" || exit 1
```

## 📚 Best Practices

### Command Structure
```bash
# Good: Clear, specific tasks
python3 run-nexus.py --task "Create a Python script that prints hello world"

# Better: Include context
python3 run-nexus.py --task "Create a Python script for data processing with error handling"

# Best: Specify requirements
python3 run-nexus.py --task "Create a Python script that reads CSV files, processes data with pandas, and outputs results to JSON"
```

### Session Management
```bash
# Start with clear context
python3 run-nexus.py --interactive
Manus> I'm working on a web development project and need help with file structure

# Save important sessions
Manus> save web_project_session.json

# Use descriptive task names
python3 run-nexus.py --task "Setup Flask project structure with templates and static directories"
```

### Performance Optimization
```bash
# Use specific working directories
MANUS_WORKING_DIR=/tmp/nexus python3 run-nexus.py --task "Process temporary files"

# Limit iterations for complex tasks
MAX_ITERATIONS=500 python3 run-nexus.py --task "Complex analysis task"

# Set appropriate timeouts
TIMEOUT_SECONDS=60 python3 run-nexus.py --task "Quick file operation"
```

## 🎯 Use Cases & Examples

### Daily Development Workflow
```bash
# Morning setup
python3 run-nexus.py --task "Check git status and create daily task list"

# Code review
python3 run-nexus.py --task "Analyze Python files for code quality issues"

# Documentation
python3 run-nexus.py --task "Update README with recent changes"

# End of day
python3 run-nexus.py --task "Create progress report and backup files"
```

### System Administration
```bash
# Health check
python3 run-nexus.py --task "Generate system health report"

# Log analysis
python3 run-nexus.py --task "Analyze system logs for errors"

# Cleanup
python3 run-nexus.py --task "Clean up temporary files and optimize storage"
```

### Project Management
```bash
# Project overview
python3 run-nexus.py --task "Create project structure analysis and documentation"

# Task tracking
python3 run-nexus.py --task "Generate TODO list from code comments"

# Progress reporting
python3 run-nexus.py --task "Create weekly progress report"
```

---

**Need help?** 
- Check `HOW_TO_TEST.md` for testing instructions
- See `HOW_TO_DEPLOY.md` for deployment options  
- Review `TROUBLESHOOTING.md` for common issues
- Read `CRITICAL_INFO.md` for important configuration details