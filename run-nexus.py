#!/usr/bin/env python3
"""
Simple Nexus Agent Runner - bypasses complex configuration.
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def setup_environment():
    """Set up minimal environment for testing."""
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    os.environ.update({
        'MANUS_WORKING_DIR': str(data_dir),
        'LLM__PROVIDER': 'mock',
        'AGENT__NAME': 'nexus-agent',
        'DEBUG_MODE': 'true',
        'PYTHONUNBUFFERED': '1'
    })

async def run_single_task(task_text):
    """Run a single task."""
    from manus.core.llm_providers import MockProvider
    from manus.core.config import LLMConfig, SecurityConfig
    from manus.tools.registry import ToolRegistry
    from manus.security.validator import SecurityValidator
    
    # Create components
    llm_config = LLMConfig(provider="mock", model="mock-model")
    security_config = SecurityConfig()
    security_validator = SecurityValidator(security_config)
    tool_registry = ToolRegistry(security_validator)
    llm_provider = MockProvider(llm_config)
    
    print(f"🎯 Task: {task_text}")
    print("="*60)
    
    # Get LLM response
    messages = [{"role": "user", "content": task_text}]
    response = await llm_provider.generate_response(messages)
    
    print("🤖 Agent Response:")
    print(response['text_content'])
    
    # Execute tool calls
    if response['tool_calls']:
        print(f"\n🔧 Executing {len(response['tool_calls'])} tool(s):")
        for i, tool_call in enumerate(response['tool_calls'], 1):
            print(f"\n  {i}. {tool_call['name']}({tool_call['input']})")
            try:
                result = await tool_registry.execute_tool(
                    tool_call['name'], 
                    tool_call['input']
                )
                print(f"     ✅ Result: {str(result)[:100]}...")
            except Exception as e:
                print(f"     ❌ Error: {e}")
    else:
        print("\n📝 No tools executed (conversation only)")
    
    print("="*60)

async def run_interactive():
    """Run interactive mode."""
    from manus.core.llm_providers import MockProvider
    from manus.core.config import LLMConfig, SecurityConfig
    from manus.tools.registry import ToolRegistry
    from manus.security.validator import SecurityValidator
    
    # Create components
    llm_config = LLMConfig(provider="mock", model="mock-model")
    security_config = SecurityConfig()
    security_validator = SecurityValidator(security_config)
    tool_registry = ToolRegistry(security_validator)
    llm_provider = MockProvider(llm_config)
    
    print("🤖 Nexus Agent Interactive Mode")
    print("Available tools:", len(tool_registry.list_tools()))
    print("Type 'quit' or 'exit' to end session")
    print("="*60)
    
    while True:
        try:
            user_input = input("\n> ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            if not user_input:
                continue
                
            await run_single_task(user_input)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except EOFError:
            break

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Nexus Agent Test Runner")
    parser.add_argument("--task", "-t", help="Run a single task")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--test", action="store_true", help="Run demo tests")
    
    args = parser.parse_args()
    
    setup_environment()
    
    if args.task:
        asyncio.run(run_single_task(args.task))
    elif args.interactive:
        asyncio.run(run_interactive())
    elif args.test:
        # Run demo tests
        test_tasks = [
            "Hello! Please introduce yourself",
            "List available tools",
            "What can you help me with?"
        ]
        async def run_tests():
            for task in test_tasks:
                await run_single_task(task)
                print()
        asyncio.run(run_tests())
    else:
        print("Nexus Agent Test Runner")
        print("Usage:")
        print("  python3 run-nexus.py --task 'Hello world'")
        print("  python3 run-nexus.py --interactive")
        print("  python3 run-nexus.py --test")

if __name__ == "__main__":
    main()