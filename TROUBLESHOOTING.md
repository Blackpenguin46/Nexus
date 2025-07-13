# 🔧 Troubleshooting Guide

This comprehensive guide helps resolve common issues with the Nexus autonomous agent framework.

## 🚨 Quick Fixes

### Most Common Issues

| Issue | Quick Fix | Command |
|-------|-----------|---------|
| Module not found | Install dependencies | `pip3 install --user -r requirements.txt` |
| Permission denied | Fix permissions | `chmod 755 data/ && mkdir -p data` |
| Configuration error | Reset config | `echo "LLM__PROVIDER=mock" > .env` |
| Agent hangs | Check timeouts | `timeout 30s python3 run-nexus.py --test` |
| Import errors | Check Python version | `python3 --version` (need 3.10+) |

## 📋 Diagnostic Commands

### System Check
```bash
# Check Python version
python3 --version

# Check dependencies
python3 -c "import manus; print('✅ Imports work')"

# Test basic functionality
python3 run-nexus.py --test

# Check configuration
python3 -c "from manus.core.config import AgentConfig; print('✅ Config loads')"

# Verify permissions
ls -la data/
```

### Environment Validation
```bash
# Check environment variables
env | grep -E "(LLM__|MANUS_|DEBUG_)"

# Validate paths
echo "Working dir: $MANUS_WORKING_DIR"
echo "Python path: $(which python3)"
echo "Current dir: $(pwd)"

# Check disk space
df -h .

# Check memory
free -h  # Linux
vm_stat  # macOS
```

## 🚨 Error Categories

### 1. Installation Issues

#### Error: "ModuleNotFoundError: No module named 'manus'"
**Symptoms:**
```
ModuleNotFoundError: No module named 'manus'
```

**Causes:**
- Missing dependencies
- Wrong Python version
- Incorrect installation path

**Solutions:**
```bash
# Install dependencies
pip3 install --user pydantic pydantic-settings python-dotenv rich fastapi uvicorn aiohttp selenium webdriver-manager PyYAML cryptography validators structlog psutil json5 aiofiles

# Check Python version (need 3.10+)
python3 --version

# Verify installation
python3 -c "import sys; print(sys.path)"

# If still failing, try system install
sudo pip3 install pydantic pydantic-settings python-dotenv rich
```

#### Error: "ImportError: No module named 'torch'"
**Symptoms:**
```
ImportError: No module named 'torch'
```

**Causes:**
- PyTorch not installed (optional dependency)
- Using HuggingFace provider without PyTorch

**Solutions:**
```bash
# Use mock provider (recommended for testing)
echo "LLM__PROVIDER=mock" > .env

# Or install PyTorch (if needed)
pip3 install torch transformers

# Verify mock provider works
python3 run-nexus.py --test
```

### 2. Configuration Issues

#### Error: "Configuration validation failed"
**Symptoms:**
```
pydantic_core._pydantic_core.ValidationError: 1 validation error
```

**Causes:**
- Invalid .env file
- Missing configuration
- Conflicting settings

**Solutions:**
```bash
# Reset configuration
rm .env
cat > .env << EOF
LLM__PROVIDER=mock
AGENT__NAME=nexus-local
DEBUG_MODE=true
MANUS_WORKING_DIR=./data
EOF

# Validate configuration
python3 -c "from manus.core.config import AgentConfig; AgentConfig()"

# Check environment
env | grep LLM__
```

#### Error: "Path '.' is outside allowed directories"
**Symptoms:**
```
SecurityError: Path '.' is outside allowed directories
```

**Causes:**
- Security validator blocking local paths
- Working directory not in allowed paths

**Solutions:**
```bash
# Set working directory
export MANUS_WORKING_DIR=$(pwd)/data
mkdir -p data

# Update configuration
echo "MANUS_WORKING_DIR=./data" >> .env

# Test access
python3 run-nexus.py --task "List files"
```

### 3. Runtime Issues

#### Error: Agent hangs/freezes
**Symptoms:**
- No response from agent
- Process appears stuck
- No output after command

**Causes:**
- Infinite loops
- Missing timeout protection
- Blocking operations

**Solutions:**
```bash
# Force stop
pkill -f "python3 run-nexus.py"

# Test with timeout
timeout 30s python3 run-nexus.py --test

# Check for infinite loops
python3 run-nexus.py --debug --task "Simple task" 2>&1 | tail -50

# Verify timeout fixes are applied
grep -n "timeout" manus/cli.py
```

#### Error: "Command 'ls' is not in allowed list"
**Symptoms:**
```
SecurityError: Command 'ls' is not in allowed list
```

**Causes:**
- Security validator too restrictive
- Missing allowed commands

**Solutions:**
```bash
# Check security configuration
python3 -c "from manus.security.validator import SecurityValidator; print('Security OK')"

# Verify allowed commands
grep -A 10 "ALLOWED_COMMANDS" manus/security/validator.py

# Test with basic command
python3 run-nexus.py --task "Show current directory"
```

#### Error: Tool execution fails
**Symptoms:**
```
❌ Error: Missing required argument: directory
```

