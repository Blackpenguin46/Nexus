#!/usr/bin/env python3
"""
Minimal test for Nexus Agent bypassing complex configuration.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_minimal():
    """Test with minimal configuration."""
    try:
        print("🚀 Testing Nexus Agent with minimal setup...")
        
        # Create local data directory
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Set environment for local testing
        os.environ['MANUS_WORKING_DIR'] = str(data_dir)
        
        # Import core components
        from manus.core.llm_providers import MockProvider
        from manus.core.config import LLMConfig, SecurityConfig
        from manus.tools.registry import ToolRegistry
        from manus.security.validator import SecurityValidator
        from manus.core.state import AgentState
        
        print("✅ Core imports successful")
        
        # Create minimal configs
        llm_config = LLMConfig(provider="mock", model="mock-model")
        security_config = SecurityConfig()
        
        # Create components
        security_validator = SecurityValidator(security_config)
        tool_registry = ToolRegistry(security_validator)
        llm_provider = MockProvider(llm_config)
        
        print("✅ Components created")
        
        # Test LLM provider
        messages = [{"role": "user", "content": "Hello! Please introduce yourself."}]
        response = await llm_provider.generate_response(messages)
        
        print("\n" + "="*50)
        print("📊 LLM RESPONSE TEST:")
        print("="*50)
        print(f"Text: {response['text_content'][:200]}...")
        print(f"Tool calls: {len(response['tool_calls'])}")
        print(f"Complete: {response['is_complete']}")
        
        # Test tool if there are tool calls
        if response['tool_calls']:
            tool_call = response['tool_calls'][0]
            print(f"\n🔧 Testing tool: {tool_call['name']}")
            
            try:
                result = await tool_registry.execute_tool(
                    tool_call['name'], 
                    tool_call['input']
                )
                print(f"Tool result: {str(result)[:100]}...")
            except Exception as e:
                print(f"Tool execution: {e}")
        
        print("="*50)
        print("✅ Minimal test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_minimal())
    sys.exit(0 if success else 1)