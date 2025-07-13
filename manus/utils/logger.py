"""
Logging utilities for the Manus agent system.

This module provides structured logging with JSON formatting, log rotation,
and security-aware logging that masks sensitive information.
"""

import json
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.config import LoggingConfig


class SecurityAwareFormatter(logging.Formatter):
    """Formatter that masks sensitive information in log messages."""
    
    SENSITIVE_FIELDS = {
        "api_key", "token", "password", "secret", "key", 
        "authorization", "x-api-key", "master_key"
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with sensitive data masking."""
        # Create a copy to avoid modifying the original
        record_dict = record.__dict__.copy()
        
        # Mask sensitive information
        self._mask_sensitive_data(record_dict)
        
        if hasattr(record, 'extra') and record.extra:
            self._mask_sensitive_data(record.extra)
        
        return super().format(record)
    
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> None:
        """Recursively mask sensitive data in a dictionary."""
        if not isinstance(data, dict):
            return
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if key contains sensitive information
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS):
                if isinstance(value, str) and len(value) > 8:
                    data[key] = value[:4] + "***" + value[-2:]
                else:
                    data[key] = "***masked***"
            elif isinstance(value, dict):
                self._mask_sensitive_data(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._mask_sensitive_data(item)


class JSONFormatter(SecurityAwareFormatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra') and record.extra:
            log_entry.update(record.extra)
        
        # Mask sensitive data
        self._mask_sensitive_data(log_entry)
        
        return json.dumps(log_entry, default=str)


class TextFormatter(SecurityAwareFormatter):
    """Human-readable text formatter."""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


def setup_logging(config: LoggingConfig) -> None:
    """
    Set up logging configuration for the entire application.
    
    Args:
        config: Logging configuration object
    """
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set log level
    log_level = getattr(logging, config.level.upper())
    root_logger.setLevel(log_level)
    
    # Choose formatter
    if config.format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if config.file:
        file_path = Path(config.file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=file_path,
            maxBytes=config.max_size_mb * 1024 * 1024,  # Convert MB to bytes
            backupCount=config.backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    if not config.enable_detailed_logging:
        # Reduce noise from third-party libraries
        logging.getLogger("anthropic").setLevel(logging.WARNING)
        logging.getLogger("selenium").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info("Logging configured", extra={
        "level": config.level,
        "format": config.format,
        "file": str(config.file) if config.file else None,
        "detailed": config.enable_detailed_logging
    })


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class StructuredLogger:
    """Wrapper for structured logging with context management."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._context: Dict[str, Any] = {}
    
    def add_context(self, **kwargs) -> None:
        """Add context fields to all subsequent log messages."""
        self._context.update(kwargs)
    
    def remove_context(self, *keys) -> None:
        """Remove context fields."""
        for key in keys:
            self._context.pop(key, None)
    
    def clear_context(self) -> None:
        """Clear all context fields."""
        self._context.clear()
    
    def _log_with_context(self, level: int, message: str, **kwargs) -> None:
        """Log message with context."""
        extra = {**self._context, **kwargs}
        self.logger.log(level, message, extra={"extra": extra})
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)


def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Structured logger instance
    """
    return StructuredLogger(get_logger(name))