**Causes:**
- Tool parameter mismatch
- Missing arguments
- Invalid tool configuration

**Solutions:**
```bash
# Check tool registry
python3 -c "from manus.tools.registry import ToolRegistry; print('Tools OK')"

# Debug tool execution
python3 run-nexus.py --debug --task "List files"

# Test specific tool
python3 -c "from manus.tools.file_tools import FileTools; print('File tools OK')"
```

### 4. Permission Issues

#### Error: "Permission denied"
**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: '/path/to/file'
```

**Causes:**
- Insufficient file permissions
- Directory not writable
- Security restrictions

**Solutions:**
```bash
# Fix data directory permissions
chmod 755 data/
mkdir -p data

# Check current permissions
ls -la data/

# Set working directory
export MANUS_WORKING_DIR=$(pwd)/data

# Test permissions
touch data/test.txt && rm data/test.txt
```

#### Error: Docker permission issues
**Symptoms:**
```
docker: permission denied while trying to connect to the Docker daemon socket
```

**Solutions:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Or use sudo
sudo docker build -t nexus-agent .

# Test Docker access
docker --version
```

### 5. Network Issues

#### Error: Web interface not accessible
**Symptoms:**
- Browser can't connect to localhost:8080
- Connection refused errors

**Causes:**
- Port already in use
- Firewall blocking
- Service not started

**Solutions:**
```bash
# Check port usage
lsof -i :8080  # macOS/Linux
netstat -an | grep 8080  # Windows

# Use different port
python3 run-nexus.py --web --port 8081

# Check firewall
sudo ufw status  # Ubuntu
sudo firewall-cmd --list-ports  # CentOS

# Test local connection
curl http://localhost:8080/health
```

## 🔍 Advanced Debugging

### Enable Debug Logging
```bash
# Enable debug mode
export DEBUG_MODE=true
python3 run-nexus.py --debug --interactive

# Check log files
tail -f logs/agent.log

# Debug specific component
python3 -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from manus.core.agent import ManusAgent
print('Debug enabled')
"
```

### Memory Debugging
```bash
# Check memory usage
python3 -c "
import psutil
import subprocess
import time

proc = subprocess.Popen(['python3', 'run-nexus.py', '--test'])
time.sleep(5)
process = psutil.Process(proc.pid)
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')
proc.terminate()
"

# Monitor memory over time
while true; do
    ps aux | grep "run-nexus.py" | grep -v grep
    sleep 5
done
```

### Performance Profiling
```bash
# Profile execution
python3 -m cProfile -o profile.out run-nexus.py --test

# Analyze profile
python3 -c "
import pstats
p = pstats.Stats('profile.out')
p.sort_stats('cumulative').print_stats(10)
"

# Time execution
time python3 run-nexus.py --test
```

### Network Debugging
```bash
# Check network connectivity
ping -c 3 8.8.8.8

# Test local connections
nc -zv localhost 8080

# Check DNS resolution
nslookup localhost

# Monitor network traffic
sudo netstat -tulpn | grep python
```

## 🔧 Recovery Procedures

### Complete Reset
```bash
#!/bin/bash
# reset_nexus.sh

echo "🔄 Resetting Nexus Agent..."

# Stop any running instances
pkill -f "python3 run-nexus.py"

# Clear temporary files
rm -rf data/*
rm -f logs/*.log

# Reset configuration
cat > .env << EOF
LLM__PROVIDER=mock
AGENT__NAME=nexus-reset
DEBUG_MODE=true
MANUS_WORKING_DIR=./data
EOF

# Recreate directories
mkdir -p data logs
chmod 755 data logs

# Test basic functionality
python3 run-nexus.py --test

echo "✅ Reset complete"
```

### Dependency Reinstall
```bash
#!/bin/bash
# reinstall_deps.sh

echo "📦 Reinstalling dependencies..."

# Remove existing packages
pip3 uninstall -y pydantic pydantic-settings python-dotenv rich fastapi uvicorn

# Clear pip cache
pip3 cache purge

# Reinstall with latest versions
pip3 install --user --upgrade pydantic pydantic-settings python-dotenv rich fastapi uvicorn aiohttp selenium webdriver-manager PyYAML cryptography validators structlog psutil json5 aiofiles

# Verify installation
python3 -c "import manus; print('✅ Installation verified')"

echo "✅ Dependencies reinstalled"
```

### Configuration Recovery
```bash
#!/bin/bash
# recover_config.sh

echo "⚙️ Recovering configuration..."

# Backup current config
if [ -f .env ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
fi

# Create minimal working config
cat > .env << EOF
# Core Configuration
LLM__PROVIDER=mock
AGENT__NAME=nexus-recovery
DEBUG_MODE=true

# Paths
MANUS_WORKING_DIR=./data
LOG_DIR=./logs

# Security
SECURITY__ALLOWED_DOMAINS=localhost,127.0.0.1
SECURITY__BLOCKED_PORTS=22,23,25,53,135,139,445

# Performance
MAX_ITERATIONS=1000
TIMEOUT_SECONDS=300
EOF

# Test configuration
python3 -c "from manus.core.config import AgentConfig; AgentConfig(); print('✅ Config valid')"

echo "✅ Configuration recovered"
```

