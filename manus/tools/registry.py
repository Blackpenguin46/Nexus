"""
Tool registry system for managing and executing agent tools.

This module provides a centralized registry for all available tools,
with schema validation, security checks, and execution orchestration.
"""

import asyncio
import inspect
import time
from typing import Any, Callable, Dict, List, Optional

from ..core.exceptions import ToolError, ValidationError
from ..security.validator import SecurityValidator
from ..utils.logger import get_logger
from .file_tools import FileTools
from .shell_tools import ShellTools


class ToolRegistry:
    """
    Central registry for all agent tools with validation and execution.
    
    Manages tool registration, schema validation, security checking,
    and coordinated execution of tools with proper error handling.
    """
    
    def __init__(self, security_validator: SecurityValidator):
        self.security_validator = security_validator
        self.logger = get_logger(__name__)
        
        # Tool storage
        self.tools: Dict[str, Callable] = {}
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        
        # Tool instances
        self.file_tools = FileTools(security_validator)
        self.shell_tools = ShellTools(security_validator)
        
        # Register built-in tools
        self._register_builtin_tools()
        
        self.logger.info(f"Tool registry initialized with {len(self.tools)} tools")
    
    def _register_builtin_tools(self) -> None:
        """Register all built-in tools."""
        # File tools
        self._register_tool_set(self.file_tools, "file_")
        
        # Shell tools  
        self._register_tool_set(self.shell_tools, "shell_")
        
        # Register placeholder tools for future implementation
        self._register_placeholder_tools()
    
    def _register_tool_set(self, tool_instance: Any, prefix: str) -> None:
        """Register all tools from a tool class instance."""
        for method_name in dir(tool_instance):
            if method_name.startswith(prefix) and not method_name.startswith('_'):
                method = getattr(tool_instance, method_name)
                if callable(method):
                    # Get schema from method docstring or annotations
                    schema = self._extract_tool_schema(method, method_name)
                    self.register_tool(method_name, method, schema)
    
    def _register_placeholder_tools(self) -> None:
        """Register placeholder tools for future implementation."""
        placeholders = [
            {
                "name": "browser_navigate",
                "description": "Navigate to a URL in the browser",
                "schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to navigate to"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "browser_click",
                "description": "Click an element on the page",
                "schema": {
                    "type": "object", 
                    "properties": {
                        "xpath": {"type": "string", "description": "XPath of element to click"}
                    },
                    "required": ["xpath"]
                }
            },
            {
                "name": "search_web",
                "description": "Search the web for information",
                "schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            }
        ]
        
        for placeholder in placeholders:
            async def placeholder_func(**kwargs):
                raise ToolError(
                    f"Tool {placeholder['name']} is not yet implemented",
                    tool_name=placeholder['name'],
                    tool_args=kwargs
                )
            
            self.register_tool(
                placeholder['name'],
                placeholder_func,
                placeholder['schema'],
                {"implemented": False, "description": placeholder['description']}
            )
    
    def register_tool(
        self,
        name: str,
        function: Callable,
        schema: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a new tool in the registry.
        
        Args:
            name: Tool name
            function: Tool function to execute
            schema: JSON schema for tool arguments
            metadata: Optional metadata about the tool
        """
        if name in self.tools:
            self.logger.warning(f"Overriding existing tool: {name}")
        
        # Validate schema format
        self._validate_schema(schema)
        
        # Store tool
        self.tools[name] = function
        self.schemas[name] = schema
        self.metadata[name] = metadata or {}
        
        self.logger.debug(f"Registered tool: {name}")
    
    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool from the registry.
        
        Args:
            name: Tool name to remove
            
        Returns:
            True if tool was removed, False if not found
        """
        if name in self.tools:
            del self.tools[name]
            del self.schemas[name]
            del self.metadata[name]
            self.logger.debug(f"Unregistered tool: {name}")
            return True
        return False
    
    def list_tools(self) -> List[str]:
        """Get list of all registered tool names."""
        return list(self.tools.keys())
    
    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific tool."""
        return self.schemas.get(name)
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get all tool schemas formatted for Claude API."""
        schemas = []
        
        for name, schema in self.schemas.items():
            # Convert to Claude tool format
            claude_schema = {
                "name": name,
                "description": self.metadata.get(name, {}).get("description", f"Execute {name}"),
                "input_schema": schema
            }
            schemas.append(claude_schema)
        
        return schemas
    
    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive information about a tool."""
        if name not in self.tools:
            return None
        
        return {
            "name": name,
            "schema": self.schemas[name],
            "metadata": self.metadata[name],
            "implemented": self.metadata[name].get("implemented", True),
            "description": self.metadata[name].get("description", f"Execute {name}")
        }
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool with the given arguments.
        
        Args:
            name: Tool name to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            ToolError: If tool execution fails
        """
        if name not in self.tools:
            raise ToolError(
                f"Tool '{name}' not found in registry",
                tool_name=name,
                tool_args=arguments
            )
        
        start_time = time.time()
        
        try:
            # Validate arguments against schema
            self._validate_arguments(name, arguments)
            
            # Security validation
            self.security_validator.validate_tool_call(name, arguments)
            
            # Get tool function
            tool_function = self.tools[name]
            
            # Execute tool (handle both sync and async functions)
            if inspect.iscoroutinefunction(tool_function):
                result = await tool_function(**arguments)
            else:
                # Run sync function in thread pool to avoid blocking
                result = await asyncio.to_thread(tool_function, **arguments)
            
            execution_time = time.time() - start_time
            self.logger.debug(f"Tool {name} executed successfully in {execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            if isinstance(e, (ToolError, ValidationError)):
                raise
            
            # Wrap unexpected errors
            raise ToolError(
                f"Tool execution failed: {e}",
                tool_name=name,
                tool_args=arguments,
                details={
                    "execution_time": execution_time,
                    "error_type": type(e).__name__
                }
            )
    
    def _validate_schema(self, schema: Dict[str, Any]) -> None:
        """Validate that a schema is properly formatted."""
        if not isinstance(schema, dict):
            raise ValidationError(
                "Tool schema must be a dictionary",
                field_name="schema",
                validation_rule="dict_type"
            )
        
        required_fields = ["type", "properties"]
        for field in required_fields:
            if field not in schema:
                raise ValidationError(
                    f"Tool schema missing required field: {field}",
                    field_name="schema",
                    validation_rule="required_fields"
                )
    
    def _validate_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """Validate tool arguments against schema."""
        schema = self.schemas[tool_name]
        
        # Check required arguments
        required = schema.get("required", [])
        for req_arg in required:
            if req_arg not in arguments:
                raise ValidationError(
                    f"Missing required argument: {req_arg}",
                    field_name=req_arg,
                    validation_rule="required"
                )
        
        # Validate argument types
        properties = schema.get("properties", {})
        for arg_name, arg_value in arguments.items():
            if arg_name in properties:
                self._validate_argument_type(arg_name, arg_value, properties[arg_name])
    
    def _validate_argument_type(self, name: str, value: Any, property_schema: Dict[str, Any]) -> None:
        """Validate a single argument type."""
        expected_type = property_schema.get("type")
        
        if expected_type == "string" and not isinstance(value, str):
            raise ValidationError(
                f"Argument '{name}' must be a string",
                field_name=name,
                validation_rule="string_type"
            )
        elif expected_type == "integer" and not isinstance(value, int):
            raise ValidationError(
                f"Argument '{name}' must be an integer",
                field_name=name,
                validation_rule="integer_type"
            )
        elif expected_type == "number" and not isinstance(value, (int, float)):
            raise ValidationError(
                f"Argument '{name}' must be a number",
                field_name=name,
                validation_rule="number_type"
            )
        elif expected_type == "boolean" and not isinstance(value, bool):
            raise ValidationError(
                f"Argument '{name}' must be a boolean",
                field_name=name,
                validation_rule="boolean_type"
            )
        elif expected_type == "array" and not isinstance(value, list):
            raise ValidationError(
                f"Argument '{name}' must be an array",
                field_name=name,
                validation_rule="array_type"
            )
        elif expected_type == "object" and not isinstance(value, dict):
            raise ValidationError(
                f"Argument '{name}' must be an object",
                field_name=name,
                validation_rule="object_type"
            )
    
    def _extract_tool_schema(self, method: Callable, tool_name: str) -> Dict[str, Any]:
        """Extract schema from method signature and docstring."""
        # Get function signature
        sig = inspect.signature(method)
        
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
                
            # Determine parameter type
            param_type = "string"  # Default
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list:
                    param_type = "array"
                elif param.annotation == dict:
                    param_type = "object"
            
            properties[param_name] = {
                "type": param_type,
                "description": f"Parameter {param_name} for {tool_name}"
            }
            
            # Check if required (no default value)
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    async def cleanup(self) -> None:
        """Clean up tool registry resources."""
        # Clean up tool instances that need cleanup
        if hasattr(self.shell_tools, 'cleanup'):
            await self.shell_tools.cleanup()
        
        self.logger.info("Tool registry cleanup completed")