"""
Agent state management for persistent task execution.

This module handles the agent's internal state, including conversation history,
task progress, and context management. It supports serialization for persistence
across container restarts and session management.
"""

import json
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from .exceptions import ValidationError


class TaskStatus(str, Enum):
    """Task execution status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolCall(BaseModel):
    """Represents a tool call made by the agent."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    result: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


class Message(BaseModel):
    """Represents a message in the conversation."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    role: str  # "user", "assistant", "tool"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tool_calls: List[ToolCall] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


class TaskContext(BaseModel):
    """Represents the context for a specific task."""
    
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Task execution data
    initial_prompt: str
    current_plan: List[str] = Field(default_factory=list)
    completed_steps: List[str] = Field(default_factory=list)
    current_step: Optional[str] = None
    
    # Progress tracking
    iteration_count: int = 0
    max_iterations: int = 50
    success_rate: float = 0.0
    
    # Results and artifacts
    final_result: Optional[str] = None
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    error_history: List[str] = Field(default_factory=list)
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }
    
    def update_status(self, status: TaskStatus) -> None:
        """Update task status with timestamp."""
        self.status = status
        self.updated_at = datetime.utcnow()
        if status == TaskStatus.COMPLETED:
            self.completed_at = datetime.utcnow()
    
    def add_error(self, error: str) -> None:
        """Add an error to the history."""
        self.error_history.append(f"{datetime.utcnow().isoformat()}: {error}")
        self.updated_at = datetime.utcnow()
    
    def calculate_success_rate(self) -> float:
        """Calculate success rate based on completed vs failed operations."""
        if self.iteration_count == 0:
            return 0.0
        
        successful_operations = len(self.completed_steps)
        failed_operations = len(self.error_history)
        total_operations = successful_operations + failed_operations
        
        if total_operations == 0:
            return 0.0
        
        self.success_rate = successful_operations / total_operations
        return self.success_rate


class AgentState(BaseModel):
    """
    Complete agent state including conversation history, context, and metadata.
    
    This class manages the agent's persistent state across multiple interactions
    and provides serialization/deserialization capabilities.
    """
    
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_name: str = "manus-remake"
    agent_version: str = "0.1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    # Conversation management
    messages: List[Message] = Field(default_factory=list)
    current_task: Optional[TaskContext] = None
    task_history: List[TaskContext] = Field(default_factory=list)
    
    # Context and memory
    working_directory: str = "/app/data"
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    global_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Performance metrics
    total_iterations: int = 0
    total_tool_calls: int = 0
    total_errors: int = 0
    average_response_time_ms: float = 0.0
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }
    
    def start_new_task(self, description: str, initial_prompt: str) -> str:
        """Start a new task and return the task ID."""
        # Archive current task if it exists
        if self.current_task:
            self.task_history.append(self.current_task)
        
        # Create new task
        self.current_task = TaskContext(
            description=description,
            initial_prompt=initial_prompt
        )
        
        self.update_activity()
        return self.current_task.task_id
    
    def add_message(
        self, 
        role: str, 
        content: str, 
        tool_calls: Optional[List[ToolCall]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a message to the conversation history."""
        message = Message(
            role=role,
            content=content,
            tool_calls=tool_calls or [],
            metadata=metadata or {}
        )
        
        self.messages.append(message)
        self.update_activity()
        return message.id
    
    def add_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Optional[str] = None,
        error: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> str:
        """Add a tool call to the current conversation."""
        tool_call = ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            error=error,
            duration_ms=duration_ms
        )
        
        # Add to the last assistant message or create a new one
        if self.messages and self.messages[-1].role == "assistant":
            self.messages[-1].tool_calls.append(tool_call)
        else:
            self.add_message("assistant", "", tool_calls=[tool_call])
        
        self.total_tool_calls += 1
        if error:
            self.total_errors += 1
        
        self.update_activity()
        return tool_call.id
    
    def update_task_progress(
        self,
        plan: Optional[List[str]] = None,
        current_step: Optional[str] = None,
        completed_step: Optional[str] = None
    ) -> None:
        """Update the current task's progress."""
        if not self.current_task:
            return
        
        if plan:
            self.current_task.current_plan = plan
        
        if current_step:
            self.current_task.current_step = current_step
        
        if completed_step:
            self.current_task.completed_steps.append(completed_step)
        
        self.current_task.iteration_count += 1
        self.total_iterations += 1
        self.current_task.updated_at = datetime.utcnow()
        self.update_activity()
    
    def complete_task(self, result: str, artifacts: Optional[Dict[str, Any]] = None) -> None:
        """Mark the current task as completed."""
        if not self.current_task:
            return
        
        self.current_task.update_status(TaskStatus.COMPLETED)
        self.current_task.final_result = result
        if artifacts:
            self.current_task.artifacts.update(artifacts)
        
        self.current_task.calculate_success_rate()
        self.update_activity()
    
    def fail_task(self, error: str) -> None:
        """Mark the current task as failed."""
        if not self.current_task:
            return
        
        self.current_task.update_status(TaskStatus.FAILED)
        self.current_task.add_error(error)
        self.total_errors += 1
        self.update_activity()
    
    def get_context_for_llm(self, max_messages: int = 20) -> Dict[str, Any]:
        """Get formatted context for LLM consumption."""
        context = {
            "session_id": self.session_id,
            "current_task": None,
            "recent_messages": [],
            "working_directory": self.working_directory,
            "global_context": self.global_context,
        }
        
        # Add current task information
        if self.current_task:
            context["current_task"] = {
                "id": self.current_task.task_id,
                "description": self.current_task.description,
                "status": self.current_task.status,
                "current_plan": self.current_task.current_plan,
                "completed_steps": self.current_task.completed_steps,
                "current_step": self.current_task.current_step,
                "iteration": self.current_task.iteration_count,
                "max_iterations": self.current_task.max_iterations,
            }
        
        # Add recent messages
        recent_messages = self.messages[-max_messages:] if self.messages else []
        context["recent_messages"] = [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "tool_calls": [
                    {
                        "tool_name": tc.tool_name,
                        "arguments": tc.arguments,
                        "result": tc.result,
                        "error": tc.error,
                    }
                    for tc in msg.tool_calls
                ],
            }
            for msg in recent_messages
        ]
        
        return context
    
    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def to_json(self) -> str:
        """Serialize state to JSON string."""
        return self.json(indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "AgentState":
        """Deserialize state from JSON string."""
        try:
            return cls.parse_raw(json_str)
        except Exception as e:
            raise ValidationError(
                f"Failed to parse agent state from JSON: {e}",
                field_name="json_data",
                validation_rule="valid_json_format"
            )
    
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save state to a file."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, "w") as f:
                f.write(self.to_json())
        except Exception as e:
            raise ValidationError(
                f"Failed to save state to file: {e}",
                field_name="file_path",
                details={"path": str(file_path)}
            )
    
    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> "AgentState":
        """Load state from a file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ValidationError(
                f"State file not found: {file_path}",
                field_name="file_path"
            )
        
        try:
            with open(file_path, "r") as f:
                json_data = f.read()
            return cls.from_json(json_data)
        except Exception as e:
            raise ValidationError(
                f"Failed to load state from file: {e}",
                field_name="file_path",
                details={"path": str(file_path)}
            )