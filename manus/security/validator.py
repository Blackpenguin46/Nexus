"""
Security validation system for the Manus agent.

This module implements zero-trust security validation for all agent operations,
including input sanitization, command validation, path traversal protection,
and network access controls.
"""

import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from ..core.config import SecurityConfig
from ..core.exceptions import SecurityError
from ..utils.logger import get_logger


class SecurityValidator:
    """
    Comprehensive security validator implementing zero-trust principles.
    
    All agent operations must pass through security validation to prevent
    unauthorized access, code injection, and other security threats.
    """
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Command validation patterns
        self.ALLOWED_COMMANDS = {
            'ls', 'pwd', 'echo', 'cat', 'grep', 'find', 'head', 'tail',
            'wc', 'sort', 'uniq', 'cut', 'awk', 'sed', 'git', 'pip',
            'python', 'python3', 'node', 'npm', 'curl', 'wget', 'mkdir',
            'touch', 'cp', 'mv', 'chmod', 'which', 'whoami', 'date'
        }
        
        self.FORBIDDEN_PATTERNS = [
            r'rm\s+-rf',              # Dangerous deletions
            r'rm\s+--recursive',      # Recursive deletions
            r';\s*rm',                # Command chaining with rm
            r'\|\s*sh',               # Piping to shell
            r'\|\s*bash',             # Piping to bash
            r'>\s*/dev/',             # Writing to device files
            r'curl.*\|.*sh',          # Downloading and executing
            r'wget.*\|.*sh',          # Downloading and executing
            r'eval\s*\(',             # Dynamic code evaluation
            r'exec\s*\(',             # Code execution
            r'__import__',            # Python imports
            r'subprocess\.',          # Subprocess calls
            r'os\.system',            # OS system calls
            r'os\.popen',             # OS popen calls
            r'dd\s+if=',              # Disk operations
            r'mkfs\.',                # Filesystem creation
            r'fdisk',                 # Disk partitioning
            r'mount\s+',              # Mounting filesystems
            r'umount\s+',             # Unmounting filesystems
            r'sudo\s+',               # Privilege escalation
            r'su\s+',                 # User switching
            r'passwd\s+',             # Password changes
            r'chown\s+',              # Ownership changes
            r'chgrp\s+',              # Group changes
            r'systemctl\s+',          # System control
            r'service\s+',            # Service management
            r'crontab\s+',            # Cron operations
            r'nc\s+.*-[el]',          # Netcat listeners
            r'netcat\s+.*-[el]',      # Netcat listeners
            r'/etc/passwd',           # System files
            r'/etc/shadow',           # Shadow file
            r'/root/',                # Root directory
            r'\.\./',                 # Directory traversal
            r'\.\./\.\.',             # Multiple traversal
        ]
        
        # Safe base paths for file operations
        self.ALLOWED_BASE_PATHS = [
            '/app', '/tmp', '/home/manus', '/var/tmp/manus'
        ]
        
        # Network validation
        self.allowed_domains = set(config.allowed_domains)
        self.blocked_ports = set(config.blocked_ports)
        
        self.logger.info("Security validator initialized with zero-trust configuration")
    
    def validate_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """
        Validate a tool call for security compliance.
        
        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments to validate
            
        Raises:
            SecurityError: If validation fails
        """
        self.logger.debug(f"Validating tool call: {tool_name}")
        
        # Validate tool name
        if not self._is_safe_tool_name(tool_name):
            raise SecurityError(
                f"Tool '{tool_name}' is not allowed",
                violation_type="unauthorized_tool",
                attempted_action=tool_name
            )
        
        # Validate arguments based on tool type
        if tool_name.startswith('shell_'):
            self._validate_shell_arguments(arguments)
        elif tool_name.startswith('file_'):
            self._validate_file_arguments(arguments)
        elif tool_name.startswith('browser_'):
            self._validate_browser_arguments(arguments)
        elif tool_name.startswith('network_'):
            self._validate_network_arguments(arguments)
        
        # Generic argument validation
        self._validate_generic_arguments(arguments)
    
    def validate_shell_command(self, command: str) -> None:
        """
        Validate a shell command for security threats.
        
        Args:
            command: Shell command to validate
            
        Raises:
            SecurityError: If command is not safe
        """
        if not command or not command.strip():
            raise SecurityError(
                "Empty command not allowed",
                violation_type="empty_command"
            )
        
        # Check for forbidden patterns
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                raise SecurityError(
                    f"Command contains forbidden pattern: {pattern}",
                    violation_type="forbidden_pattern",
                    attempted_action=command
                )
        
        # Parse and validate command structure
        try:
            tokens = shlex.split(command)
            if not tokens:
                raise SecurityError(
                    "Invalid command structure",
                    violation_type="invalid_command",
                    attempted_action=command
                )
            
            # Check base command
            base_command = tokens[0].split('/')[-1]  # Get command name without path
            if base_command not in self.ALLOWED_COMMANDS:
                raise SecurityError(
                    f"Command '{base_command}' is not in allowed list",
                    violation_type="unauthorized_command",
                    attempted_action=command
                )
            
            # Additional validation for specific commands
            self._validate_specific_command(base_command, tokens[1:])
            
        except ValueError as e:
            raise SecurityError(
                f"Failed to parse command: {e}",
                violation_type="parse_error",
                attempted_action=command
            )
    
    def validate_file_path(self, path: str, operation: str = "access") -> str:
        """
        Validate a file path for security compliance.
        
        Args:
            path: File path to validate
            operation: Type of operation (read, write, delete, etc.)
            
        Returns:
            Absolute, normalized path if valid
            
        Raises:
            SecurityError: If path is not safe
        """
        if not path:
            raise SecurityError(
                "Empty path not allowed",
                violation_type="empty_path"
            )
        
        try:
            # Normalize and resolve the path
            normalized_path = Path(path).resolve()
            
            # Check if path is within allowed directories
            path_str = str(normalized_path)
            allowed = False
            
            for base_path in self.ALLOWED_BASE_PATHS:
                base_resolved = str(Path(base_path).resolve())
                if path_str.startswith(base_resolved):
                    allowed = True
                    break
            
            if not allowed:
                raise SecurityError(
                    f"Path '{path}' is outside allowed directories",
                    violation_type="path_traversal",
                    attempted_action=f"{operation} {path}"
                )
            
            # Additional checks for sensitive files
            sensitive_patterns = [
                r'/etc/passwd', r'/etc/shadow', r'/root/', r'\.ssh/',
                r'\.env', r'\.key', r'id_rsa', r'id_dsa', r'\.pem'
            ]
            
            for pattern in sensitive_patterns:
                if re.search(pattern, path_str, re.IGNORECASE):
                    raise SecurityError(
                        f"Access to sensitive file '{path}' is not allowed",
                        violation_type="sensitive_file_access",
                        attempted_action=f"{operation} {path}"
                    )
            
            return path_str
            
        except (OSError, ValueError) as e:
            raise SecurityError(
                f"Invalid path '{path}': {e}",
                violation_type="invalid_path",
                attempted_action=f"{operation} {path}"
            )
    
    def validate_network_request(self, url: str) -> None:
        """
        Validate a network request for security compliance.
        
        Args:
            url: URL to validate
            
        Raises:
            SecurityError: If request is not allowed
        """
        try:
            parsed = urlparse(url)
            
            # Check protocol
            if parsed.scheme not in {'http', 'https'}:
                raise SecurityError(
                    f"Protocol '{parsed.scheme}' is not allowed",
                    violation_type="unauthorized_protocol",
                    attempted_action=f"request {url}"
                )
            
            # Check domain
            domain = parsed.netloc.lower()
            if ':' in domain:
                domain, port_str = domain.split(':', 1)
                try:
                    port = int(port_str)
                    if port in self.blocked_ports:
                        raise SecurityError(
                            f"Port {port} is blocked",
                            violation_type="blocked_port",
                            attempted_action=f"request {url}"
                        )
                except ValueError:
                    raise SecurityError(
                        f"Invalid port in URL: {port_str}",
                        violation_type="invalid_port",
                        attempted_action=f"request {url}"
                    )
            
            # Check if domain is allowed
            domain_allowed = False
            for allowed_domain in self.allowed_domains:
                if domain == allowed_domain or domain.endswith('.' + allowed_domain):
                    domain_allowed = True
                    break
            
            if not domain_allowed:
                raise SecurityError(
                    f"Domain '{domain}' is not in allowed list",
                    violation_type="unauthorized_domain",
                    attempted_action=f"request {url}"
                )
            
        except Exception as e:
            if isinstance(e, SecurityError):
                raise
            raise SecurityError(
                f"Failed to validate URL '{url}': {e}",
                violation_type="url_validation_error",
                attempted_action=f"request {url}"
            )
    
    def validate_python_code(self, code: str) -> None:
        """
        Validate Python code for security threats.
        
        Args:
            code: Python code to validate
            
        Raises:
            SecurityError: If code contains security threats
        """
        if not code or not code.strip():
            return
        
        # Check for dangerous imports and functions
        dangerous_patterns = [
            r'import\s+os\b',
            r'from\s+os\s+import',
            r'import\s+subprocess\b',
            r'from\s+subprocess\s+import',
            r'import\s+sys\b',
            r'from\s+sys\s+import',
            r'__import__\s*\(',
            r'eval\s*\(',
            r'exec\s*\(',
            r'compile\s*\(',
            r'open\s*\(',
            r'file\s*\(',
            r'input\s*\(',
            r'raw_input\s*\(',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                raise SecurityError(
                    f"Python code contains dangerous pattern: {pattern}",
                    violation_type="dangerous_code",
                    attempted_action=f"execute code: {code[:100]}..."
                )
        
        # Check for file operations
        file_patterns = [
            r'with\s+open\s*\(',
            r'\.read\s*\(',
            r'\.write\s*\(',
            r'\.writelines\s*\(',
        ]
        
        for pattern in file_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                # Allow file operations but log them
                self.logger.warning(f"Python code contains file operation: {pattern}")
    
    def _is_safe_tool_name(self, tool_name: str) -> bool:
        """Check if a tool name is safe to use."""
        # Basic format validation
        if not re.match(r'^[a-z][a-z0-9_]*$', tool_name):
            return False
        
        # Check against known safe tools
        safe_prefixes = {
            'file_', 'shell_', 'browser_', 'search_', 'info_',
            'code_', 'media_', 'message_', 'debug_', 'help_'
        }
        
        return any(tool_name.startswith(prefix) for prefix in safe_prefixes)
    
    def _validate_shell_arguments(self, arguments: Dict[str, Any]) -> None:
        """Validate shell tool arguments."""
        if 'command' in arguments:
            self.validate_shell_command(arguments['command'])
        
        if 'working_directory' in arguments:
            self.validate_file_path(arguments['working_directory'], 'access')
    
    def _validate_file_arguments(self, arguments: Dict[str, Any]) -> None:
        """Validate file tool arguments."""
        if 'path' in arguments:
            self.validate_file_path(arguments['path'], 'access')
        
        if 'file_path' in arguments:
            self.validate_file_path(arguments['file_path'], 'access')
        
        if 'content' in arguments and isinstance(arguments['content'], str):
            # Check for suspicious content
            if len(arguments['content']) > self.config.max_file_size_mb * 1024 * 1024:
                raise SecurityError(
                    f"File content exceeds maximum size limit",
                    violation_type="oversized_content"
                )
    
    def _validate_browser_arguments(self, arguments: Dict[str, Any]) -> None:
        """Validate browser tool arguments."""
        if 'url' in arguments:
            self.validate_network_request(arguments['url'])
        
        if 'xpath' in arguments:
            # Basic XPath validation to prevent injection
            xpath = arguments['xpath']
            if not isinstance(xpath, str) or len(xpath) > 500:
                raise SecurityError(
                    "Invalid XPath expression",
                    violation_type="invalid_xpath"
                )
    
    def _validate_network_arguments(self, arguments: Dict[str, Any]) -> None:
        """Validate network tool arguments."""
        if 'url' in arguments:
            self.validate_network_request(arguments['url'])
        
        if 'domain' in arguments:
            domain = arguments['domain'].lower()
            if domain not in self.allowed_domains:
                raise SecurityError(
                    f"Domain '{domain}' is not allowed",
                    violation_type="unauthorized_domain"
                )
    
    def _validate_generic_arguments(self, arguments: Dict[str, Any]) -> None:
        """Perform generic validation on all arguments."""
        for key, value in arguments.items():
            if isinstance(value, str):
                # Check for injection patterns
                injection_patterns = [
                    r'<script\b', r'javascript:', r'on\w+\s*=',
                    r'\$\(', r'eval\s*\(', r'document\.',
                ]
                
                for pattern in injection_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        self.logger.warning(
                            f"Potentially dangerous content in argument '{key}': {pattern}"
                        )
                
                # Check argument length
                if len(value) > 10000:  # 10KB limit
                    raise SecurityError(
                        f"Argument '{key}' exceeds maximum length",
                        violation_type="oversized_argument"
                    )
    
    def _validate_specific_command(self, command: str, args: List[str]) -> None:
        """Validate specific commands with additional rules."""
        if command == 'git':
            # Allow most git commands but restrict some
            if args and args[0] in ['config', 'remote']:
                if '--global' in args:
                    raise SecurityError(
                        "Global git configuration changes not allowed",
                        violation_type="unauthorized_git_operation"
                    )
        
        elif command in ['curl', 'wget']:
            # Validate URLs in curl/wget commands
            for arg in args:
                if arg.startswith('http'):
                    self.validate_network_request(arg)
        
        elif command == 'python' or command == 'python3':
            # Check for dangerous Python flags
            dangerous_flags = ['-c', '--command', '-m', '--module']
            for flag in dangerous_flags:
                if flag in args:
                    # If using -c flag, validate the code
                    if flag in ['-c', '--command']:
                        idx = args.index(flag)
                        if idx + 1 < len(args):
                            self.validate_python_code(args[idx + 1])