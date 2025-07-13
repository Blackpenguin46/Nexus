"""
Main Manus Agent class - orchestrates all components for autonomous task execution.

This is the primary interface for the Manus agent system, combining the agent loop,
tool registry, security validation, and state management into a cohesive autonomous
AI agent capable of complex task execution.
"""

import asyncio
import os
import signal
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..security.validator import SecurityValidator
from ..tools.registry import ToolRegistry
from ..utils.logger import get_logger, setup_logging
from ..utils.metrics import MetricsCollector
from .config import Config
from .exceptions import ConfigurationError, ManusError
from .loop import AgentLoop
from .state import AgentState


class ManusAgent:
    """
    Main Manus Agent orchestrating autonomous task execution.
    
    This class provides the primary interface for interacting with the agent system,
    handling initialization, task execution, state persistence, and graceful shutdown.
    """
    
    def __init__(self, config: Optional[Config] = None, state_file: Optional[str] = None):
        """
        Initialize the Manus agent.
        
        Args:
            config: Configuration object, defaults to loading from environment
            state_file: Path to state file for persistence
        """
        # Load configuration
        self.config = config or Config.from_env()
        self.config.validate_runtime()
        
        # Set up logging
        setup_logging(self.config.logging)
        self.logger = get_logger(__name__)
        
        # Initialize state management
        self.state_file = Path(state_file) if state_file else Path("data/agent_state.json")
        self.state = self._load_or_create_state()
        
        # Initialize core components
        self.security_validator = SecurityValidator(self.config.security)
        self.tool_registry = ToolRegistry(self.security_validator)
        self.agent_loop = AgentLoop(self.config, self.tool_registry, self.security_validator)
        self.metrics = MetricsCollector()
        
        # Runtime state
        self._running = False
        self._shutdown_requested = False
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info(f"Manus agent initialized - Session: {self.state.session_id}")
    
    def _load_or_create_state(self) -> AgentState:
        """Load existing state or create new one."""
        if self.state_file.exists():
            try:
                state = AgentState.load_from_file(self.state_file)
                self.logger.info(f"Loaded existing state from {self.state_file}")
                return state
            except Exception as e:
                self.logger.warning(f"Failed to load state file, creating new state: {e}")
        
        # Create new state
        state = AgentState(
            agent_name=self.config.agent.name,
            agent_version=self.config.agent.version,
            working_directory=str(Path("data").absolute())
        )
        
        # Ensure data directory exists
        Path(state.working_directory).mkdir(parents=True, exist_ok=True)
        
        return state
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self._shutdown_requested = True
    
    async def execute_task(self, task_prompt: str) -> Dict[str, Any]:
        """
        Execute a task using the autonomous agent.
        
        Args:
            task_prompt: Description of the task to execute
            
        Returns:
            Dictionary containing execution results and metadata
        """
        if self._shutdown_requested:
            raise ManusError("Cannot execute task: shutdown in progress")
        
        self._running = True
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.logger.info(f"Starting task execution: {task_prompt[:100]}...")
            
            # Record task start
            self.metrics.record_task_start()
            
            # Execute task through agent loop
            success, result = await self.agent_loop.execute_task(
                task_prompt, 
                self.state,
                max_iterations=self.config.agent.max_iterations
            )
            
            # Calculate execution time
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Record metrics
            self.metrics.record_task_completion(success, execution_time)
            
            # Save state
            await self._save_state()
            
            # Prepare response
            response = {
                "success": success,
                "result": result,
                "execution_time": execution_time,
                "task_id": self.state.current_task.task_id if self.state.current_task else None,
                "iterations": self.state.current_task.iteration_count if self.state.current_task else 0,
                "metrics": self.metrics.get_summary()
            }
            
            self.logger.info(
                f"Task {'completed' if success else 'failed'} in {execution_time:.2f}s"
            )
            
            return response
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            self.metrics.record_task_completion(False, execution_time)
            
            error_msg = f"Task execution failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            
            return {
                "success": False,
                "result": error_msg,
                "execution_time": execution_time,
                "error": str(e),
                "metrics": self.metrics.get_summary()
            }
        finally:
            self._running = False
    
    async def chat(self, message: str) -> str:
        """
        Simple chat interface for interactive use.
        
        Args:
            message: User message
            
        Returns:
            Agent response
        """
        result = await self.execute_task(message)
        return result["result"]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status and metrics."""
        return {
            "session_id": self.state.session_id,
            "agent_name": self.state.agent_name,
            "agent_version": self.state.agent_version,
            "running": self._running,
            "current_task": {
                "id": self.state.current_task.task_id if self.state.current_task else None,
                "status": self.state.current_task.status if self.state.current_task else None,
                "iteration": self.state.current_task.iteration_count if self.state.current_task else 0,
            },
            "total_tasks": len(self.state.task_history),
            "total_iterations": self.state.total_iterations,
            "total_tool_calls": self.state.total_tool_calls,
            "total_errors": self.state.total_errors,
            "metrics": self.metrics.get_summary(),
            "available_tools": list(self.tool_registry.list_tools()),
        }
    
    def get_conversation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history."""
        messages = self.state.messages[-limit:] if limit else self.state.messages
        return [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "tool_calls": len(msg.tool_calls),
            }
            for msg in messages
        ]
    
    def clear_conversation(self) -> None:
        """Clear conversation history but preserve task history."""
        self.state.messages.clear()
        self.logger.info("Conversation history cleared")
    
    async def reset_session(self) -> None:
        """Reset the entire session, creating a new state."""
        self.logger.info("Resetting session")
        
        # Archive current state if needed
        if self.state.messages or self.state.task_history:
            archive_path = self.state_file.with_suffix(f".{self.state.session_id}.json")
            self.state.save_to_file(archive_path)
            self.logger.info(f"Archived previous session to {archive_path}")
        
        # Create new state
        self.state = AgentState(
            agent_name=self.config.agent.name,
            agent_version=self.config.agent.version,
            working_directory=str(Path("data").absolute())
        )
        
        # Reset metrics
        self.metrics = MetricsCollector()
        
        await self._save_state()
        self.logger.info(f"New session started: {self.state.session_id}")
    
    async def add_tool(self, tool_name: str, tool_function, tool_schema: Dict[str, Any]) -> None:
        """Dynamically add a new tool to the registry."""
        self.tool_registry.register_tool(tool_name, tool_function, tool_schema)
        self.logger.info(f"Added new tool: {tool_name}")
    
    async def remove_tool(self, tool_name: str) -> bool:
        """Remove a tool from the registry."""
        success = self.tool_registry.unregister_tool(tool_name)
        if success:
            self.logger.info(f"Removed tool: {tool_name}")
        return success
    
    async def _save_state(self) -> None:
        """Save current state to file."""
        try:
            self.state.save_to_file(self.state_file)
            self.logger.debug(f"State saved to {self.state_file}")
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the agent."""
        self.logger.info("Shutting down Manus agent")
        
        self._shutdown_requested = True
        
        # Wait for current task to complete if running
        if self._running:
            self.logger.info("Waiting for current task to complete...")
            timeout = 30  # 30 second timeout
            while self._running and timeout > 0:
                await asyncio.sleep(1)
                timeout -= 1
            
            if self._running:
                self.logger.warning("Force shutdown: task did not complete in time")
        
        # Save final state
        await self._save_state()
        
        # Close resources
        if hasattr(self.tool_registry, 'cleanup'):
            await self.tool_registry.cleanup()
        
        if hasattr(self.agent_loop, 'cleanup'):
            await self.agent_loop.cleanup()
        
        self.logger.info("Manus agent shutdown complete")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return (
            f"ManusAgent(session={self.state.session_id[:8]}, "
            f"running={self._running}, "
            f"tasks={len(self.state.task_history)})"
        )