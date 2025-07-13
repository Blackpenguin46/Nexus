"""
Exception classes for the Manus agent system.

This module defines the exception hierarchy used throughout the agent system,
following Python best practices for error handling and providing detailed
error information for debugging and monitoring.
"""

import traceback
from typing import Any, Dict, Optional


class ManusError(Exception):
    """Base exception class for all Manus-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause
        self.traceback_str = traceback.format_exc() if cause else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "traceback": self.traceback_str,
        }


class SecurityError(ManusError):
    """Raised when security validation fails."""
    
    def __init__(
        self,
        message: str,
        violation_type: str,
        attempted_action: Optional[str] = None,
        **kwargs,
    ):
        details = {
            "violation_type": violation_type,
            "attempted_action": attempted_action,
        }
        details.update(kwargs.get("details", {}))
        super().__init__(message, error_code="SECURITY_VIOLATION", details=details)


class ToolError(ManusError):
    """Raised when tool execution fails."""
    
    def __init__(
        self,
        message: str,
        tool_name: str,
        tool_args: Optional[Dict[str, Any]] = None,
        exit_code: Optional[int] = None,
        **kwargs,
    ):
        details = {
            "tool_name": tool_name,
            "tool_args": tool_args,
            "exit_code": exit_code,
        }
        details.update(kwargs.get("details", {}))
        super().__init__(message, error_code="TOOL_EXECUTION_FAILED", details=details)


class LLMError(ManusError):
    """Raised when LLM API calls fail."""
    
    def __init__(
        self,
        message: str,
        api_provider: str,
        status_code: Optional[int] = None,
        retry_count: Optional[int] = None,
        **kwargs,
    ):
        details = {
            "api_provider": api_provider,
            "status_code": status_code,
            "retry_count": retry_count,
        }
        details.update(kwargs.get("details", {}))
        super().__init__(message, error_code="LLM_API_ERROR", details=details)


class ConfigurationError(ManusError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None,
        **kwargs,
    ):
        details = {
            "config_key": config_key,
            "expected_type": expected_type,
        }
        details.update(kwargs.get("details", {}))
        super().__init__(message, error_code="CONFIGURATION_ERROR", details=details)


class ValidationError(ManusError):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        validation_rule: Optional[str] = None,
        **kwargs,
    ):
        details = {
            "field_name": field_name,
            "validation_rule": validation_rule,
        }
        details.update(kwargs.get("details", {}))
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class TimeoutError(ManusError):
    """Raised when operations exceed timeout limits."""
    
    def __init__(
        self,
        message: str,
        operation: str,
        timeout_seconds: float,
        **kwargs,
    ):
        details = {
            "operation": operation,
            "timeout_seconds": timeout_seconds,
        }
        details.update(kwargs.get("details", {}))
        super().__init__(message, error_code="TIMEOUT_ERROR", details=details)


class ResourceError(ManusError):
    """Raised when system resources are exhausted."""
    
    def __init__(
        self,
        message: str,
        resource_type: str,
        current_usage: Optional[float] = None,
        limit: Optional[float] = None,
        **kwargs,
    ):
        details = {
            "resource_type": resource_type,
            "current_usage": current_usage,
            "limit": limit,
        }
        details.update(kwargs.get("details", {}))
        super().__init__(message, error_code="RESOURCE_EXHAUSTED", details=details)