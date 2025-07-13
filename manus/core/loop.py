"""
Core agent loop implementation with ReAct + CodeAct hybrid architecture.

This module implements the main agent loop that drives autonomous task execution,
combining reasoning (ReAct) with executable code actions (CodeAct) for maximum
flexibility and capability.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

from ..security.validator import SecurityValidator
from ..tools.registry import ToolRegistry
from ..utils.logger import get_logger
from .config import Config
from .exceptions import LLMError, ManusError, SecurityError, TimeoutError, ToolError
from .llm_providers import create_llm_provider, LLMProvider
from .state import AgentState, TaskStatus, ToolCall


class AgentLoop:
    """
    Main agent loop implementing ReAct + CodeAct hybrid architecture.
    
    The loop follows these phases:
    1. Perceive: Analyze current state and context
    2. Think: Use LLM to reason about next actions
    3. Act: Execute tools or generate code
    4. Observe: Capture results and update state
    5. Reflect: Evaluate progress and adapt strategy
    """
    
    def __init__(
        self, 
        config: Config, 
        tool_registry: ToolRegistry,
        security_validator: SecurityValidator
    ):
        self.config = config
        self.tool_registry = tool_registry
        self.security_validator = security_validator
        self.logger = get_logger(__name__)
        
        # Initialize LLM provider
        self.llm_provider = create_llm_provider(config.llm)
        
        # Performance tracking
        self.iteration_times: List[float] = []
        self.error_count = 0
        
    async def execute_task(
        self, 
        task_prompt: str, 
        state: AgentState,
        max_iterations: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Execute a task using the agent loop.
        
        Args:
            task_prompt: The initial task description
            state: Agent state to maintain context
            max_iterations: Override default max iterations
            
        Returns:
            Tuple of (success, final_result)
        """
        start_time = time.time()
        max_iterations = max_iterations or self.config.agent.max_iterations
        
        try:
            # Start new task in state
            task_id = state.start_new_task(
                description=f"Execute: {task_prompt[:100]}...",
                initial_prompt=task_prompt
            )
            
            self.logger.info(f"Starting task execution: {task_id}")
            
            # Add initial user message
            state.add_message("user", task_prompt)
            
            # Main agent loop
            for iteration in range(max_iterations):
                self.logger.debug(f"Agent loop iteration {iteration + 1}/{max_iterations}")
                
                try:
                    # Check timeout
                    if time.time() - start_time > self.config.agent.timeout_seconds:
                        raise TimeoutError(
                            f"Task exceeded timeout of {self.config.agent.timeout_seconds}s",
                            operation="task_execution",
                            timeout_seconds=self.config.agent.timeout_seconds
                        )
                    
                    # Execute one iteration of the loop
                    iteration_start = time.time()
                    should_continue = await self._execute_iteration(state, iteration)
                    iteration_time = time.time() - iteration_start
                    
                    self.iteration_times.append(iteration_time)
                    
                    if not should_continue:
                        # Task completed successfully
                        final_result = self._extract_final_result(state)
                        state.complete_task(final_result)
                        
                        total_time = time.time() - start_time
                        self.logger.info(
                            f"Task completed successfully in {iteration + 1} iterations "
                            f"({total_time:.2f}s total)"
                        )
                        return True, final_result
                        
                except Exception as e:
                    self.error_count += 1
                    error_msg = f"Error in iteration {iteration + 1}: {e}"
                    self.logger.error(error_msg)
                    
                    # Add error to state
                    if state.current_task:
                        state.current_task.add_error(error_msg)
                    
                    # Try to recover
                    if await self._attempt_recovery(e, state, iteration):
                        continue
                    else:
                        # Recovery failed, abort task
                        state.fail_task(error_msg)
                        return False, f"Task failed: {error_msg}"
            
            # Reached max iterations without completion
            error_msg = f"Task exceeded maximum iterations ({max_iterations})"
            state.fail_task(error_msg)
            self.logger.warning(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Fatal error in task execution: {e}"
            self.logger.error(error_msg, exc_info=True)
            state.fail_task(error_msg)
            return False, error_msg
    
    async def _execute_iteration(self, state: AgentState, iteration: int) -> bool:
        """
        Execute one iteration of the agent loop.
        
        Returns:
            bool: True if should continue, False if task is complete
        """
        # 1. Perceive: Get current context
        context = self._build_context(state)
        
        # 2. Think: Get LLM response with reasoning
        llm_response = await self._get_llm_response(context, state)
        
        # 3. Act: Execute any tool calls or code
        tool_results = await self._execute_actions(llm_response, state)
        
        # 4. Observe: Process results and update state
        observations = self._process_observations(tool_results, state)
        
        # 5. Reflect: Determine if task is complete
        is_complete = self._evaluate_completion(llm_response, observations, state)
        
        # Update state with progress
        state.update_task_progress()
        
        return not is_complete
    
    def _build_context(self, state: AgentState) -> Dict[str, Any]:
        """Build context for LLM including state, tools, and instructions."""
        context = {
            "system_prompt": self._get_system_prompt(),
            "conversation_history": state.get_context_for_llm(),
            "available_tools": self.tool_registry.get_tool_schemas(),
            "current_state": {
                "working_directory": state.working_directory,
                "iteration": state.current_task.iteration_count if state.current_task else 0,
                "max_iterations": self.config.agent.max_iterations,
            }
        }
        return context
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt that defines the agent's behavior."""
        return """You are Manus, an autonomous AI agent capable of executing complex tasks through reasoning and action.

You operate using a ReAct + CodeAct hybrid approach:
1. REASON about the task and plan your approach
2. ACT by calling tools or writing executable code
3. OBSERVE the results and adapt your strategy
4. REFLECT on progress and determine next steps

Key capabilities:
- File system operations (read, write, execute)
- Shell command execution with security validation
- Web browsing and automation
- Code generation and execution
- Information search and retrieval

Security guidelines:
- All operations are sandboxed and monitored
- Input validation is enforced on all tool calls
- Network access is restricted to approved domains
- File operations are limited to safe directories

When you need to take action:
1. Use available tools for standard operations
2. Generate Python code for complex logic or multi-step operations
3. Always validate inputs and handle errors gracefully
4. Provide clear explanations of your reasoning

Signal task completion by including "TASK_COMPLETE" in your response along with a summary of what was accomplished."""
    
    async def _get_llm_response(self, context: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        """Get response from LLM with tool calling support."""
        try:
            # Build messages for LLM
            messages = self._format_messages_for_llm(context, state)
            
            # Get response from LLM provider
            response = await self.llm_provider.generate_response(
                messages=messages,
                tools=context["available_tools"]
            )
            
            # Process response
            return self._process_llm_response(response, state)
            
        except Exception as e:
            raise LLMError(
                f"Failed to get LLM response: {e}",
                api_provider=self.config.llm.provider,
                details={"model": self.config.llm.model}
            )
    
    def _format_messages_for_llm(self, context: Dict[str, Any], state: AgentState) -> List[Dict[str, str]]:
        """Format conversation history for LLM."""
        messages = []
        
        # Add system context as first message
        system_context = f"""
{context['system_prompt']}

Current task context:
{json.dumps(context['conversation_history'], indent=2)}

Available tools:
{json.dumps([tool['name'] for tool in context['available_tools']], indent=2)}
"""
        
        messages.append({
            "role": "system",
            "content": system_context
        })
        
        # Add conversation history
        for msg in context['conversation_history'].get('recent_messages', []):
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return messages
    
    def _process_llm_response(self, response: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        """Process LLM response and extract actions."""
        processed = {
            "text_content": response.get("text_content", ""),
            "tool_calls": response.get("tool_calls", []),
            "reasoning": "",
            "is_complete": response.get("is_complete", False)
        }
        
        # Add assistant message to state
        state.add_message("assistant", processed["text_content"])
        
        return processed
    
    async def _execute_actions(self, llm_response: Dict[str, Any], state: AgentState) -> List[Dict[str, Any]]:
        """Execute tool calls from LLM response."""
        results = []
        
        for tool_call in llm_response["tool_calls"]:
            try:
                # Validate tool call security
                self.security_validator.validate_tool_call(
                    tool_call["name"], 
                    tool_call["input"]
                )
                
                # Execute tool
                start_time = time.time()
                result = await self.tool_registry.execute_tool(
                    tool_call["name"],
                    tool_call["input"]
                )
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Record successful tool call
                tool_call_id = state.add_tool_call(
                    tool_name=tool_call["name"],
                    arguments=tool_call["input"],
                    result=str(result),
                    duration_ms=duration_ms
                )
                
                results.append({
                    "tool_call_id": tool_call["id"],
                    "success": True,
                    "result": result,
                    "duration_ms": duration_ms
                })
                
                self.logger.debug(f"Tool {tool_call['name']} executed successfully")
                
            except SecurityError as e:
                error_msg = f"Security violation in tool {tool_call['name']}: {e}"
                self.logger.error(error_msg)
                
                state.add_tool_call(
                    tool_name=tool_call["name"],
                    arguments=tool_call["input"],
                    error=error_msg
                )
                
                results.append({
                    "tool_call_id": tool_call["id"],
                    "success": False,
                    "error": error_msg
                })
                
            except Exception as e:
                error_msg = f"Tool execution failed: {e}"
                self.logger.error(error_msg)
                
                state.add_tool_call(
                    tool_name=tool_call["name"],
                    arguments=tool_call["input"],
                    error=error_msg
                )
                
                results.append({
                    "tool_call_id": tool_call["id"],
                    "success": False,
                    "error": error_msg
                })
        
        return results
    
    def _process_observations(self, tool_results: List[Dict[str, Any]], state: AgentState) -> str:
        """Process tool execution results into observations."""
        observations = []
        
        for result in tool_results:
            if result["success"]:
                observations.append(f"Tool executed successfully: {result['result']}")
            else:
                observations.append(f"Tool execution failed: {result['error']}")
        
        observation_text = "\n".join(observations) if observations else "No tools executed"
        
        # Add observation as tool message
        if observations:
            state.add_message("tool", observation_text)
        
        return observation_text
    
    def _evaluate_completion(
        self, 
        llm_response: Dict[str, Any], 
        observations: str, 
        state: AgentState
    ) -> bool:
        """Evaluate if the task is complete based on LLM response and results."""
        # Check explicit completion signal
        if llm_response["is_complete"]:
            return True
        
        # Check for task completion indicators
        completion_indicators = [
            "task complete",
            "task finished",
            "successfully completed",
            "objective achieved",
            "goal accomplished"
        ]
        
        text_lower = llm_response["text_content"].lower()
        return any(indicator in text_lower for indicator in completion_indicators)
    
    def _extract_final_result(self, state: AgentState) -> str:
        """Extract the final result from the conversation."""
        if not state.messages:
            return "Task completed without explicit result"
        
        # Get the last assistant message
        last_message = None
        for msg in reversed(state.messages):
            if msg.role == "assistant":
                last_message = msg
                break
        
        if last_message:
            return last_message.content
        else:
            return "Task completed"
    
    async def _attempt_recovery(self, error: Exception, state: AgentState, iteration: int) -> bool:
        """Attempt to recover from an error and continue execution."""
        # Implement hierarchical recovery strategy
        
        # Level 1: Simple retry for transient errors
        if isinstance(error, (LLMError, ToolError)) and iteration < 3:
            self.logger.info(f"Attempting simple retry for {type(error).__name__}")
            await asyncio.sleep(1)  # Brief pause
            return True
        
        # Level 2: Graceful degradation
        if isinstance(error, SecurityError):
            self.logger.warning("Security error - adding to context for LLM awareness")
            state.add_message(
                "system", 
                f"Security error occurred: {error}. Please modify your approach."
            )
            return True
        
        # Level 3: Complex error recovery (future implementation)
        # This could involve asking the LLM to analyze the error and suggest alternatives
        
        return False  # Recovery failed
    
    async def cleanup(self) -> None:
        """Clean up agent loop resources."""
        if self.llm_provider:
            await self.llm_provider.cleanup()
        self.logger.info("Agent loop cleanup completed")