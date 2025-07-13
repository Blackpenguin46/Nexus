# Manus Remake - FREE Autonomous AI Agent 🆓

A **completely free** autonomous AI agent that runs locally on your Mac M2 using Hugging Face models. No API costs, no usage limits, no credit cards required!

## 🌟 Why This Version is Perfect for You

- **💯 100% FREE**: No API costs, no subscriptions, no hidden fees
- **🔒 PRIVATE**: Everything runs locally on your Mac - your data never leaves your machine
- **⚡ OPTIMIZED**: Specially optimized for Apple Silicon M2 with Metal Performance Shaders
- **🚀 AUTONOMOUS**: Full agent capabilities including reasoning, planning, and tool use
- **📱 NO LIMITS**: Use it as much as you want without worrying about costs

## 🏗️ What You Get

### Core Features
- **Local LLM**: Runs Hugging Face models optimized for M2 Macs
- **Autonomous Operation**: Multi-step reasoning and task execution
- **File Operations**: Read, write, edit files securely
- **Shell Commands**: Execute terminal commands safely
- **Web Browsing**: Browser automation (coming soon)
- **Multiple Interfaces**: CLI and web interface

### Recommended Models (All Free!)

#### 🏃‍♂️ Fast & Lightweight (< 500MB)
- `microsoft/DialoGPT-small` - 117MB, very fast, good for basic tasks
- `microsoft/CodeGPT-small-py` - 124MB, optimized for Python coding
- `Salesforce/codet5-small` - 60MB, excellent for code generation

#### ⚖️ Balanced (500MB - 1GB)
- `microsoft/DialoGPT-medium` - 355MB, good balance of speed and capability
- `facebook/blenderbot-400M-distill` - 400MB, great for conversations

#### 🧠 More Capable (1GB+)
- `microsoft/DialoGPT-large` - 762MB, better reasoning and complex tasks
- `facebook/blenderbot-1B-distill` - 1GB, most capable free option

## 🚀 Quick Start (5 Minutes!)

### 1. Prerequisites
- Mac with M2 chip (optimized for Metal Performance Shaders)
- Python 3.11+ 
- Docker Desktop
- 2-8GB free space (depending on model choice)

### 2. Clone and Setup
```bash
git clone <repository-url>
cd Manus-remake
cp .env.template .env
```

### 3. Configure for FREE Usage
Edit your `.env` file:
```bash
# Use the free Hugging Face provider
LLM__PROVIDER=huggingface
LLM__MODEL=microsoft/DialoGPT-medium
LLM__DEVICE=mps
LLM__LOAD_IN_4BIT=true

# No API key needed!
```

### 4. Build and Run
```bash
# Build the container
docker build -t manus-free .

# Run interactively
docker run -it --rm -v $(pwd)/data:/app/data --env-file .env manus-free
```

That's it! Your free autonomous agent is running! 🎉

## 🎯 Usage Examples

### Interactive Mode
```bash
docker run -it --rm -v $(pwd)/data:/app/data --env-file .env manus-free

# Try these tasks:
> "Create a Python script to calculate fibonacci numbers"
> "Analyze the files in my current directory"
> "Write a summary of a text file"
> "Help me organize my project structure"
```

### Single Task Mode
```bash
# Execute one task and exit
docker run --rm -v $(pwd)/data:/app/data --env-file .env manus-free \
  --task "Create a todo list app in Python"
```

### Web Interface
```bash
# Start web server
docker run -p 8000:8000 --rm -v $(pwd)/data:/app/data --env-file .env manus-free --web

# Open http://localhost:8000 in your browser
```

## ⚙️ Model Selection Guide

Choose your model based on your needs:

### For Speed (Recommended for starting)
```bash
LLM__MODEL=microsoft/DialoGPT-small    # 117MB, very fast
```

### For Coding Tasks
```bash
LLM__MODEL=microsoft/CodeGPT-small-py  # 124MB, great for Python
LLM__MODEL=Salesforce/codet5-small     # 60MB, general coding
```

### For Better Conversations
```bash
LLM__MODEL=microsoft/DialoGPT-medium   # 355MB, balanced
LLM__MODEL=facebook/blenderbot-400M-distill  # 400MB, conversational
```

### For Complex Reasoning
```bash
LLM__MODEL=microsoft/DialoGPT-large    # 762MB, most capable
```

## 🔧 Performance Optimization

### Memory Settings for M2 Mac
```bash
# For 8GB Mac
LLM__LOAD_IN_4BIT=true
LLM__MAX_TOKENS=512

# For 16GB+ Mac
LLM__LOAD_IN_4BIT=false
LLM__MAX_TOKENS=1024
```

