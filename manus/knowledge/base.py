"""
Enhanced Knowledge Base for Nexus Agent
Provides contextual information and reasoning patterns
"""

import time
from typing import Dict, List, Any, Optional
from pathlib import Path

class KnowledgeBase:
    """
    Enhanced knowledge base with contextual reasoning patterns and responses.
    """
    
    def __init__(self):
        self.patterns = self._initialize_patterns()
        self.responses = self._initialize_responses()
        self.tools_knowledge = self._initialize_tools_knowledge()
        
    def _initialize_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize sophisticated reasoning patterns."""
        return {
            "datetime_patterns": {
                "keywords": ["date", "time", "today", "now", "current", "when", "day", "month", "year"],
                "response_style": "direct_information",
                "tool_preference": "shell_exec",
                "command_template": "date",
                "context": "temporal_information"
            },
            
            "system_info_patterns": {
                "keywords": ["system", "computer", "machine", "os", "operating", "info", "details", "specs"],
                "response_style": "comprehensive_analysis",
                "tool_preference": "shell_exec",
                "command_template": "uname -a && echo '---' && sw_vers 2>/dev/null || lsb_release -a 2>/dev/null",
                "context": "system_analysis"
            },
            
            "file_exploration_patterns": {
                "keywords": ["list", "show", "files", "directory", "folder", "contents", "ls", "dir"],
                "response_style": "structured_listing",
                "tool_preference": "file_list",
                "command_template": {"directory": "."},
                "context": "file_system_exploration"
            },
            
            "development_patterns": {
                "keywords": ["create", "script", "code", "program", "python", "development", "build"],
                "response_style": "structured_creation",
                "tool_preference": "file_write",
                "command_template": None,  # Dynamic based on request
                "context": "software_development"
            },
            
            "analysis_patterns": {
                "keywords": ["analyze", "examine", "investigate", "review", "assess", "study"],
                "response_style": "methodical_analysis",
                "tool_preference": "file_list",
                "command_template": {"directory": "."},
                "context": "analytical_task"
            }
        }
    
    def _initialize_responses(self) -> Dict[str, Dict[str, str]]:
        """Initialize contextual response templates."""
        return {
            "temporal_information": {
                "intro": "I'll check the current date and time information for you.",
                "processing": "Retrieving temporal data...",
                "success": "Here's the current date and time information:",
                "context_note": "This information is from the system clock."
            },
            
            "system_analysis": {
                "intro": "I'll gather comprehensive system information for you.",
                "processing": "Analyzing system configuration...",
                "success": "Here's your system analysis:",
                "context_note": "This includes OS details, hardware info, and system status."
            },
            
            "file_system_exploration": {
                "intro": "I'll explore the file system structure for you.",
                "processing": "Scanning directory contents...",
                "success": "Here's what I found in the directory:",
                "context_note": "Showing files and folders with metadata."
            },
            
            "software_development": {
                "intro": "I'll help you with this development task.",
                "processing": "Creating development artifacts...",
                "success": "Development task completed:",
                "context_note": "Following best practices and conventions."
            },
            
            "analytical_task": {
                "intro": "I'll perform a systematic analysis for you.",
                "processing": "Conducting thorough examination...",
                "success": "Analysis complete:",
                "context_note": "Based on available data and patterns."
            }
        }
    
    def _initialize_tools_knowledge(self) -> Dict[str, Dict[str, Any]]:
        """Initialize tool-specific knowledge and best practices."""
        return {
            "file_list": {
                "purpose": "Directory and file exploration",
                "best_practices": ["Always specify directory parameter", "Use '.' for current directory"],
                "common_patterns": [".", "..", "/specific/path"],
                "output_interpretation": "Returns structured file metadata"
            },
            
            "shell_exec": {
                "purpose": "System command execution",
                "best_practices": ["Use safe commands only", "Include error handling"],
                "common_patterns": ["date", "uname -a", "ps aux", "df -h"],
                "output_interpretation": "Returns command output and execution status"
            },
            
            "file_write": {
                "purpose": "File creation and content writing",
                "best_practices": ["Use descriptive filenames", "Include proper headers"],
                "common_patterns": ["script.py", "README.md", "config.json"],
                "output_interpretation": "Returns success status and file details"
            },
            
            "file_read": {
                "purpose": "File content retrieval",
                "best_practices": ["Check file existence first", "Handle encoding issues"],
                "common_patterns": ["config files", "documentation", "code files"],
                "output_interpretation": "Returns file content and metadata"
            }
        }
    
    def get_contextual_response(self, intent: str, user_message: str) -> Dict[str, str]:
        """Get contextual response templates based on intent."""
        
        # Map intents to response contexts
        intent_context_map = {
            "datetime_query": "temporal_information",
            "system_query": "system_analysis", 
            "exploration": "file_system_exploration",
            "file_manipulation": "software_development",
            "development": "software_development",
            "analysis": "analytical_task",
            "greeting": "system_analysis"  # Default to system check for greetings
        }
        
        context = intent_context_map.get(intent, "analytical_task")
        return self.responses.get(context, self.responses["analytical_task"])
    
    def get_enhanced_explanation(self, intent: str, tool: str, user_message: str) -> str:
        """Generate enhanced explanations based on context."""
        
        context_explanations = {
            "datetime_query": {
                "shell_exec": f"I'll retrieve the current system date and time. This gives you precise temporal information including timezone details.",
                "default": "I'll get the current date and time for you."
            },
            
            "system_query": {
                "shell_exec": f"I'll gather comprehensive system information including OS version, kernel details, and hardware architecture. This provides a complete system profile.",
                "default": "I'll collect detailed system information for you."
            },
            
            "exploration": {
                "file_list": f"I'll scan the directory structure to show you all files and folders, including metadata like file sizes, types, and permissions.",
                "shell_exec": f"I'll use system commands to provide a detailed directory listing with extended information.",
                "default": "I'll explore the file system for you."
            },
            
            "file_manipulation": {
                "file_write": f"I'll create a new file based on your specifications. I'll ensure proper formatting, structure, and best practices.",
                "default": "I'll handle this file operation for you."
            },
            
            "development": {
                "file_write": f"I'll create development artifacts following best practices. This includes proper structure, documentation, and maintainable code.",
                "shell_exec": f"I'll execute development-related commands to set up your environment or build process.",
                "default": "I'll assist with this development task."
            }
        }
        
        intent_explanations = context_explanations.get(intent, {})
        return intent_explanations.get(tool, intent_explanations.get("default", "I'll help you with this task."))
    
    def get_tool_parameters(self, intent: str, tool: str, user_message: str) -> Dict[str, Any]:
        """Generate intelligent tool parameters based on context."""
        
        if tool == "file_list":
            # Intelligent directory inference
            message_lower = user_message.lower()
            if "parent" in message_lower or ".." in message_lower:
                return {"directory": ".."}
            elif "current" in message_lower or "this" in message_lower or "here" in message_lower:
                return {"directory": "."}
            else:
                return {"directory": "."}
        
        elif tool == "shell_exec":
            # Context-aware command selection
            if intent == "datetime_query":
                return {"command": "date"}
            elif intent == "system_query":
                return {"command": "uname -a && echo '---' && sw_vers 2>/dev/null || lsb_release -a 2>/dev/null || cat /etc/os-release 2>/dev/null"}
            elif "memory" in user_message.lower():
                return {"command": "free -h 2>/dev/null || vm_stat | head -10"}
            elif "disk" in user_message.lower() or "space" in user_message.lower():
                return {"command": "df -h ."}
            elif "process" in user_message.lower():
                return {"command": "ps aux | head -10"}
            else:
                return {"command": "pwd && ls -la"}
        
        elif tool == "file_write":
            # Intelligent file creation parameters
            message_lower = user_message.lower()
            
            if "python" in message_lower or "script" in message_lower:
                return {
                    "path": "script.py",
                    "content": self._generate_python_template(user_message)
                }
            elif "readme" in message_lower or "documentation" in message_lower:
                return {
                    "path": "README.md", 
                    "content": self._generate_readme_template(user_message)
                }
            elif "config" in message_lower:
                return {
                    "path": "config.json",
                    "content": self._generate_config_template(user_message)
                }
            else:
                return {
                    "path": "note.txt",
                    "content": self._generate_note_template(user_message)
                }
        
        return {}
    
    def _generate_python_template(self, user_message: str) -> str:
        """Generate Python script template based on user request."""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        if "web" in user_message.lower() or "flask" in user_message.lower():
            return f'''#!/usr/bin/env python3
"""
Web Application Script
Created: {timestamp}
Request: {user_message}
"""

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/hello')
def api_hello():
    return jsonify({{"message": "Hello from Nexus Agent!", "timestamp": "{timestamp}"}})

def main():
    print("Starting web application...")
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main()
'''
        
        elif "data" in user_message.lower() or "csv" in user_message.lower():
            return f'''#!/usr/bin/env python3
"""
Data Processing Script
Created: {timestamp}
Request: {user_message}
"""

import pandas as pd
import numpy as np
from pathlib import Path

def process_data(input_file):
    """Process data from input file."""
    try:
        # Read data
        df = pd.read_csv(input_file)
        print(f"Loaded {{len(df)}} rows from {{input_file}}")
        
        # Basic analysis
        print("\\nData Summary:")
        print(df.describe())
        
        # Process and save
        output_file = input_file.replace('.csv', '_processed.csv')
        df.to_csv(output_file, index=False)
        print(f"\\nProcessed data saved to {{output_file}}")
        
    except Exception as e:
        print(f"Error processing data: {{e}}")

def main():
    print("Data Processing Script - Created by Nexus Agent")
    print(f"Request: {user_message}")
    
    # Example usage
    # process_data('input.csv')

if __name__ == "__main__":
    main()
'''
        
        else:
            return f'''#!/usr/bin/env python3
"""
Python Script
Created: {timestamp}
Request: {user_message}
"""

def main():
    """Main function - Entry point of the script."""
    print("Hello from Nexus Agent!")
    print(f"Script created: {timestamp}")
    print(f"Based on request: {user_message}")
    
    # TODO: Add your code here
    pass

def helper_function():
    """Helper function - Add your logic here."""
    pass

if __name__ == "__main__":
    main()
'''
    
    def _generate_readme_template(self, user_message: str) -> str:
        """Generate README template based on user request."""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        return f'''# Project Documentation

## Overview
This documentation was created by Nexus Agent on {timestamp}.

**Original Request:** {user_message}

## Description
Add your project description here. Explain what this project does and why it's useful.

## Features
- Feature 1: Add your main features
- Feature 2: List key capabilities
- Feature 3: Highlight unique aspects

## Installation
```bash
# Add installation instructions
git clone <repository-url>
cd <project-directory>
pip install -r requirements.txt
```

## Usage
```bash
# Add usage examples
python main.py
```

## Configuration
Describe any configuration files or environment variables needed.

## Development
Instructions for developers who want to contribute.

## Testing
```bash
# Add testing instructions
python -m pytest tests/
```

## License
Add license information here.

## Contributing
Guidelines for contributing to this project.

---
*Generated by Nexus Agent - Autonomous AI Assistant*
'''
    
    def _generate_config_template(self, user_message: str) -> str:
        """Generate configuration template."""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        return f'''{{
  "metadata": {{
    "created": "{timestamp}",
    "created_by": "Nexus Agent",
    "request": "{user_message}"
  }},
  "application": {{
    "name": "My Application",
    "version": "1.0.0",
    "debug": true
  }},
  "database": {{
    "host": "localhost",
    "port": 5432,
    "name": "myapp_db",
    "username": "user",
    "password": "change_me"
  }},
  "api": {{
    "base_url": "http://localhost:8080",
    "timeout": 30,
    "retry_attempts": 3
  }},
  "logging": {{
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "app.log"
  }}
}}
'''
    
    def _generate_note_template(self, user_message: str) -> str:
        """Generate note template."""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        return f'''Note Created by Nexus Agent

Date: {timestamp}
Request: {user_message}

This file demonstrates autonomous file creation capabilities.

Key Information:
- Agent: Nexus Autonomous AI Assistant
- Reasoning Engine: ReAct + CodeAct Hybrid
- Features: 21+ tools, security validation, local operation
- Capabilities: File ops, system interaction, development tasks

Task Context:
Your request was processed through sophisticated reasoning patterns
that analyzed intent, classified task type, and selected appropriate
tools for execution.

Next Steps:
- Modify this content as needed
- Use this as a template for future notes  
- Explore more agent capabilities

---
Generated autonomously without API costs!
'''

# Global knowledge base instance
knowledge_base = KnowledgeBase()