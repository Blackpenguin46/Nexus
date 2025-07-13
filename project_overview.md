# Nexus - Autonomous AI Agent Framework

## Project Overview

Nexus (originally "Manus Remake") is a production-ready autonomous AI agent framework designed for complex task execution with a focus on security, reliability, and extensibility. The project implements a hybrid ReAct + CodeAct architecture that combines reasoning with executable actions.

## 🎯 Project Goals

- Create a secure, containerized autonomous agent capable of executing complex multi-step tasks
- Implement production-grade security with zero-trust validation
- Provide multiple interfaces: CLI, web API, and interactive modes
- Support both local and cloud LLM providers with optimizations for Apple Silicon
- Enable extensible tool ecosystem for diverse capabilities

## 🏗️ Architecture

### Core Components

1. **Agent Loop** (`manus/core/loop.py`)
   - ReAct + CodeAct hybrid architecture
   - Iterative: perceive → think → act → observe → reflect
   - Built-in timeout protection and error recovery

2. **Tool Registry** (`manus/tools/`)
   - Centralized tool management with schema validation
   - Security integration for all tool executions
   - File operations, shell commands, browser automation (planned)

3. **Security Layer** (`manus/security/`)
   - Zero-trust input validation
   - Command injection prevention
   - Path traversal protection
   - Network domain allowlists

4. **State Management** (`manus/core/state.py`)
   - Persistent conversation and task tracking
   - Session management across restarts
   - Metrics collection and analytics

5. **LLM Providers** (`manus/core/llm_providers.py`)
   - Unified interface for multiple providers
   - HuggingFace (local models with Apple Silicon optimization)
   - Ollama (local model server)
   - Mock provider (for testing/demo)

## 🔧 Technology Stack

- **Language**: Python 3.11+
- **Containerization**: Docker with security hardening
- **Web Framework**: FastAPI for REST API
- **CLI Interface**: Rich for interactive experience
- **ML Framework**: PyTorch with Metal Performance Shaders (MPS) support
- **Security**: Custom validation layer with input sanitization
- **State Persistence**: JSON-based with backup support

## 🚀 Features

### Implemented
- ✅ Autonomous agent loop with timeout protection
- ✅ Secure file system operations
- ✅ Shell command execution with validation
- ✅ Interactive CLI and web API interfaces
- ✅ Session state persistence
- ✅ Comprehensive logging and metrics
- ✅ Docker containerization with security hardening

### Planned
- 🔄 Browser automation tools (Selenium integration)
- 🔄 Web search and information retrieval
- 🔄 Claude API integration
- 🔄 Comprehensive testing suite
- 🔄 Performance benchmarking

## 🔒 Security Features

- **Container Isolation**: Rootless execution with resource limits
- **Input Validation**: Command injection and path traversal prevention
- **Network Controls**: Domain allowlists and port blocking
- **File System Protection**: Safe base directories and access controls
- **Audit Logging**: Security event monitoring and tracking

## 🎮 Usage Modes

### Interactive Mode
```bash
python -m manus.cli
```

### Single Task Execution
```bash
python -m manus.cli --task "Create a Python script to calculate fibonacci numbers"
```

### Web API Server
```bash
python -m manus.cli --web --port 8000
```

## 🏃‍♂️ Quick Start

1. **Setup Environment**
   ```bash
   cd /Users/zaymasta/Nexusv2.0/Nexus
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.template .env
   # Edit .env with your configuration
   ```

3. **Run Agent**
   ```bash
   # Interactive mode
   python -m manus.cli
   
   # Or with Docker
   docker build -t nexus-agent .
   docker run -it --rm -v $(pwd)/data:/app/data nexus-agent
   ```

## 🐛 Recent Debugging and Fixes

### Terminal Freeze Issues (Resolved)

**Problems Identified:**
1. Infinite loop in CLI without proper signal handling
2. Blocking LLM model loading operations
3. Synchronous input calls without timeouts
4. Lack of iteration limits and timeout protection

**Fixes Applied:**
- Added timeout protection for user input (`asyncio.wait_for` with 5-minute timeout)
- Implemented iteration limits (max 1000 attempts) to prevent infinite loops
- Added per-iteration timeouts (60 seconds) in agent loop
- Improved model loading with timeout protection (5 minutes total, 3 minutes for model)
- Enhanced error handling with graceful shutdown
- Added shutdown request checking in loops

### Performance Optimizations
- Model loading timeout protection prevents terminal freezing
- Async operation wrapping for blocking calls
- Process isolation for shell commands
- Resource cleanup on shutdown

## 📁 Project Structure

```
nexus/
├── manus/                  # Core agent package
│   ├── core/              # Agent logic, state, configuration
│   │   ├── agent.py       # Main agent orchestrator
│   │   ├── loop.py        # Agent execution loop
│   │   ├── config.py      # Configuration management
│   │   ├── state.py       # State persistence
│   │   └── llm_providers.py # LLM provider implementations
│   ├── tools/             # Tool implementations
│   │   ├── registry.py    # Tool management
│   │   ├── file_tools.py  # File operations
│   │   └── shell_tools.py # Shell commands
│   ├── security/          # Security validation
│   │   └── validator.py   # Input validation and filtering
│   ├── utils/             # Utilities
│   │   ├── logger.py      # Structured logging
│   │   └── metrics.py     # Performance metrics
│   ├── api/               # Web API server
│   │   └── server.py      # FastAPI application
│   └── cli.py             # Command line interface
├── data/                  # Agent data directory
├── docs/                  # Documentation
├── tests/                 # Test suite (structure ready)
├── Dockerfile             # Container definition
├── docker-compose.yml     # Development environment
├── pyproject.toml         # Python project configuration
└── requirements.txt       # Python dependencies
```

## 🎯 Success Metrics

- **Task Completion Rate**: Target >90%
- **Response Time**: <30 seconds for complex tasks
- **Container Startup**: <10 seconds
- **Memory Usage**: <2GB per instance
- **Security**: Zero critical vulnerabilities

## 🔮 Future Roadmap

1. **Q1 2024**: Complete browser automation tools
2. **Q2 2024**: Implement comprehensive testing suite
3. **Q3 2024**: Performance optimization and benchmarking
4. **Q4 2024**: Production deployment and monitoring

## 🤝 Contributing

The project follows secure development practices:
- All tool implementations require security validation
- Code changes must include appropriate tests
- Security reviews required for tool additions
- Documentation updates for new features

## 📄 License

MIT License - See LICENSE file for details

---

**Note**: This is an autonomous AI agent capable of executing code and interacting with systems. Always review and understand the agent's capabilities before deployment in production environments.