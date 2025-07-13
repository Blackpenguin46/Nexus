# 🧪 How to Test Nexus Agent

This guide provides comprehensive testing instructions for the Nexus autonomous agent framework.

## 📋 Prerequisites

Before testing, ensure you have:
- Python 3.10+ installed
- All dependencies installed
- Proper directory permissions

## 🚀 Quick Setup & Test

```bash
# 1. Install dependencies
pip3 install --user pydantic pydantic-settings python-dotenv rich fastapi uvicorn aiohttp selenium webdriver-manager PyYAML cryptography validators structlog psutil json5 aiofiles

# 2. Verify installation
python3 -c "import manus; print('✅ Nexus imported successfully')"

# 3. Run quick test
python3 run-nexus.py --test
```

## 🎯 Testing Modes

### 1. Demo Test (Recommended First)
```bash
python3 run-nexus.py --test
```
**What it tests:**
- Agent initialization
- Basic tool execution
- Reasoning pipeline
- Security validation

**Expected output:**
```
🎯 Task: Hello! Please introduce yourself
============================================================
🤖 Agent Response:
Let me check our current environment and working directory to understand the context better.

🔧 Executing 1 tool(s):
  1. shell_pwd({})
     ✅ Result: /Users/your-path/Nexus/data...
```

### 2. Interactive Mode
```bash
python3 run-nexus.py --interactive
```
**Test scenarios:**
- Conversation continuity
- Multi-turn reasoning
- Context memory
- User interruption handling

**Example conversation:**
```
Manus> hello
Agent: Let me check our current environment...
Manus> create a python script
Agent: I'll create a Python script template for you...
Manus> exit
```

### 3. Single Task Mode
```bash
python3 run-nexus.py --task "Create a hello world script"
```
**Test different task types:**
- File operations: `"Create a README file"`
- System info: `"What's the current date and system info?"`
- Analysis: `"List all files in this directory"`
- Complex: `"Create a complete Python project structure"`

### 4. Web Interface Mode
```bash
python3 run-nexus.py --web
# Visit http://localhost:8080
```

## 🔬 Advanced Testing

### Security Validation Tests
```bash
# Test path traversal protection
python3 run-nexus.py --task "Read the file ../../../etc/passwd"

# Test command validation
python3 run-nexus.py --task "Run rm -rf /"

# Test allowed operations
python3 run-nexus.py --task "Show current directory"
```

### Reasoning Engine Tests
```bash
# Test multi-step reasoning
python3 run-nexus.py --task "First check the date, then create a log file, and finally list all files"

# Test intent classification
python3 run-nexus.py --task "I need help debugging this broken code"

# Test complexity detection
python3 run-nexus.py --task "Analyze this codebase and create comprehensive documentation"
```

### Tool Orchestration Tests
```bash
# File operations
python3 run-nexus.py --task "Create a config.json file with default settings"

# System operations
python3 run-nexus.py --task "Show me system information and running processes"

# Development tasks
python3 run-nexus.py --task "Create a Python script that processes CSV data"
```

## 🐳 Docker Testing

### Build and Test
```bash
# Build Docker image
docker build -t nexus-agent .

# Test in container
docker run --rm -it nexus-agent python3 run-nexus.py --test

# Interactive container test
docker run --rm -it nexus-agent python3 run-nexus.py --interactive

# Web interface test
docker run --rm -p 8080:8080 nexus-agent python3 run-nexus.py --web
```

### Docker Compose Testing
```bash
# Start services
docker-compose up -d

# Test web interface
curl http://localhost:8080/health

# View logs
docker-compose logs nexus-agent

# Stop services
docker-compose down
```

## 📊 Performance Testing

### Load Testing
```bash
# Multiple concurrent requests
for i in {1..10}; do
  python3 run-nexus.py --task "Create file_$i.txt" &
done
wait
```

### Memory Usage Testing
```bash
# Monitor memory during execution
python3 -c "
import psutil
import subprocess
import time

# Start agent
proc = subprocess.Popen(['python3', 'run-nexus.py', '--interactive'])
time.sleep(2)

# Monitor memory
process = psutil.Process(proc.pid)
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB')
proc.terminate()
"
```

### Timeout Testing
```bash
# Test timeout protection
timeout 10s python3 run-nexus.py --interactive
```

## 🛡️ Security Testing

