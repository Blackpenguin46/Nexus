# Manus Remake - Autonomous AI Agent

A production-ready autonomous AI agent inspired by ManusAI, featuring Claude 3.5 Sonnet integration, secure container sandboxing, and comprehensive tool orchestration.

## 🚀 Features

- **Autonomous Task Execution**: ReAct + CodeAct hybrid architecture for complex reasoning and action
- **Security-First Design**: Zero-trust validation, container sandboxing, and input sanitization
- **Claude Integration**: Native Claude 3.5 Sonnet API with tool calling and computer use capabilities
- **Comprehensive Tools**: File operations, shell commands, browser automation, and web search
- **Production Ready**: Error recovery, monitoring, logging, and performance metrics
- **Multiple Interfaces**: CLI, web API, and interactive chat modes

## 🏗️ Architecture

### Core Components

- **Agent Loop**: ReAct-based reasoning cycle with CodeAct code execution
- **Tool Registry**: Extensible tool system with schema validation
- **Security Validator**: Zero-trust security with comprehensive input validation
- **State Management**: Persistent conversation and task state across sessions

### Security Features

- Docker container isolation with rootless execution
- Command allowlist validation and pattern filtering
- Path traversal protection and file access controls
- Network request filtering and domain allowlists
- Real-time security monitoring and audit logging

## 📦 Installation

### Prerequisites

- Python 3.10+
- Docker Desktop (optional, for containerized deployment)

### 🚀 Quick Start (3 Steps)

1. **Clone and Install Dependencies**:
```bash
git clone <repository-url>
cd Nexus
pip3 install --user pydantic pydantic-settings python-dotenv rich fastapi uvicorn aiohttp selenium webdriver-manager PyYAML cryptography validators structlog psutil json5 aiofiles
```

2. **Test the Agent** (No additional setup required):
```bash
# Quick demo test
python3 run-nexus.py --test

# Interactive mode
python3 run-nexus.py --interactive

# Single task
python3 run-nexus.py --task "Hello! Please introduce yourself"
```

3. **Docker Setup** (Optional):
```bash
# Web interface on http://localhost:8080
./setup-test.sh
./run-test.sh web
```

### ⚠️ IMPORTANT for Git Clone Users

**If you cloned this repo, the following fixes have been applied:**

- ✅ PyTorch made optional (use `LLM__PROVIDER=mock` for testing)
- ✅ Working directory changed from `/app/data` to `./data`
- ✅ Terminal freeze issues fixed with timeout protection
- ✅ Configuration simplified for local development

**See `SETUP.md` for detailed setup instructions.**

### Development Setup

1. **Local Development**:
```bash
# Use the simple test runner (recommended)
python3 run-nexus.py --interactive

# Or traditional method (requires proper .env setup)
python -m manus.cli --debug
```

2. **Docker Development**:
```bash
# Interactive mode
./run-test.sh interactive

# Web server mode  
./run-test.sh web
```

### Configuration

**For local testing** (in `.env`):
```bash
LLM__PROVIDER=mock          # Use mock for testing
AGENT__NAME=nexus-agent
DEBUG_MODE=true
MANUS_WORKING_DIR=./data
```

**For production** (add your API keys):
```bash
LLM__PROVIDER=anthropic     # Or huggingface, ollama
ANTHROPIC_API_KEY=your_key_here
```

## 🎯 Usage

### Interactive Mode

```bash
# Start interactive session
docker run -it --rm -v $(pwd)/data:/app/data --env-file .env manus-agent

# Available commands:
# - Type any task: "Create a web scraper for news articles"
# - status: Show agent status and metrics
# - history: Show conversation history
# - clear: Clear conversation history
# - reset: Reset entire session
# - help: Show help information
# - exit: Exit the agent
```

### Command Line Interface

```bash
# Execute single task
docker run --rm -v $(pwd)/data:/app/data --env-file .env manus-agent \
  --task "Analyze the file data/report.csv and create a summary"

# Show status
docker run --rm -v $(pwd)/data:/app/data --env-file .env manus-agent --status

# Debug mode
docker run --rm -v $(pwd)/data:/app/data --env-file .env manus-agent \
  --debug --task "Debug the Python script in data/app.py"
```

### Web API

