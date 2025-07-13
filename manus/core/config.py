"""
Configuration management for the Manus agent system.

This module handles all configuration settings with validation, type checking,
and environment variable support. It follows the 12-factor app principles
for configuration management.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

from .exceptions import ConfigurationError


class SecurityConfig(BaseModel):
    """Security-related configuration settings."""
    
    allowed_domains: List[str] = Field(
        default=["api.anthropic.com", "googleapis.com", "github.com", "pypi.org"],
        description="Domains allowed for network requests"
    )
    blocked_ports: List[int] = Field(
        default=[22, 23, 135, 139, 445, 1433, 3389],
        description="Network ports to block for security"
    )
    max_file_size_mb: int = Field(
        default=100,
        description="Maximum file size in MB for file operations"
    )
    enable_security_scanning: bool = Field(
        default=True,
        description="Enable security scanning of inputs and outputs"
    )
    master_key: Optional[str] = Field(
        default=None,
        description="Master encryption key for sensitive data"
    )
    
    @validator("master_key")
    def validate_master_key(cls, v):
        if v and len(v) < 32:
            raise ValueError("Master key must be at least 32 characters long")
        return v


class LLMConfig(BaseModel):
    """LLM configuration settings for local and API models."""
    
    # Model selection
    provider: str = Field(default="mock", description="LLM provider: 'huggingface', 'ollama', 'anthropic', or 'mock'")
    model: str = Field(default="mock-model", description="Model name to use")
    
    # API settings (for external providers)
    api_key: Optional[str] = Field(default=None, description="API key if using external provider")
    api_base_url: Optional[str] = Field(default=None, description="Base URL for API")
    
    # Generation settings
    max_tokens: int = Field(default=2048, description="Maximum tokens per request")
    temperature: float = Field(default=0.1, description="Temperature for responses")
    max_context_window: int = Field(default=4096, description="Maximum context window size")
    request_timeout: int = Field(default=120, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    
    # Local model settings
    device: str = Field(default="cpu", description="Device for local models: 'mps' (Apple Silicon), 'cuda', 'cpu'")
    torch_dtype: str = Field(default="float32", description="Torch data type for optimization")
    load_in_8bit: bool = Field(default=False, description="Use 8-bit quantization")
    load_in_4bit: bool = Field(default=False, description="Use 4-bit quantization (saves memory)")
    trust_remote_code: bool = Field(default=False, description="Trust remote code for model loading")
    
    # Performance settings
    enable_prompt_caching: bool = Field(default=True, description="Enable prompt caching")
    batch_size: int = Field(default=1, description="Batch size for inference")
    enable_attention_slicing: bool = Field(default=True, description="Enable attention slicing for memory optimization")
    
    @validator("temperature")
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        return v


class AgentConfig(BaseModel):
    """Agent behavior configuration settings."""
    
    name: str = Field(default="manus-remake", description="Agent name")
    version: str = Field(default="0.1.0", description="Agent version")
    max_iterations: int = Field(default=50, description="Maximum agent loop iterations")
    timeout_seconds: int = Field(default=300, description="Overall task timeout")
    enable_reflection: bool = Field(default=True, description="Enable self-reflection")
    enable_planning: bool = Field(default=True, description="Enable task planning")
    max_tool_calls_per_iteration: int = Field(
        default=5, 
        description="Maximum tool calls per iteration"
    )


class BrowserConfig(BaseModel):
    """Browser automation configuration."""
    
    headless: bool = Field(default=True, description="Run browser in headless mode")
    window_size: str = Field(default="1920x1080", description="Browser window size")
    timeout: int = Field(default=30, description="Browser operation timeout")
    user_agent: str = Field(
        default="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        description="Browser user agent string"
    )
    enable_javascript: bool = Field(default=True, description="Enable JavaScript")
    enable_images: bool = Field(default=False, description="Load images")
    
    @validator("window_size")
    def validate_window_size(cls, v):
        try:
            width, height = v.split("x")
            int(width), int(height)
            return v
        except ValueError:
            raise ValueError("Window size must be in format 'WIDTHxHEIGHT'")


class ContainerConfig(BaseModel):
    """Container resource configuration."""
    
    memory_limit: str = Field(default="2g", description="Memory limit")
    cpu_limit: float = Field(default=1.0, description="CPU limit")
    network_mode: str = Field(default="bridge", description="Network mode")
    enable_security_opts: bool = Field(default=True, description="Enable security options")


class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format (json or text)")
    file: Optional[str] = Field(default=None, description="Log file path")
    max_size_mb: int = Field(default=100, description="Maximum log file size in MB")
    backup_count: int = Field(default=3, description="Number of backup log files")
    enable_detailed_logging: bool = Field(
        default=False, 
        description="Enable detailed debug logging"
    )
    
    @validator("level")
    def validate_log_level(cls, v):
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()


class Config(BaseSettings):
    """Main configuration class that aggregates all settings."""
    
    # Sub-configurations
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    container: ContainerConfig = Field(default_factory=ContainerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Development settings
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_nested_delimiter": "__",
        "case_sensitive": False,
        "extra": "ignore",  # Allow extra environment variables
    }
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        try:
            return cls()
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration: {e}",
                details={"error": str(e)}
            )
    
    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "Config":
        """Load configuration from a file."""
        config_path = Path(config_path)
        if not config_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {config_path}",
                config_key="config_file"
            )
        
        try:
            # Load configuration file content and parse
            # This would need implementation based on file format (YAML, JSON, etc.)
            return cls()
        except Exception as e:
            raise ConfigurationError(
                f"Failed to parse configuration file: {e}",
                config_key="config_file",
                details={"file_path": str(config_path), "error": str(e)}
            )
    
    def validate_runtime(self) -> None:
        """Perform runtime validation of configuration."""
        # Validate API key only for external providers
        if self.llm.provider in ["anthropic", "openai"] and not self.llm.api_key:
            raise ConfigurationError(
                f"API key is required for {self.llm.provider} provider",
                config_key="llm.api_key"
            )
        
        # Validate local model requirements
        if self.llm.provider == "huggingface":
            try:
                import torch
                import transformers
                print(f"PyTorch version: {torch.__version__}")
                print(f"Transformers version: {transformers.__version__}")
                
                # Check device availability
                if self.llm.device == "mps" and not torch.backends.mps.is_available():
                    print("MPS not available, falling back to CPU")
                    self.llm.device = "cpu"
                elif self.llm.device == "cuda" and not torch.cuda.is_available():
                    print("CUDA not available, falling back to CPU")
                    self.llm.device = "cpu"
                    
            except ImportError as e:
                raise ConfigurationError(
                    f"Required dependencies for Hugging Face provider not found: {e}",
                    config_key="llm.provider"
                )
        
        # Validate security settings
        if self.security.enable_security_scanning and not self.security.master_key:
            print("Warning: Security scanning enabled but no master key provided")
        
        # Validate resource limits
        try:
            memory_value = self.container.memory_limit.rstrip("gmkGMK")
            float(memory_value)
        except ValueError:
            raise ConfigurationError(
                "Invalid memory limit format",
                config_key="container.memory_limit",
                expected_type="string with suffix (g, m, k)"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)."""
        data = self.dict()
        
        # Mask sensitive information
        if "api_key" in data.get("llm", {}):
            data["llm"]["api_key"] = "***masked***"
        if "master_key" in data.get("security", {}):
            data["security"]["master_key"] = "***masked***"
        
        return data