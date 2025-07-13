"""
FastAPI web server for the Manus agent.

Provides REST API endpoints for interacting with the agent,
monitoring status, and managing tasks.
"""

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..core.agent import ManusAgent
from ..core.config import Config
from ..utils.logger import get_logger


# Request/Response models
class TaskRequest(BaseModel):
    prompt: str
    max_iterations: Optional[int] = None


class TaskResponse(BaseModel):
    success: bool
    result: str
    task_id: Optional[str]
    execution_time: float
    iterations: int
    metrics: Dict[str, Any]


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    task_id: Optional[str]


class StatusResponse(BaseModel):
    session_id: str
    agent_name: str
    agent_version: str
    running: bool
    current_task: Dict[str, Any]
    total_tasks: int
    total_iterations: int
    total_tool_calls: int
    total_errors: int
    metrics: Dict[str, Any]
    available_tools: List[str]


# Global agent instance
_agent: Optional[ManusAgent] = None
logger = get_logger(__name__)


def create_app(config: Config) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Manus Agent API",
        description="REST API for the Manus autonomous AI agent",
        version="0.1.0",
        docs_url="/docs" if config.debug_mode else None,
        redoc_url="/redoc" if config.debug_mode else None
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if config.debug_mode else ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize the agent on startup."""
        global _agent
        try:
            _agent = ManusAgent(config)
            logger.info("Manus agent initialized for API server")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up resources on shutdown."""
        global _agent
        if _agent:
            await _agent.shutdown()
            logger.info("Manus agent shut down")
    
    def get_agent() -> ManusAgent:
        """Get the global agent instance."""
        if _agent is None:
            raise HTTPException(status_code=500, detail="Agent not initialized")
        return _agent
    
    @app.get("/", response_model=Dict[str, str])
    async def root():
        """Root endpoint with basic information."""
        return {
            "name": "Manus Agent API",
            "version": "0.1.0",
            "status": "running",
            "docs": "/docs" if config.debug_mode else "disabled"
        }
    
    @app.get("/health", response_model=Dict[str, str])
    async def health_check():
        """Health check endpoint."""
        agent = get_agent()
        return {
            "status": "healthy",
            "session_id": agent.state.session_id,
            "agent_version": agent.state.agent_version
        }
    
    @app.get("/status", response_model=StatusResponse)
    async def get_status():
        """Get current agent status and metrics."""
        agent = get_agent()
        status = agent.get_status()
        return StatusResponse(**status)
    
    @app.post("/task", response_model=TaskResponse)
    async def execute_task(request: TaskRequest, background_tasks: BackgroundTasks):
        """Execute a task with the agent."""
        agent = get_agent()
        
        try:
            result = await agent.execute_task(request.prompt)
            return TaskResponse(**result)
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        """Simple chat interface."""
        agent = get_agent()
        
        try:
            response = await agent.chat(request.message)
            return ChatResponse(
                response=response,
                task_id=agent.state.current_task.task_id if agent.state.current_task else None
            )
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/history", response_model=List[Dict[str, Any]])
    async def get_history(limit: int = 50):
        """Get conversation history."""
        agent = get_agent()
        return agent.get_conversation_history(limit)
    
    @app.delete("/history")
    async def clear_history():
        """Clear conversation history."""
        agent = get_agent()
        agent.clear_conversation()
        return {"message": "Conversation history cleared"}
    
    @app.post("/reset")
    async def reset_session():
        """Reset the agent session."""
        agent = get_agent()
        await agent.reset_session()
        return {"message": "Session reset successfully"}
    
    @app.get("/tools", response_model=List[str])
    async def list_tools():
        """Get list of available tools."""
        agent = get_agent()
        return agent.tool_registry.list_tools()
    
    @app.get("/tools/{tool_name}", response_model=Dict[str, Any])
    async def get_tool_info(tool_name: str):
        """Get information about a specific tool."""
        agent = get_agent()
        tool_info = agent.tool_registry.get_tool_info(tool_name)
        
        if tool_info is None:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        return tool_info
    
    @app.get("/metrics", response_model=Dict[str, Any])
    async def get_metrics():
        """Get detailed metrics and performance data."""
        agent = get_agent()
        return {
            "summary": agent.metrics.get_summary(),
            "tool_performance": agent.metrics.get_tool_performance(),
            "error_summary": agent.metrics.get_error_summary(),
            "performance_trend": agent.metrics.get_performance_trend(60)  # Last hour
        }
    
    @app.get("/config", response_model=Dict[str, Any])
    async def get_config():
        """Get current configuration (sensitive data masked)."""
        if not config.debug_mode:
            raise HTTPException(status_code=403, detail="Config access disabled in production")
        
        return config.to_dict()
    
    return app