"""
Manus Remake: Autonomous AI Agent with Claude Integration

A production-ready autonomous agent inspired by ManusAI, featuring:
- ReAct + CodeAct hybrid architecture
- Zero-trust security with container sandboxing
- Claude 3.5 Sonnet integration with computer use
- Hierarchical error recovery
- Production monitoring and observability

Author: Sam Oakes
Version: 0.1.0
"""

__version__ = "0.1.0"
__author__ = "Sam Oakes"
__email__ = "samoakes@example.com"

# Core imports for public API
from .core.agent import ManusAgent
from .core.config import Config
from .core.exceptions import ManusError, SecurityError, ToolError

__all__ = [
    "ManusAgent",
    "Config", 
    "ManusError",
    "SecurityError",
    "ToolError",
    "__version__",
    "__author__",
]