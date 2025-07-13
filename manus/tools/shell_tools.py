"""
Production-grade shell tools for the Manus agent.

This module provides secure shell command execution with comprehensive
validation, output capture, and proper process management.
"""

import asyncio
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..core.exceptions import ToolError, TimeoutError
from ..security.validator import SecurityValidator
from ..utils.logger import get_logger


class ShellTools:
    """
    Secure shell command execution with production-grade safety.
    
    All commands go through security validation and are executed
    with proper isolation, timeout handling, and output capture.
    """
    
    def __init__(self, security_validator: SecurityValidator):
        self.security_validator = security_validator
        self.logger = get_logger(__name__)
        
        # Default timeout for commands (seconds)
        self.default_timeout = 30
        
        # Maximum output size (bytes)
        self.max_output_size = 1024 * 1024  # 1MB
        
        # Current working directory for shell operations
        self.working_directory = "/app/data"
        
        # Ensure working directory exists
        Path(self.working_directory).mkdir(parents=True, exist_ok=True)
    
    async def shell_exec(
        self,
        command: str,
        timeout: Optional[int] = None,
        capture_output: bool = True,
        working_directory: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a shell command with security validation and output capture.
        
        Args:
            command: Shell command to execute
            timeout: Timeout in seconds (default: 30)
            capture_output: Whether to capture stdout/stderr
            working_directory: Working directory for command execution
            
        Returns:
            Dictionary with execution results
            
        Raises:
            ToolError: If command execution fails
            TimeoutError: If command exceeds timeout
        """
        start_time = time.time()
        timeout = timeout or self.default_timeout
        
        try:
            # Validate command
            self.security_validator.validate_shell_command(command)
            
            # Validate working directory if provided
            if working_directory:
                safe_wd = self.security_validator.validate_file_path(working_directory, "access")
                working_directory = safe_wd
            else:
                working_directory = self.working_directory
            
            # Ensure working directory exists
            Path(working_directory).mkdir(parents=True, exist_ok=True)
            
            self.logger.debug(f"Executing command: {command[:100]}...")
            
            # Prepare environment
            env = os.environ.copy()
            env.update({
                'HOME': '/home/manus',
                'USER': 'manus',
                'SHELL': '/bin/bash',
                'PATH': '/usr/local/bin:/usr/bin:/bin',
                'TERM': 'xterm-256color',
            })
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                cwd=working_directory,
                env=env,
                limit=self.max_output_size
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # Kill the process
                process.kill()
                await process.wait()
                
                execution_time = time.time() - start_time
                raise TimeoutError(
                    f"Command timed out after {timeout} seconds",
                    operation="shell_command",
                    timeout_seconds=timeout
                )
            
            execution_time = time.time() - start_time
            
            # Decode output
            stdout_text = stdout.decode('utf-8', errors='replace') if stdout else ''
            stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ''
            
            # Prepare result
            result = {
                "command": command,
                "exit_code": process.returncode,
                "success": process.returncode == 0,
                "execution_time": execution_time,
                "working_directory": working_directory,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "output_size": len(stdout_text) + len(stderr_text)
            }
            
            # Log result
            if process.returncode == 0:
                self.logger.debug(f"Command succeeded in {execution_time:.2f}s")
            else:
                self.logger.warning(f"Command failed with exit code {process.returncode}")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            if isinstance(e, (ToolError, TimeoutError)):
                raise
            
            raise ToolError(
                f"Shell command execution failed: {e}",
                tool_name="shell_exec",
                tool_args={
                    "command": command,
                    "timeout": timeout,
                    "execution_time": execution_time
                }
            )
    
    async def shell_which(self, command: str) -> Dict[str, Any]:
        """
        Find the location of a command in the system PATH.
        
        Args:
            command: Command name to locate
            
        Returns:
            Dictionary with command location info
        """
        try:
            result = await self.shell_exec(f"which {command}", timeout=10)
            
            if result["success"] and result["stdout"].strip():
                location = result["stdout"].strip()
                return {
                    "command": command,
                    "found": True,
                    "location": location,
                    "executable": True
                }
            else:
                return {
                    "command": command,
                    "found": False,
                    "location": None,
                    "executable": False
                }
                
        except Exception as e:
            return {
                "command": command,
                "found": False,
                "location": None,
                "executable": False,
                "error": str(e)
            }
    
    async def shell_pwd(self) -> str:
        """
        Get the current working directory.
        
        Returns:
            Current working directory path
        """
        try:
            result = await self.shell_exec("pwd", timeout=5)
            
            if result["success"]:
                return result["stdout"].strip()
            else:
                return self.working_directory
                
        except Exception:
            return self.working_directory
    
    async def shell_cd(self, directory: str) -> str:
        """
        Change the working directory for subsequent commands.
        
        Args:
            directory: Directory to change to
            
        Returns:
            Success message with new working directory
            
        Raises:
            ToolError: If directory change fails
        """
        try:
            # Validate directory path
            safe_path = self.security_validator.validate_file_path(directory, "access")
            dir_path = Path(safe_path)
            
            if not dir_path.exists():
                raise ToolError(
                    f"Directory does not exist: {directory}",
                    tool_name="shell_cd",
                    tool_args={"directory": directory}
                )
            
            if not dir_path.is_dir():
                raise ToolError(
                    f"Path is not a directory: {directory}",
                    tool_name="shell_cd",
                    tool_args={"directory": directory}
                )
            
            # Update working directory
            self.working_directory = str(dir_path.resolve())
            
            self.logger.debug(f"Changed working directory to: {self.working_directory}")
            return f"Changed working directory to: {self.working_directory}"
            
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Failed to change directory: {e}",
                tool_name="shell_cd",
                tool_args={"directory": directory}
            )
    
    async def shell_ls(
        self,
        path: Optional[str] = None,
        all_files: bool = False,
        long_format: bool = False
    ) -> Dict[str, Any]:
        """
        List directory contents.
        
        Args:
            path: Path to list (default: current working directory)
            all_files: Show hidden files (ls -a)
            long_format: Use long format (ls -l)
            
        Returns:
            Dictionary with directory listing
        """
        try:
            # Build ls command
            cmd_parts = ["ls"]
            
            if all_files:
                cmd_parts.append("-a")
            
            if long_format:
                cmd_parts.append("-l")
            
            if path:
                # Validate path
                safe_path = self.security_validator.validate_file_path(path, "read")
                cmd_parts.append(f"'{safe_path}'")
            
            command = " ".join(cmd_parts)
            result = await self.shell_exec(command, timeout=15)
            
            return {
                "path": path or self.working_directory,
                "command": command,
                "success": result["success"],
                "output": result["stdout"],
                "error": result["stderr"],
                "exit_code": result["exit_code"]
            }
            
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Failed to list directory: {e}",
                tool_name="shell_ls",
                tool_args={"path": path, "all_files": all_files, "long_format": long_format}
            )
    
    async def shell_cat(self, file_path: str, lines: Optional[int] = None) -> Dict[str, Any]:
        """
        Display file contents using cat command.
        
        Args:
            file_path: Path to file to display
            lines: Number of lines to display (uses head if specified)
            
        Returns:
            Dictionary with file contents
        """
        try:
            # Validate file path
            safe_path = self.security_validator.validate_file_path(file_path, "read")
            
            # Build command
            if lines:
                command = f"head -n {lines} '{safe_path}'"
            else:
                command = f"cat '{safe_path}'"
            
            result = await self.shell_exec(command, timeout=30)
            
            return {
                "file_path": file_path,
                "command": command,
                "success": result["success"],
                "content": result["stdout"],
                "error": result["stderr"],
                "exit_code": result["exit_code"],
                "lines_requested": lines
            }
            
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Failed to read file: {e}",
                tool_name="shell_cat",
                tool_args={"file_path": file_path, "lines": lines}
            )
    
    async def shell_grep(
        self,
        pattern: str,
        file_path: Optional[str] = None,
        recursive: bool = False,
        case_insensitive: bool = False,
        line_numbers: bool = False
    ) -> Dict[str, Any]:
        """
        Search for patterns in files using grep.
        
        Args:
            pattern: Search pattern
            file_path: File or directory to search (default: current directory)
            recursive: Search recursively in directories
            case_insensitive: Case insensitive search
            line_numbers: Show line numbers
            
        Returns:
            Dictionary with search results
        """
        try:
            # Build grep command
            cmd_parts = ["grep"]
            
            if case_insensitive:
                cmd_parts.append("-i")
            
            if line_numbers:
                cmd_parts.append("-n")
            
            if recursive:
                cmd_parts.append("-r")
            
            # Add pattern (quoted for safety)
            cmd_parts.append(f"'{pattern}'")
            
            # Add file path if specified
            if file_path:
                safe_path = self.security_validator.validate_file_path(file_path, "read")
                cmd_parts.append(f"'{safe_path}'")
            
            command = " ".join(cmd_parts)
            result = await self.shell_exec(command, timeout=60)
            
            return {
                "pattern": pattern,
                "file_path": file_path,
                "command": command,
                "success": result["success"],
                "matches": result["stdout"],
                "error": result["stderr"],
                "exit_code": result["exit_code"],
                "match_count": len(result["stdout"].splitlines()) if result["stdout"] else 0
            }
            
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Failed to search files: {e}",
                tool_name="shell_grep",
                tool_args={
                    "pattern": pattern,
                    "file_path": file_path,
                    "recursive": recursive
                }
            )
    
    async def shell_find(
        self,
        search_path: Optional[str] = None,
        name_pattern: Optional[str] = None,
        file_type: Optional[str] = None,
        max_depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Find files and directories using find command.
        
        Args:
            search_path: Path to search in (default: current directory)
            name_pattern: Name pattern to match
            file_type: File type filter ('f' for files, 'd' for directories)
            max_depth: Maximum search depth
            
        Returns:
            Dictionary with search results
        """
        try:
            # Build find command
            cmd_parts = ["find"]
            
            # Add search path
            if search_path:
                safe_path = self.security_validator.validate_file_path(search_path, "read")
                cmd_parts.append(f"'{safe_path}'")
            else:
                cmd_parts.append(".")
            
            # Add max depth
            if max_depth:
                cmd_parts.extend(["-maxdepth", str(max_depth)])
            
            # Add file type filter
            if file_type in ['f', 'd', 'l']:  # file, directory, link
                cmd_parts.extend(["-type", file_type])
            
            # Add name pattern
            if name_pattern:
                cmd_parts.extend(["-name", f"'{name_pattern}'"])
            
            command = " ".join(cmd_parts)
            result = await self.shell_exec(command, timeout=60)
            
            # Parse results
            files = []
            if result["success"] and result["stdout"]:
                files = [line.strip() for line in result["stdout"].splitlines() if line.strip()]
            
            return {
                "search_path": search_path or ".",
                "name_pattern": name_pattern,
                "file_type": file_type,
                "command": command,
                "success": result["success"],
                "files": files,
                "file_count": len(files),
                "error": result["stderr"],
                "exit_code": result["exit_code"]
            }
            
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Failed to find files: {e}",
                tool_name="shell_find",
                tool_args={
                    "search_path": search_path,
                    "name_pattern": name_pattern,
                    "file_type": file_type
                }
            )
    
    async def shell_env(self) -> Dict[str, str]:
        """
        Get environment variables.
        
        Returns:
            Dictionary of environment variables
        """
        try:
            result = await self.shell_exec("env", timeout=10)
            
            env_vars = {}
            if result["success"]:
                for line in result["stdout"].splitlines():
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key] = value
            
            return env_vars
            
        except Exception as e:
            raise ToolError(
                f"Failed to get environment variables: {e}",
                tool_name="shell_env",
                tool_args={}
            )
    
    async def shell_ps(self) -> Dict[str, Any]:
        """
        List running processes.
        
        Returns:
            Dictionary with process information
        """
        try:
            result = await self.shell_exec("ps aux", timeout=15)
            
            processes = []
            if result["success"] and result["stdout"]:
                lines = result["stdout"].splitlines()
                if lines:
                    # Skip header line
                    for line in lines[1:]:
                        parts = line.split(None, 10)
                        if len(parts) >= 11:
                            processes.append({
                                "user": parts[0],
                                "pid": parts[1],
                                "cpu": parts[2],
                                "mem": parts[3],
                                "command": parts[10]
                            })
            
            return {
                "command": "ps aux",
                "success": result["success"],
                "processes": processes,
                "process_count": len(processes),
                "error": result["stderr"]
            }
            
        except Exception as e:
            raise ToolError(
                f"Failed to list processes: {e}",
                tool_name="shell_ps",
                tool_args={}
            )
    
    def get_working_directory(self) -> str:
        """Get the current working directory."""
        return self.working_directory
    
    def set_working_directory(self, directory: str) -> None:
        """Set the working directory (with validation)."""
        safe_path = self.security_validator.validate_file_path(directory, "access")
        self.working_directory = safe_path
    
    async def cleanup(self) -> None:
        """Clean up shell tools resources."""
        # No persistent resources to clean up for shell tools
        self.logger.debug("Shell tools cleanup completed")