### Speed vs Quality Trade-offs
```bash
# Faster responses
LLM__TEMPERATURE=0.0
LLM__MAX_TOKENS=512

# More creative responses
LLM__TEMPERATURE=0.3
LLM__MAX_TOKENS=1024
```

## 🆚 Free vs Paid Comparison

| Feature | Free Version | Claude API Version |
|---------|-------------|-------------------|
| **Cost** | 🆓 $0 forever | 💰 $$ per request |
| **Speed** | ⚡ Fast (local) | 🌐 Network dependent |
| **Privacy** | 🔒 100% local | ☁️ Sent to Anthropic |
| **Limits** | ♾️ Unlimited | 📊 Rate limited |
| **Quality** | 👍 Good | 🌟 Excellent |
| **Setup** | 🔧 5 minutes | 💳 Need API key |

## 🛠️ Advanced Configuration

### Model Comparison on M2 Mac
| Model | Size | Speed | Quality | Best For |
|-------|------|--------|---------|----------|
| DialoGPT-small | 117MB | ⚡⚡⚡ | ⭐⭐ | Quick tasks |
| CodeGPT-small | 124MB | ⚡⚡⚡ | ⭐⭐⭐ | Programming |
| DialoGPT-medium | 355MB | ⚡⚡ | ⭐⭐⭐ | General use |
| BlenderBot-400M | 400MB | ⚡⚡ | ⭐⭐⭐⭐ | Conversations |
| DialoGPT-large | 762MB | ⚡ | ⭐⭐⭐⭐ | Complex tasks |

### Custom Model Configuration
```bash
# Try any Hugging Face model!
LLM__MODEL=microsoft/DialoGPT-large
LLM__MODEL=facebook/blenderbot-1B-distill
LLM__MODEL=microsoft/CodeGPT-small-py

# Experimental models (advanced users)
LLM__TRUST_REMOTE_CODE=true
LLM__MODEL=some-custom-model
```

## 🔍 Troubleshooting

### Common Issues

**Model too slow?**
```bash
# Use a smaller model
LLM__MODEL=microsoft/DialoGPT-small
LLM__LOAD_IN_4BIT=true
```

**Out of memory?**
```bash
# Enable aggressive memory optimization
LLM__LOAD_IN_4BIT=true
LLM__ENABLE_ATTENTION_SLICING=true
LLM__MAX_TOKENS=256
```

**Want better quality?**
```bash
# Use a larger model (requires more RAM)
LLM__MODEL=microsoft/DialoGPT-large
LLM__LOAD_IN_4BIT=false
```

### Performance Tips

1. **First run will be slower** - models download and cache locally
2. **Subsequent runs are fast** - models are cached on disk
3. **RAM usage scales with model size** - monitor with Activity Monitor
4. **Use 4-bit quantization** for memory savings on smaller Macs

## 🎯 What Can It Do?

### File Operations
- Read and analyze text files
- Create and edit Python scripts
- Organize directory structures
- Process CSV and JSON data

### Coding Tasks
- Generate Python, JavaScript, HTML code
- Debug and fix code issues
- Explain complex algorithms
- Create documentation

### System Tasks
- Execute shell commands safely
- Install packages and dependencies
- Monitor system resources
- Automate routine tasks

### Analysis & Research
- Summarize documents
- Extract information from files
- Compare and contrast data
- Generate reports

## 🔮 Future Enhancements

Coming soon to the free version:
- 🌐 **Browser Automation**: Web scraping and form filling
- 🔍 **Local Search**: Search without external APIs
- 🎨 **Image Processing**: Basic image manipulation
- 📊 **Data Analysis**: CSV/JSON analysis and visualization
- 🧩 **Plugin System**: Add your own custom tools

## 💡 Tips for Best Results

1. **Start with DialoGPT-medium** - good balance of speed and quality
2. **Be specific in your requests** - "Create a Python function that..." vs "Help with Python"
3. **Break complex tasks into steps** - the agent works better with clear goals
4. **Use the web interface** for better interaction monitoring
5. **Monitor memory usage** - switch to smaller models if needed

## 🤝 Community & Support

- **Issues**: Report bugs and request features
- **Discussions**: Share your use cases and tips
- **Contributions**: Help improve the free version
- **Model Testing**: Try new models and share results

---

**🎉 Enjoy your completely FREE autonomous AI agent! No limits, no costs, just pure AI power running locally on your Mac M2!**