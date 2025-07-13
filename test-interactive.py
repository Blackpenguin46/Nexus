#!/usr/bin/env python3
"""
Interactive test for Nexus Agent with tool execution.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_interactive():
    """Test with tool execution."""
    try:
        print("🚀 Testing Nexus Agent with tool execution...")
        
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
        
        print("✅ Core imports successful")
        
        # Create minimal configs
        llm_config = LLMConfig(provider="mock", model="mock-model")
        security_config = SecurityConfig()
        
        # Create components
        security_validator = SecurityValidator(security_config)
        tool_registry = ToolRegistry(security_validator)
        llm_provider = MockProvider(llm_config)
        
        print("✅ Components created")
        
        # Test different message types that should trigger tools
        test_scenarios = [
            {
                "name": "Directory Listing",
                "message": "Please list the files in the current directory"
            },
            {
                "name": "System Information", 
                "message": "Can you check the system information?"
            },
            {
                "name": "File Creation",
                "message": "Create a Python hello world script"
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n🎯 Testing scenario: {scenario['name']}")
            print(f"Message: {scenario['message']}")
            
            messages = [{"role": "user", "content": scenario['message']}]
            response = await llm_provider.generate_response(messages)
            
            print(f"Response: {response['text_content'][:100]}...")
            print(f"Tool calls: {len(response['tool_calls'])}")
            
            # Execute any tool calls
            for i, tool_call in enumerate(response['tool_calls']):
                print(f"\n🔧 Executing tool {i+1}: {tool_call['name']}")
                print(f"Arguments: {tool_call['input']}")
                
                try:
                    result = await tool_registry.execute_tool(
                        tool_call['name'], 
                        tool_call['input']
                    )
                    print(f"✅ Tool result: {str(result)[:150]}...")
                except Exception as e:
                    print(f"❌ Tool error: {e}")
            
            print("-" * 50)
        
        # Test available tools
        print(f"\n📚 Available tools: {len(tool_registry.list_tools())}")
        for tool_name in sorted(tool_registry.list_tools()):
            print(f"  • {tool_name}")
        
        print("\n✅ Interactive test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_interactive())
    sys.exit(0 if success else 1)