```bash
# Start web server
docker run -p 8000:8000 --rm -v $(pwd)/data:/app/data --env-file .env manus-agent --web

# API endpoints:
# GET  /status        - Agent status
# POST /task          - Execute task
# POST /chat          - Chat interface  
# GET  /history       - Conversation history
# GET  /tools         - Available tools
# GET  /metrics       - Performance metrics
# GET  /docs          - API documentation (debug mode)
```

## 🛠️ Available Tools

### File Operations
- `file_read` - Read file contents with encoding detection
- `file_write` - Atomic file writing with backup
- `file_append` - Append content to files
- `file_delete` - Safe file deletion with confirmation
- `file_copy` - Copy files with overwrite protection
- `file_move` - Move files atomically
- `file_list` - List directory contents with metadata
- `file_info` - Detailed file/directory information
- `directory_create` - Create directories with parent support

### Shell Operations
- `shell_exec` - Execute shell commands with validation
- `shell_which` - Find command locations
- `shell_pwd` - Get current working directory
- `shell_cd` - Change working directory
- `shell_ls` - List directory contents
- `shell_cat` - Display file contents
- `shell_grep` - Search text patterns in files
- `shell_find` - Find files and directories
- `shell_env` - Get environment variables
- `shell_ps` - List running processes

### Browser Automation (Planned)
- `browser_navigate` - Navigate to URLs
- `browser_click` - Click page elements
- `browser_input` - Fill form fields
- `browser_scroll` - Scroll page content
- `browser_screenshot` - Capture screenshots

### Information & Search (Planned)
- `search_web` - Web search integration
- `search_image` - Image search capabilities
- `info_fetch_url` - Direct URL content retrieval

## ⚙️ Configuration

Configuration is managed through environment variables and the `.env` file:

### Claude API Settings
```bash
ANTHROPIC_API_KEY=your_api_key
LLM__MODEL=claude-3-5-sonnet-20241022
LLM__MAX_TOKENS=4000
LLM__TEMPERATURE=0.0
```

### Security Settings
```bash
SECURITY__ALLOWED_DOMAINS=api.anthropic.com,googleapis.com
SECURITY__BLOCKED_PORTS=22,23,135,139,445
SECURITY__MAX_FILE_SIZE_MB=100
SECURITY__ENABLE_SECURITY_SCANNING=true
```

### Agent Behavior
```bash
AGENT__MAX_ITERATIONS=50
AGENT__TIMEOUT_SECONDS=300
AGENT__ENABLE_REFLECTION=true
AGENT__ENABLE_PLANNING=true
```

## 📊 Monitoring & Metrics

The agent provides comprehensive monitoring:

- **Performance Metrics**: Response times, success rates, resource usage
- **Security Events**: Validation failures, blocked operations, audit trail
- **Tool Analytics**: Usage statistics, success rates, error patterns
- **System Health**: CPU, memory, disk usage monitoring

Access metrics via:
- Web API: `GET /metrics`
- CLI: `manus --status`
- Logs: Structured JSON logging with security-aware formatting

## 🔒 Security

### Container Security
- Rootless execution with minimal privileges
- Resource limits (CPU, memory, disk)
- Network isolation with domain allowlists
- Read-only filesystem where possible

### Input Validation
- Command injection prevention
- Path traversal protection
- SQL injection filtering
- XSS protection for web inputs

### Monitoring
- Real-time security event logging
- Anomaly detection for suspicious patterns
- Audit trail for all operations
- Error analysis and alerting

## 🧪 Testing

```bash
# Run test suite
poetry run pytest

# Security tests
poetry run pytest tests/security/

# Performance benchmarks
poetry run pytest tests/performance/ -m slow

# Integration tests
poetry run pytest tests/integration/
```

## 📋 Development

### Project Structure
```
manus/
├── core/           # Core agent logic
├── tools/          # Tool implementations
├── security/       # Security validation
├── utils/          # Utilities (logging, metrics)
├── api/            # Web API server
└── cli.py          # Command line interface
```

### Adding Tools

1. Create tool class in `manus/tools/`
2. Implement methods with proper docstrings
3. Register with tool registry
4. Add security validation rules
5. Write tests

Example:
```python
class MyTools:
    def my_tool(self, param: str) -> str:
        """Tool description for Claude."""
        # Implementation
        return result
```

### Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Ensure security compliance
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Inspired by ManusAI's autonomous agent architecture
- Built on Anthropic's Claude AI capabilities
- Follows security best practices from OWASP and NIST

---

**Note**: This is an autonomous AI agent capable of executing code and interacting with systems. Always review and understand the agent's capabilities before deployment in production environments.