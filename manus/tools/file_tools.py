"""
Secure file system tools for the Manus agent.

This module provides production-ready file operations with comprehensive
security validation, atomic operations, and proper error handling.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..core.exceptions import ToolError
from ..security.validator import SecurityValidator
from ..utils.logger import get_logger


class FileTools:
    """
    Secure file system operations with comprehensive validation.
    
    All file operations go through security validation and implement
    atomic operations where possible to prevent data corruption.
    """
    
    def __init__(self, security_validator: SecurityValidator):
        self.security_validator = security_validator
        self.logger = get_logger(__name__)
        
        # Ensure safe directories exist
        for base_path in self.security_validator.ALLOWED_BASE_PATHS:
            try:
                Path(base_path).mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                # Directory may not be accessible, that's okay
                pass
    
    def file_read(self, path: str, encoding: str = "utf-8") -> str:
        """
        Read the contents of a file.
        
        Args:
            path: Path to the file to read
            encoding: File encoding (default: utf-8)
            
        Returns:
            File contents as string
            
        Raises:
            ToolError: If file cannot be read
        """
        try:
            # Validate path
            safe_path = self.security_validator.validate_file_path(path, "read")
            
            file_path = Path(safe_path)
            if not file_path.exists():
                raise ToolError(
                    f"File does not exist: {path}",
                    tool_name="file_read",
                    tool_args={"path": path}
                )
            
            if not file_path.is_file():
                raise ToolError(
                    f"Path is not a file: {path}",
                    tool_name="file_read", 
                    tool_args={"path": path}
                )
            
            # Check file size
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > self.security_validator.config.max_file_size_mb:
                raise ToolError(
                    f"File too large: {size_mb:.1f}MB (max: {self.security_validator.config.max_file_size_mb}MB)",
                    tool_name="file_read",
                    tool_args={"path": path}
                )
            
            # Read file content
            content = file_path.read_text(encoding=encoding)
            
            self.logger.debug(f"Read file: {safe_path} ({len(content)} chars)")
            return content
            
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Failed to read file: {e}",
                tool_name="file_read",
                tool_args={"path": path, "encoding": encoding}
            )
    
    def file_write(
        self, 
        path: str, 
        content: str, 
        encoding: str = "utf-8",
        backup: bool = True
    ) -> str:
        """
        Write content to a file using atomic operations.
        
        Args:
            path: Path to the file to write
            content: Content to write
            encoding: File encoding (default: utf-8)
            backup: Create backup if file exists (default: True)
            
        Returns:
            Success message with file info
            
        Raises:
            ToolError: If file cannot be written
        """
        try:
            # Validate path and content
            safe_path = self.security_validator.validate_file_path(path, "write")
            
            if len(content.encode(encoding)) > self.security_validator.config.max_file_size_mb * 1024 * 1024:
                raise ToolError(
                    f"Content too large (max: {self.security_validator.config.max_file_size_mb}MB)",
                    tool_name="file_write",
                    tool_args={"path": path}
                )
            
            file_path = Path(safe_path)
            
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup if file exists
            backup_path = None
            if backup and file_path.exists():
                backup_path = file_path.with_suffix(file_path.suffix + '.backup')
                shutil.copy2(file_path, backup_path)
                self.logger.debug(f"Created backup: {backup_path}")
            
            # Atomic write using temporary file
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding=encoding,
                dir=file_path.parent,
                delete=False,
                prefix=f".{file_path.name}.",
                suffix=".tmp"
            ) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name
            
            # Atomic move
            shutil.move(temp_path, file_path)
            
            # Get file info
            stat = file_path.stat()
            size_kb = stat.st_size / 1024
            
            result = f"Successfully wrote {len(content)} characters ({size_kb:.1f}KB) to {path}"
            if backup_path:
                result += f" (backup created: {backup_path.name})"
            
            self.logger.debug(f"Wrote file: {safe_path}")
            return result
            
        except Exception as e:
            # Clean up temp file if it exists
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                    
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Failed to write file: {e}",
                tool_name="file_write",
                tool_args={"path": path, "content_length": len(content)}
            )
    
    def file_append(self, path: str, content: str, encoding: str = "utf-8") -> str:
        """
        Append content to a file.
        
        Args:
            path: Path to the file to append to
            content: Content to append
            encoding: File encoding (default: utf-8)
            
        Returns:
            Success message
            
        Raises:
            ToolError: If file cannot be appended to
        """
        try:
            # Validate path
            safe_path = self.security_validator.validate_file_path(path, "write")
            file_path = Path(safe_path)
            
            # Create file if it doesn't exist
            if not file_path.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.touch()
            
            # Check total size after append
            current_size = file_path.stat().st_size if file_path.exists() else 0
            new_content_size = len(content.encode(encoding))
            total_size_mb = (current_size + new_content_size) / (1024 * 1024)
            
            if total_size_mb > self.security_validator.config.max_file_size_mb:
                raise ToolError(
                    f"File would exceed size limit after append: {total_size_mb:.1f}MB",
                    tool_name="file_append",
                    tool_args={"path": path}
                )
            
            # Append content
            with open(file_path, 'a', encoding=encoding) as f:
                f.write(content)
            
            self.logger.debug(f"Appended to file: {safe_path}")
            return f"Successfully appended {len(content)} characters to {path}"
            
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Failed to append to file: {e}",
                tool_name="file_append",
                tool_args={"path": path, "content_length": len(content)}
            )
    
    def file_delete(self, path: str, confirm: bool = False) -> str:
        """
        Delete a file with safety checks.
        
        Args:
            path: Path to the file to delete
            confirm: Confirmation flag to prevent accidental deletion
            
        Returns:
            Success message
            
        Raises:
            ToolError: If file cannot be deleted
        """
        try:
            if not confirm:
                raise ToolError(
                    "File deletion requires explicit confirmation (confirm=True)",
                    tool_name="file_delete",
                    tool_args={"path": path}
                )
            
            # Validate path
            safe_path = self.security_validator.validate_file_path(path, "delete")
            file_path = Path(safe_path)
            
            if not file_path.exists():
                return f"File does not exist: {path}"
            
            if not file_path.is_file():
                raise ToolError(
                    f"Path is not a file: {path}",
                    tool_name="file_delete",
                    tool_args={"path": path}
                )
            
            # Get file info before deletion
            size_kb = file_path.stat().st_size / 1024
            
            # Delete file
            file_path.unlink()
            
            self.logger.debug(f"Deleted file: {safe_path}")
            return f"Successfully deleted {path} ({size_kb:.1f}KB)"
            
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Failed to delete file: {e}",
                tool_name="file_delete",
                tool_args={"path": path}
            )
    
    def file_copy(self, source: str, destination: str, overwrite: bool = False) -> str:
        """
        Copy a file to another location.
        
        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Allow overwriting existing files
            
        Returns:
            Success message
            
        Raises:
            ToolError: If file cannot be copied
        """
        try:
            # Validate paths
            safe_source = self.security_validator.validate_file_path(source, "read")
            safe_dest = self.security_validator.validate_file_path(destination, "write")
            
            source_path = Path(safe_source)
            dest_path = Path(safe_dest)
            
            if not source_path.exists():
                raise ToolError(
                    f"Source file does not exist: {source}",
                    tool_name="file_copy",
                    tool_args={"source": source, "destination": destination}
                )
            
            if not source_path.is_file():
                raise ToolError(
                    f"Source is not a file: {source}",
                    tool_name="file_copy",
                    tool_args={"source": source, "destination": destination}
                )
            
            if dest_path.exists() and not overwrite:
                raise ToolError(
                    f"Destination exists and overwrite=False: {destination}",
                    tool_name="file_copy",
                    tool_args={"source": source, "destination": destination}
                )
            
            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file with metadata
            shutil.copy2(source_path, dest_path)
            
            # Get file info
            size_kb = dest_path.stat().st_size / 1024
            
            self.logger.debug(f"Copied file: {safe_source} -> {safe_dest}")
            return f"Successfully copied {source} to {destination} ({size_kb:.1f}KB)"
            
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Failed to copy file: {e}",
                tool_name="file_copy",
                tool_args={"source": source, "destination": destination}
            )
    
    def file_move(self, source: str, destination: str, overwrite: bool = False) -> str:
        """
        Move a file to another location.
        
        Args:
            source: Source file path
            destination: Destination file path  
            overwrite: Allow overwriting existing files
            
        Returns:
            Success message
            
        Raises:
            ToolError: If file cannot be moved
        """
        try:
            # First copy the file
            copy_result = self.file_copy(source, destination, overwrite)
            
            # Then delete the original
            self.file_delete(source, confirm=True)
            
            self.logger.debug(f"Moved file: {source} -> {destination}")
            return f"Successfully moved {source} to {destination}"
            
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Failed to move file: {e}",
                tool_name="file_move",
                tool_args={"source": source, "destination": destination}
            )
    
    def file_list(self, directory: str, pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List files in a directory.
        
        Args:
            directory: Directory path to list
            pattern: Optional filename pattern (glob style)
            
        Returns:
            List of file information dictionaries
            
        Raises:
            ToolError: If directory cannot be listed
        """
        try:
            # Validate path
            safe_path = self.security_validator.validate_file_path(directory, "read")
            dir_path = Path(safe_path)
            
            if not dir_path.exists():
                raise ToolError(
                    f"Directory does not exist: {directory}",
                    tool_name="file_list",
                    tool_args={"directory": directory}
                )
            
            if not dir_path.is_dir():
                raise ToolError(
                    f"Path is not a directory: {directory}",
                    tool_name="file_list",
                    tool_args={"directory": directory}
                )
            
            # Get file list
            if pattern:
                files = dir_path.glob(pattern)
            else:
                files = dir_path.iterdir()
            
            file_list = []
            for file_path in sorted(files):
                try:
                    stat = file_path.stat()
                    file_info = {
                        "name": file_path.name,
                        "path": str(file_path),
                        "type": "directory" if file_path.is_dir() else "file",
                        "size": stat.st_size,
                        "size_kb": stat.st_size / 1024,
                        "modified": stat.st_mtime,
                        "permissions": oct(stat.st_mode)[-3:],
                    }
                    file_list.append(file_info)
                except (OSError, PermissionError):
                    # Skip files we can't access
                    continue
            
            self.logger.debug(f"Listed directory: {safe_path} ({len(file_list)} items)")
            return file_list
            
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Failed to list directory: {e}",
                tool_name="file_list",
                tool_args={"directory": directory, "pattern": pattern}
            )
    
    def file_info(self, path: str) -> Dict[str, Any]:
        """
        Get detailed information about a file or directory.
        
        Args:
            path: Path to examine
            
        Returns:
            Dictionary with file information
            
        Raises:
            ToolError: If path cannot be examined
        """
        try:
            # Validate path
            safe_path = self.security_validator.validate_file_path(path, "read")
            file_path = Path(safe_path)
            
            if not file_path.exists():
                raise ToolError(
                    f"Path does not exist: {path}",
                    tool_name="file_info",
                    tool_args={"path": path}
                )
            
            stat = file_path.stat()
            
            info = {
                "path": str(file_path),
                "name": file_path.name,
                "type": "directory" if file_path.is_dir() else "file",
                "size": stat.st_size,
                "size_kb": stat.st_size / 1024,
                "size_mb": stat.st_size / (1024 * 1024),
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime,
                "permissions": oct(stat.st_mode)[-3:],
                "owner_readable": os.access(file_path, os.R_OK),
                "owner_writable": os.access(file_path, os.W_OK),
                "owner_executable": os.access(file_path, os.X_OK),
            }
            
            # Add file-specific info
            if file_path.is_file():
                info["extension"] = file_path.suffix
                info["stem"] = file_path.stem
                
                # Try to detect encoding for text files
                if file_path.suffix in {'.txt', '.py', '.js', '.html', '.css', '.md', '.json', '.yaml', '.yml'}:
                    try:
                        with open(file_path, 'rb') as f:
                            sample = f.read(1024)
                        try:
                            sample.decode('utf-8')
                            info["encoding"] = "utf-8"
                        except UnicodeDecodeError:
                            info["encoding"] = "binary"
                    except Exception:
                        info["encoding"] = "unknown"
            
            # Add directory-specific info
            elif file_path.is_dir():
                try:
                    child_count = len(list(file_path.iterdir()))
                    info["child_count"] = child_count
                except PermissionError:
                    info["child_count"] = "permission_denied"
            
            self.logger.debug(f"Got file info: {safe_path}")
            return info
            
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Failed to get file info: {e}",
                tool_name="file_info",
                tool_args={"path": path}
            )
    
    def directory_create(self, path: str, parents: bool = True) -> str:
        """
        Create a directory.
        
        Args:
            path: Directory path to create
            parents: Create parent directories if needed
            
        Returns:
            Success message
            
        Raises:
            ToolError: If directory cannot be created
        """
        try:
            # Validate path
            safe_path = self.security_validator.validate_file_path(path, "write")
            dir_path = Path(safe_path)
            
            if dir_path.exists():
                if dir_path.is_dir():
                    return f"Directory already exists: {path}"
                else:
                    raise ToolError(
                        f"Path exists but is not a directory: {path}",
                        tool_name="directory_create",
                        tool_args={"path": path}
                    )
            
            # Create directory
            dir_path.mkdir(parents=parents, exist_ok=True)
            
            self.logger.debug(f"Created directory: {safe_path}")
            return f"Successfully created directory: {path}"
            
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Failed to create directory: {e}",
                tool_name="directory_create",
                tool_args={"path": path, "parents": parents}
            )