## 📊 System Requirements Check

### Minimum Requirements Validator
```bash
#!/bin/bash
# check_requirements.sh

echo "🔍 Checking system requirements..."

# Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "Python version: $PYTHON_VERSION"
if [[ $(echo "$PYTHON_VERSION" | cut -d'.' -f1-2) < "3.10" ]]; then
    echo "❌ Python 3.10+ required"
    exit 1
else
    echo "✅ Python version OK"
fi

# Memory
MEMORY_GB=$(free -m | awk '/^Mem:/{print int($2/1024)}' 2>/dev/null || echo "unknown")
echo "Memory: ${MEMORY_GB}GB"
if [[ "$MEMORY_GB" != "unknown" && "$MEMORY_GB" -lt 2 ]]; then
    echo "⚠️ Low memory (2GB+ recommended)"
else
    echo "✅ Memory OK"
fi

# Disk space
DISK_SPACE=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
echo "Disk space: ${DISK_SPACE}GB available"
if [[ "$DISK_SPACE" -lt 5 ]]; then
    echo "⚠️ Low disk space (5GB+ recommended)"
else
    echo "✅ Disk space OK"
fi

# Dependencies
echo "Checking dependencies..."
python3 -c "
try:
    import pydantic, rich, fastapi
    print('✅ Core dependencies OK')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
    exit(1)
"

echo "✅ All requirements met"
```

## 🐛 Known Issues & Workarounds

### Issue: PyTorch conflicts on Apple Silicon
**Problem:** PyTorch installation conflicts on M1/M2 Macs

**Workaround:**
```bash
# Use mock provider instead
echo "LLM__PROVIDER=mock" > .env

# Or install specific PyTorch version
pip3 install torch --index-url https://download.pytorch.org/whl/cpu
```

### Issue: Docker build fails on ARM
**Problem:** Docker build fails on ARM-based systems

**Workaround:**
```bash
# Use platform-specific build
docker build --platform linux/amd64 -t nexus-agent .

# Or use native ARM build
docker build --platform linux/arm64 -t nexus-agent .
```

### Issue: Web interface CORS errors
**Problem:** Browser blocks cross-origin requests

**Workaround:**
```bash
# Start with CORS enabled
ENABLE_CORS=true python3 run-nexus.py --web

# Or access via proper domain
echo "127.0.0.1 nexus.local" | sudo tee -a /etc/hosts
# Access via http://nexus.local:8080
```

### Issue: High memory usage
**Problem:** Agent consumes excessive memory

**Workaround:**
```bash
# Limit iterations
MAX_ITERATIONS=100 python3 run-nexus.py --interactive

# Use smaller timeout
TIMEOUT_SECONDS=60 python3 run-nexus.py --task "Quick task"

# Clear memory periodically
python3 -c "
import gc
gc.collect()
"
```

## 📞 Getting Help

### Information to Collect
When reporting issues, include:

```bash
# System information
python3 --version
uname -a
df -h .
free -h

# Agent information
cat .env
python3 -c "import manus; print(manus.__version__ if hasattr(manus, '__version__') else 'dev')"

# Error reproduction
python3 run-nexus.py --debug --test 2>&1 | head -50

# Configuration
env | grep -E "(LLM__|MANUS_|DEBUG_)"
```

### Self-Diagnosis Script
```bash
#!/bin/bash
# diagnose.sh

echo "🔍 Nexus Agent Diagnostics"
echo "=========================="

echo "System Information:"
echo "- OS: $(uname -s) $(uname -r)"
echo "- Python: $(python3 --version)"
echo "- Working Dir: $(pwd)"
echo "- User: $(whoami)"

echo -e "\nDependency Check:"
python3 -c "
deps = ['pydantic', 'rich', 'fastapi', 'uvicorn']
for dep in deps:
    try:
        __import__(dep)
        print(f'✅ {dep}')
    except ImportError:
        print(f'❌ {dep}')
"

echo -e "\nConfiguration:"
if [ -f .env ]; then
    echo "✅ .env file exists"
    grep -E "^[A-Z]" .env | head -5
else
    echo "❌ No .env file"
fi

echo -e "\nPermissions:"
if [ -d data ]; then
    echo "✅ data/ directory exists"
    ls -la data/ | head -3
else
    echo "❌ No data/ directory"
fi

echo -e "\nBasic Test:"
timeout 30s python3 run-nexus.py --test >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Basic test passed"
else
    echo "❌ Basic test failed"
fi

echo -e "\nDiagnostics complete!"
```

### Support Channels
1. **Check documentation**: Read all `.md` files in project root
2. **Review logs**: Check `logs/` directory for error details
3. **Search issues**: Look for similar problems in project issues
4. **Create bug report**: Include full diagnostic information

---

**Remember**: Most issues are configuration-related. Start with a complete reset using the recovery procedures above before seeking help.