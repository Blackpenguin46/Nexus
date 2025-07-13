# Nexus Agent Setup Guide

## 🚨 IMPORTANT: Required Changes for Local Development

**If you cloned this repository, you MUST make these changes to run locally:**

### 1. Install Python Dependencies

The agent requires specific Python packages. Install them first:

```bash
# Core dependencies (REQUIRED)
pip3 install --user pydantic pydantic-settings python-dotenv rich fastapi uvicorn aiohttp selenium webdriver-manager PyYAML cryptography validators structlog psutil json5 aiofiles

# Optional: For full ML functionality (large download)
pip3 install --user torch transformers tokenizers accelerate
```

### 2. Environment Configuration

Create a `.env` file with these settings (or use the existing one):

```bash
# Copy the template if needed
cp .env.template .env
```

**Key environment variables for local testing:**
```bash
# LLM Configuration (CRITICAL - Use mock for testing)
LLM__PROVIDER=mock
LLM__MODEL=mock-model

# Agent Configuration
AGENT__NAME=nexus-agent
AGENT__MAX_ITERATIONS=20
AGENT__TIMEOUT_SECONDS=120

# Security (use defaults for testing)
SECURITY__ALLOWED_DOMAINS=api.anthropic.com,googleapis.com,github.com,pypi.org
SECURITY__ENABLE_SECURITY_SCANNING=true

# Debug mode (recommended for testing)
DEBUG_MODE=true
LOGGING__LEVEL=INFO

# Local working directory (IMPORTANT)
MANUS_WORKING_DIR=./data
```

### 3. Fixed Code Issues

**⚠️ CRITICAL FIXES ALREADY APPLIED:**

1. **PyTorch Optional Import** (`manus/core/llm_providers.py`):
   - Made torch imports conditional to allow testing without ML dependencies
   - Added `TORCH_AVAILABLE` flag for graceful degradation

2. **Working Directory Fix** (`manus/tools/shell_tools.py`):
   - Changed from hardcoded `/app/data` to configurable path
   - Added fallback to local `./data` directory for development

3. **Timeout Protection** (Multiple files):
   - Added 5-minute timeout for user input
   - Added 60-second per-iteration timeout
   - Added model loading timeout protection
   - Fixed infinite loop prevention

## 🚀 Quick Start (3 Steps)

### Step 1: Clone and Install
```bash
git clone <repository-url>
cd Nexus
pip3 install --user pydantic pydantic-settings python-dotenv rich fastapi uvicorn aiohttp selenium webdriver-manager PyYAML cryptography validators structlog psutil json5 aiofiles
```

### Step 2: Test the Agent
```bash
# Quick test (recommended first)
python3 run-nexus.py --test

# Interactive mode
python3 run-nexus.py --interactive

# Single task
python3 run-nexus.py --task "Hello! Please introduce yourself"
```

### Step 3: Docker (Optional)
```bash
# Build and run web interface
./setup-test.sh
./run-test.sh web
# Visit http://localhost:8080
```

## 🛠️ Development Files Created

**New files for easy testing:**

1. **`run-nexus.py`** - Simple test runner (bypasses complex config)
2. **`test-minimal.py`** - Minimal component test
3. **`test-interactive.py`** - Interactive tool testing
4. **`setup-test.sh`** - Docker setup script
5. **`run-test.sh`** - Docker test runner
6. **`docker-compose.test.yml`** - Test-specific Docker config

## 🔧 Key Code Modifications Made

### 1. LLM Provider (`manus/core/llm_providers.py`)
```python
# ADDED: Optional torch imports
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

# ADDED: Check in HuggingFace provider
def __init__(self, config: LLMConfig):
    if not TORCH_AVAILABLE:
        raise LLMError("PyTorch required for HuggingFace provider")
```

### 2. Shell Tools (`manus/tools/shell_tools.py`)
```python
# CHANGED: From hardcoded path to configurable
# OLD: self.working_directory = "/app/data"
# NEW:
self.working_directory = os.environ.get('MANUS_WORKING_DIR', "/app/data")
if not Path(self.working_directory).parent.exists():
    self.working_directory = str(Path.cwd() / "data")
```

### 3. CLI Interface (`manus/cli.py`)
```python
# ADDED: Timeout protection for user input
user_input = await asyncio.wait_for(
    asyncio.to_thread(Prompt.ask, "\n[bold blue]Manus[/bold blue]"),
    timeout=300.0  # 5 minute timeout
)

# ADDED: Iteration limits
max_attempts = 1000
while attempt_count < max_attempts and not agent._shutdown_requested:
```

### 4. Agent Loop (`manus/core/loop.py`)
```python
# ADDED: Per-iteration timeout
should_continue = await asyncio.wait_for(
    self._execute_iteration(state, iteration),
    timeout=60.0  # 60 second timeout
)
```

## 🐛 Issues Fixed

### Terminal Freeze Issues (RESOLVED)
- ✅ Infinite loops in CLI
- ✅ Blocking model loading
- ✅ Synchronous input without timeouts
- ✅ Lack of iteration limits

### Configuration Issues (RESOLVED)
- ✅ PyTorch dependency requirements
- ✅ Complex nested configuration parsing
- ✅ Hardcoded container paths

### Security Features (WORKING)
- ✅ Command validation
- ✅ Path traversal protection
- ✅ Input sanitization
- ✅ Container isolation

## 📋 Testing Checklist

Before reporting issues, verify:

- [ ] Python 3.10+ installed
- [ ] All dependencies installed via pip
- [ ] `.env` file configured with `LLM__PROVIDER=mock`
- [ ] `data/` directory exists and is writable
- [ ] Run `python3 run-nexus.py --test` successfully

## 🆘 Troubleshooting

### "Module not found" errors
```bash
pip3 install --user pydantic pydantic-settings python-dotenv rich fastapi uvicorn
```

### "Configuration Error"
```bash
# Check your .env file has:
LLM__PROVIDER=mock
DEBUG_MODE=true
```

### "Permission denied" or path errors
```bash
# Ensure data directory exists
mkdir -p data
chmod 755 data
```

### Docker issues
```bash
# Rebuild if needed
docker compose -f docker-compose.test.yml build --no-cache
```

## 🎯 Next Steps

1. **Test locally** with mock provider
2. **Add Claude API key** to `.env` for full functionality
3. **Install PyTorch** for local LLM support
4. **Extend tools** for your specific use case

## 📚 Important Files to Review

- `TESTING.md` - Complete testing instructions
- `project_overview.md` - Project architecture and features
- `docs/activity.md` - Detailed debugging log
- `.env` - Environment configuration
- `run-nexus.py` - Simple test runner

**Remember: Always use the mock provider (`LLM__PROVIDER=mock`) for initial testing!**