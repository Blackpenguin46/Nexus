#!/usr/bin/env python3
"""
Simple test script for Nexus Agent without complex configuration.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set minimal environment variables
os.environ.update({
    'LLM__PROVIDER': 'mock',
    'LLM__MODEL': 'mock-model',
    'AGENT__NAME': 'test-agent',
    'AGENT__MAX_ITERATIONS': '10',
    'AGENT__TIMEOUT_SECONDS': '60',
    'DEBUG_MODE': 'true',
    'PYTHONUNBUFFERED': '1'
})

async def test_agent():
    """Test the agent with a simple task."""
    try:
        print("🚀 Testing Nexus Agent...")
        
        # Import after setting environment
        from manus.core.agent import ManusAgent
        from manus.core.config import Config
        
        print("✅ Import successful")
        
        # Create config with defaults
        config = Config.from_env()
        print("✅ Configuration loaded")
        
        # Create agent
        async with ManusAgent(config) as agent:
            print("✅ Agent created")
            
            # Test task
            task = "Hello! Please introduce yourself and show me what you can do."
            print(f"🎯 Running task: {task}")
            
            result = await agent.execute_task(task)
            
            print("\n" + "="*50)
            print("📊 RESULT:")
            print("="*50)
            print(f"Success: {result['success']}")
            print(f"Response: {result['result']}")
            print(f"Time: {result['execution_time']:.2f}s")
            print(f"Iterations: {result['iterations']}")
            print("="*50)
            
            return result['success']
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_agent())
    sys.exit(0 if success else 1)