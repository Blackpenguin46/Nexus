# 🚨 IMPORTANT: Setup Required for Git Clone Users

If you just cloned this repository, **you MUST follow these steps** to run the agent locally:

## Quick Setup (Copy & Paste)

```bash
# 1. Install dependencies
pip3 install --user pydantic pydantic-settings python-dotenv rich fastapi uvicorn aiohttp selenium webdriver-manager PyYAML cryptography validators structlog psutil json5 aiofiles

# 2. Test the agent (no additional setup needed)
python3 run-nexus.py --test
```

## What's Different

This repository includes **critical fixes** for local development:

- ✅ **No terminal freezing** - Added comprehensive timeout protection
- ✅ **No PyTorch requirement** - Use mock provider for testing  
- ✅ **Local file paths** - Works outside Docker containers
- ✅ **Simple test runner** - `run-nexus.py` bypasses complex configuration

## Files to Read

1. **`SETUP.md`** - Complete setup instructions
2. **`TESTING.md`** - Testing guide and troubleshooting
3. **`CHANGES.md`** - Technical details of fixes applied
4. **`project_overview.md`** - Project architecture and goals

## Quick Commands

```bash
# Demo test (recommended first)
python3 run-nexus.py --test

# Interactive chat
python3 run-nexus.py --interactive  

# Single task
python3 run-nexus.py --task "Create a hello world script"

# Docker web interface (if Docker installed)
./run-test.sh web  # Visit http://localhost:8080
```

## If You Get Errors

1. **"Module not found"** - Install dependencies with pip command above
2. **"Configuration Error"** - Ensure `.env` has `LLM__PROVIDER=mock`
3. **"Permission denied"** - Run `mkdir -p data && chmod 755 data`

## Need Help?

Check the documentation files or look at the debugging log in `docs/activity.md` for detailed technical information about the fixes that were applied.

**The agent is ready to use immediately after cloning - no complex setup required!**