### Input Validation
```bash
# Test malicious inputs
python3 run-nexus.py --task "'; rm -rf /; echo 'hacked'"
python3 run-nexus.py --task "../../../etc/passwd"
python3 run-nexus.py --task "<script>alert('xss')</script>"
```

### Permission Testing
```bash
# Test file permissions
chmod 000 data/
python3 run-nexus.py --task "Create a file in data directory"
chmod 755 data/
```

### Network Security
```bash
# Test blocked domains (should fail safely)
python3 run-nexus.py --task "Download from malicious-site.com"
```

## 🔧 Troubleshooting Tests

### Dependency Issues
```bash
# Test without optional dependencies
pip3 uninstall torch transformers -y
python3 run-nexus.py --test  # Should still work with mock provider
```

### Configuration Issues
```bash
# Test with invalid config
echo "INVALID_CONFIG=true" > .env
python3 run-nexus.py --test

# Reset config
rm .env
echo "LLM__PROVIDER=mock" > .env
```

### Path Issues
```bash
# Test with missing data directory
rm -rf data/
python3 run-nexus.py --test  # Should create directory automatically
```

## 📈 Continuous Integration Testing

### Automated Test Suite
Create `test_runner.py`:
```python
#!/usr/bin/env python3
import subprocess
import sys

def run_test(name, command):
    print(f"Running {name}...")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ {name} PASSED")
        return True
    else:
        print(f"❌ {name} FAILED")
        print(result.stderr)
        return False

tests = [
    ("Import Test", "python3 -c 'import manus'"),
    ("Demo Test", "timeout 30s python3 run-nexus.py --test"),
    ("File Creation", "python3 run-nexus.py --task 'Create test.txt'"),
    ("System Info", "python3 run-nexus.py --task 'What is the current date?'"),
]

passed = 0
for name, command in tests:
    if run_test(name, command):
        passed += 1

print(f"\nResults: {passed}/{len(tests)} tests passed")
sys.exit(0 if passed == len(tests) else 1)
```

Run with:
```bash
python3 test_runner.py
```

## 🎮 Interactive Testing Scenarios

### Scenario 1: Development Workflow
```bash
python3 run-nexus.py --interactive
```
```
> Create a Python project structure
> Add a main.py file with hello world
> Create a requirements.txt file
> List all created files
> exit
```

### Scenario 2: System Administration
```bash
python3 run-nexus.py --interactive
```
```
> Check current system information
> Show running processes
> Create a system report file
> exit
```

### Scenario 3: Data Analysis
```bash
python3 run-nexus.py --interactive
```
```
> Analyze the files in this directory
> Create a summary report
> Show me the largest files
> exit
```

## 📋 Test Checklist

Before deploying, verify:

- [ ] Demo test runs successfully
- [ ] Interactive mode works
- [ ] Web interface loads
- [ ] File operations execute
- [ ] Security validation blocks dangerous commands
- [ ] Timeout protection works
- [ ] Docker container builds and runs
- [ ] No Python import errors
- [ ] Configuration loads properly
- [ ] Tool execution completes

## 🐛 Common Test Issues

### Issue: "Module not found"
**Solution:**
```bash
pip3 install --user [missing-module]
```

### Issue: "Permission denied"
**Solution:**
```bash
chmod 755 data/
mkdir -p data
```

### Issue: "Configuration error"
**Solution:**
```bash
echo "LLM__PROVIDER=mock" > .env
```

### Issue: Agent hangs
**Solution:**
- Check timeout settings
- Verify no infinite loops
- Use Ctrl+C to interrupt

### Issue: Docker build fails
**Solution:**
```bash
docker system prune -f
docker build --no-cache -t nexus-agent .
```

## 📊 Success Metrics

A successful test should show:
- ✅ Agent initializes without errors
- ✅ Tools execute and return results
- ✅ Security validation works
- ✅ Reasoning responses are contextual
- ✅ No infinite loops or hangs
- ✅ Graceful error handling
- ✅ Memory usage stays reasonable (<500MB)
- ✅ Response time under 30 seconds

## 🎯 Next Steps

After successful testing:
1. Read `HOW_TO_DEPLOY.md` for deployment instructions
2. Read `HOW_TO_CLI.md` for CLI usage guide
3. Check `TROUBLESHOOTING.md` for common issues
4. Explore advanced configuration options

---

**Need help?** Check the documentation in `docs/` or review `CRITICAL_INFO.md` for troubleshooting information.