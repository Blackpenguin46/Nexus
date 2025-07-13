# ⚡ Quick Start Guide

Get your Nexus autonomous agent running in under 5 minutes!

## 🚀 30-Second Setup

Copy and paste these commands:

```bash
# 1. Install dependencies
pip3 install --user pydantic pydantic-settings python-dotenv rich fastapi uvicorn aiohttp selenium webdriver-manager PyYAML cryptography validators structlog psutil json5 aiofiles

# 2. Set up environment
echo "LLM__PROVIDER=mock" > .env && mkdir -p data

# 3. Test the agent
python3 run-nexus.py --test
```

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

**✅ If you see this, you're ready to go!**

## 🎯 Try These Commands

### Basic Usage
```bash
# Interactive chat mode
python3 run-nexus.py --interactive

# Single task
python3 run-nexus.py --task "Create a hello world Python script"

# Web interface
python3 run-nexus.py --web
# Then visit: http://localhost:8080
```

### Example Tasks
```bash
# File operations
python3 run-nexus.py --task "List all files in this directory"
python3 run-nexus.py --task "Create a README.md file"

# System information
python3 run-nexus.py --task "What's the current date and system info?"

# Development tasks
python3 run-nexus.py --task "Create a Python project structure"
```

## 💬 Interactive Mode Example

```bash
python3 run-nexus.py --interactive
```

Try this conversation:
```
Manus> hello
🤖 Agent: Let me check our current environment...

Manus> create a python script
🤖 Agent: I'll create a Python script template for you...

Manus> list files
🤖 Agent: I'll list the files in the current directory...

Manus> exit
👋 Goodbye!
```

## 🐳 Docker Quick Start

```bash
# Build and run
docker build -t nexus-agent .
docker run --rm -it nexus-agent python3 run-nexus.py --test

# Web interface
docker run --rm -p 8080:8080 nexus-agent python3 run-nexus.py --web
```

## 🔧 Common Issues

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | Run: `pip3 install --user -r requirements.txt` |
| `Permission denied` | Run: `chmod 755 data && mkdir -p data` |
| `Configuration error` | Run: `echo "LLM__PROVIDER=mock" > .env` |
| Agent hangs | Press `Ctrl+C` or run: `timeout 30s python3 run-nexus.py --test` |

## 📚 What's Next?

1. **Learn CLI**: Read `HOW_TO_CLI.md` for all command options
2. **Deploy**: See `HOW_TO_DEPLOY.md` for production setup  
3. **Test**: Check `HOW_TO_TEST.md` for comprehensive testing
4. **Troubleshoot**: Review `TROUBLESHOOTING.md` if you have issues

## 🎮 Fun Things to Try

### Creative Tasks
```bash
python3 run-nexus.py --task "Write a poem about autonomous AI agents"
python3 run-nexus.py --task "Create a story about a helpful robot"
```

### Technical Tasks
```bash
python3 run-nexus.py --task "Analyze this codebase and create documentation"
python3 run-nexus.py --task "Create a Flask web application structure"
```

### System Tasks
```bash
python3 run-nexus.py --task "Generate a system health report"
python3 run-nexus.py --task "Create a backup script for important files"
```

---

**🎉 You're all set!** Your Nexus agent is now ready for autonomous task execution with sophisticated Manus-level reasoning, running completely locally without any API costs!