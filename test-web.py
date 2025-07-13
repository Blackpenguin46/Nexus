#!/usr/bin/env python3
"""
Web server test for Nexus Agent.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_web_server():
    """Test the web server functionality."""
    try:
        print("🌐 Testing Nexus Agent Web Server...")
        
        # Create local data directory
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Set environment for local testing
        os.environ.update({
            'MANUS_WORKING_DIR': str(data_dir),
            'LLM__PROVIDER': 'mock',
            'AGENT__NAME': 'test-agent',
            'DEBUG_MODE': 'true'
        })
        
        # Import web components
        from manus.api.server import create_app
        from manus.core.config import Config, LLMConfig, SecurityConfig, AgentConfig
        import uvicorn
        
        print("✅ Web imports successful")
        
        # Create simple config
        config = Config(
            llm=LLMConfig(provider="mock", model="mock-model"),
            security=SecurityConfig(),
            agent=AgentConfig(name="test-agent"),
            debug_mode=True
        )
        
        # Create FastAPI app
        app = create_app(config)
        
        print("✅ FastAPI app created")
        
        # Test the app creation (we can't easily run the server in a test)
        print("📊 App routes:")
        for route in app.routes:
            print(f"  • {route.path} ({route.methods if hasattr(route, 'methods') else 'N/A'})")
        
        print("\n🌐 To run the web server manually:")
        print("python3 -c \"")
        print("import sys, os; sys.path.insert(0, '.'); os.environ.update({'LLM__PROVIDER': 'mock', 'MANUS_WORKING_DIR': './data'}); ")
        print("from manus.cli import main; main()\" --web --host 0.0.0.0 --port 8000 --debug")
        print("\nOr use: python3 -m manus.cli --web --host 0.0.0.0 --port 8000 --debug")
        print("Then visit: http://localhost:8000")
        
        print("\n✅ Web server test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_web_server())
    sys.exit(0 if success else 1)