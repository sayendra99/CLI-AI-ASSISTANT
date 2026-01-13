"""
Write File Tool for Rocket AI Coding Assistant.

Provides secure file writing capabilities with atomic writes,
diff generation, and comprehensive security safeguards.

Features:
    - Two write modes: Search/Replace and Full Write
    - Atomic writes (temp file + rename prevents corruption)
    - Unified diff generation for review
    - Optional backup creation
    - Path traversal prevention
    - Workspace containment verification

Author: Rocket AI Team
"""

from __future__ import annotations

import difflib
import os
import shutil
import stat
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple, Literal

# Handle imports for both package usage and direct execution
def _setup_path() -> None:
    """Add project root to path if running directly."""
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

try:
    from Rocket.TOOLS.Base import BaseTool, ToolCategory, ToolResult
    from Rocket.Utils.Log import get_logger
except ImportError:
    _setup_path()
    from Rocket.TOOLS.Base import BaseTool, ToolCategory, ToolResult
    from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)


class FileSecurityError(Exception):
    """Security violation during file operations."""
    pass


class WriteConflictError(Exception):
    """Write operation conflict (e.g., search text not found)."""
    pass


class WriteFileTool(BaseTool):
    """
    Secure file writing tool with atomic writes and diff generation.
    
    Provides safe file modification within a designated workspace directory,
    with two operation modes:
    
    Mode A - Search/Replace:
        Surgically replace the first occurrence of a text pattern.
        Fails if the pattern is not found (prevents blind writes).
    
    Mode B - Full Write:
        Complete file rewrite with new content.
        Creates new files if they don't exist.
    
    Safety Features:
        - Atomic writes: Uses temp file + rename to prevent corruption
        - Diff preview: Generates unified diff before writing
        - Optional backup: Keeps .backup copy of original
        - Path security: Same safeguards as ReadFileTool
    
    Example Usage:
        tool = WriteFileTool(workspace_root="/home/user/project")
        
        # Search/Replace mode
        result = tool.execute(
            path="src/main.py",
            mode="replace",
            old_text="def old_function():",
            new_text="def new_function():"
        )
        
        # Full write mode
        result = tool.execute(
            path="config.json",
            mode="full",
            content='{"key": "value"}'
        )
    """
    
    # Configuration constants
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    MAX_FILE_SIZE_MB: int = 10
    BACKUP_SUFFIX: str = ".backup"
    
    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        """
        Initialize the WriteFileTool.
        
        Args:
            workspace_root: Root directory for file operations.
                           Files outside this directory cannot be modified.
                           Defaults to current working directory.
        """
        self._workspace_root = Path(workspace_root or Path.cwd()).resolve()
        super().__init__()
        logger.debug(f"WriteFileTool initialized with workspace: {self._workspace_root}")
    
    @property
    def name(self) -> str:
        """Unique tool identifier."""
        return "write_file"
    
    @property
    def description(self) -> str:
        """Human-readable tool description."""
        return (
            "Write or modify a file in the workspace. "
            "Supports search/replace for surgical edits or full file writes. "
            "Uses atomic writes to prevent corruption. "
            "Generates diffs for review."
        )
    
    @property
    def category(self) -> ToolCategory:
        """Tool category for permission checks."""
        return ToolCategory.WRITE
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON Schema for LLM function calling."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Path to the file to write. Can be absolute or relative "
                        "to the workspace root. Must be within the workspace."
                    )
                },
                "mode": {
                    "type": "string",
                    "enum": ["replace", "full"],
                    "description": (
                        "Write mode: 'replace' for search/replace of first occurrence, "
                        "'full' for complete file rewrite."
                    )
                },
                "old_text": {
                    "type": "string",
                    "description": (
                        "Text to find and replace (required for 'replace' mode). "
                        "Must exist in the file exactly once or more."
                    )
                },
                "new_text": {
                    "type": "string",
                    "description": (
                        "Replacement text (required for 'replace' mode). "
                        "Replaces the first occurrence of old_text."
                    )
                },
                "content": {
                    "type": "string",
                    "description": (
                        "Full file content (required for 'full' mode). "
                        "Completely overwrites the file."
                    )
                },
                "create_backup": {
                    "type": "boolean",
                    "description": (
                        "If true, creates a .backup file before writing. "
                        "Defaults to false."
                    ),
                    "default": False
                },
                "create_if_missing": {
                    "type": "boolean",
                    "description": (
                        "If true, creates the file if it doesn't exist "
                        "(only valid for 'full' mode). Defaults to true."
                    ),
                    "default": True
                }
            },
            "required": ["path", "mode"],
            "additionalProperties": False
        }
    
    @property
    def workspace_root(self) -> Path:
        """Get the workspace root directory."""
        return self._workspace_root
    
    def set_workspace_root(self, path: Path) -> None:
        """
        Update the workspace root directory.
        
        Args:
            path: New workspace root path
            
        Raises:
            ValueError: If path doesn't exist or isn't a directory
        """
        resolved = Path(path).resolve()
        if not resolved.exists():
            raise ValueError(f"Workspace path does not exist: {path}")
        if not resolved.is_dir():
            raise ValueError(f"Workspace path is not a directory: {path}")
        
        self._workspace_root = resolved
        logger.info(f"Workspace root updated to: {self._workspace_root}")
    
    def validate_parameters(self, **kwargs: Any) -> Optional[str]:
        """
        Validate parameters before execution.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Error message if invalid, None if valid
        """
        path = kwargs.get("path")
        mode = kwargs.get("mode")
        old_text = kwargs.get("old_text")
        new_text = kwargs.get("new_text")
        content = kwargs.get("content")
        
        # Validate path
        if not path:
            return "Parameter 'path' is required"
        if not isinstance(path, str) or not path.strip():
            return "Parameter 'path' must be a non-empty string"
        
        # Validate mode
        if not mode:
            return "Parameter 'mode' is required"
        if mode not in ("replace", "full"):
            return f"Parameter 'mode' must be 'replace' or 'full', got '{mode}'"
        
        # Validate mode-specific parameters
        if mode == "replace":
            if old_text is None:
                return "Parameter 'old_text' is required for 'replace' mode"
            if not isinstance(old_text, str):
                return "Parameter 'old_text' must be a string"
            if not old_text:
                return "Parameter 'old_text' cannot be empty for 'replace' mode"
            if new_text is None:
                return "Parameter 'new_text' is required for 'replace' mode"
            if not isinstance(new_text, str):
                return "Parameter 'new_text' must be a string"
        
        elif mode == "full":
            if content is None:
                return "Parameter 'content' is required for 'full' mode"
            if not isinstance(content, str):
                return "Parameter 'content' must be a string"
        
        return None
    
    def _resolve_and_validate_path(
        self,
        file_path: str,
        must_exist: bool = True
    ) -> Path:
        """
        Resolve and validate a file path for security.
        
        Performs comprehensive security checks:
        1. Resolve to absolute path
        2. Check for path traversal attempts
        3. Verify containment within workspace
        4. Validate symlink targets
        
        Args:
            file_path: Raw file path from user input
            must_exist: Whether the file must already exist
            
        Returns:
            Resolved, validated Path object
            
        Raises:
            FileSecurityError: If security check fails
            FileNotFoundError: If file doesn't exist and must_exist=True
        """
        # Step 1: Basic path construction
        raw_path = Path(file_path)
        
        # Step 2: Check for obvious traversal patterns BEFORE resolving
        normalized_check = str(file_path).replace('\\', '/')
        if '..' in normalized_check:
            parts = normalized_check.split('/')
            for part in parts:
                if part == '..':
                    raise FileSecurityError(
                        f"Path traversal detected: '{file_path}'. "
                        "Directory traversal sequences (..) are not allowed."
                    )
        
        # Step 3: Resolve to absolute path
        if raw_path.is_absolute():
            resolved_path = raw_path.resolve()
        else:
            resolved_path = (self._workspace_root / raw_path).resolve()
        
        # Step 4: Verify the resolved path is within workspace
        try:
            resolved_path.relative_to(self._workspace_root)
        except ValueError:
            raise FileSecurityError(
                f"Access denied: '{file_path}' resolves to '{resolved_path}' "
                f"which is outside the workspace '{self._workspace_root}'. "
                "File access is restricted to the workspace directory."
            )
        
        # Step 5: Check existence if required
        if must_exist and not resolved_path.exists():
            raise FileNotFoundError(
                f"File not found: '{file_path}' "
                f"(resolved to '{resolved_path}')"
            )
        
        # Step 6: Handle symbolic links - verify target is also in workspace
        if resolved_path.exists() and resolved_path.is_symlink():
            try:
                real_path = resolved_path.resolve(strict=True)
                try:
                    real_path.relative_to(self._workspace_root)
                except ValueError:
                    raise FileSecurityError(
                        f"Symbolic link escape detected: '{file_path}' "
                        f"links to '{real_path}' outside workspace."
                    )
            except OSError as e:
                raise FileSecurityError(
                    f"Cannot resolve symbolic link '{file_path}': {e}"
                )
        
        # Step 7: Ensure parent directory exists
        parent_dir = resolved_path.parent
        if not parent_dir.exists():
            raise FileNotFoundError(
                f"Parent directory does not exist: '{parent_dir}'. "
                "Create the directory first or check the path."
            )
        
        return resolved_path
    
    def _check_file_type(self, file_path: Path) -> None:
        """
        Verify the path points to a regular file or doesn't exist.
        
        Args:
            file_path: Resolved file path
            
        Raises:
            IsADirectoryError: If path is a directory
            FileSecurityError: If path is a special file
        """
        if not file_path.exists():
            return  # OK - will be created
        
        if file_path.is_dir():
            raise IsADirectoryError(
                f"Cannot write to '{file_path}': Path is a directory."
            )
        
        # Check for special files
        try:
            mode = file_path.stat().st_mode
            if stat.S_ISBLK(mode) or stat.S_ISCHR(mode):
                raise FileSecurityError(
                    f"Cannot write to '{file_path}': Path is a device file."
                )
            if stat.S_ISFIFO(mode):
                raise FileSecurityError(
                    f"Cannot write to '{file_path}': Path is a FIFO/pipe."
                )
            if stat.S_ISSOCK(mode):
                raise FileSecurityError(
                    f"Cannot write to '{file_path}': Path is a socket."
                )
        except OSError as e:
            raise FileSecurityError(f"Cannot stat file '{file_path}': {e}")
    
    def _check_content_size(self, content: str) -> int:
        """
        Check content size against limits.
        
        Args:
            content: Content to be written
            
        Returns:
            Content size in bytes
            
        Raises:
            FileSecurityError: If content exceeds size limit
        """
        size = len(content.encode('utf-8'))
        
        if size > self.MAX_FILE_SIZE_BYTES:
            size_mb = size / (1024 * 1024)
            raise FileSecurityError(
                f"Content too large: {size_mb:.2f} MB exceeds "
                f"maximum allowed size of {self.MAX_FILE_SIZE_MB} MB."
            )
        
        return size
    
    def _read_existing_content(self, file_path: Path) -> Optional[str]:
        """
        Read existing file content for diff generation.
        
        Args:
            file_path: Path to read
            
        Returns:
            File content as string, or None if file doesn't exist
        """
        if not file_path.exists():
            return None
        
        encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings_to_try:
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        
        # Last resort: replace errors
        return file_path.read_text(encoding='utf-8', errors='replace')
    
    def _generate_diff(
        self,
        old_content: Optional[str],
        new_content: str,
        file_path: Path
    ) -> str:
        """
        Generate unified diff between old and new content.
        
        Args:
            old_content: Original file content (None if new file)
            new_content: New file content
            file_path: Path for diff header
            
        Returns:
            Unified diff string
        """
        # Get relative path for cleaner diff
        try:
            rel_path = file_path.relative_to(self._workspace_root)
        except ValueError:
            rel_path = file_path
        
        # Prepare lines for diff (handle empty content edge case)
        old_lines = (old_content or "").splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        # Ensure last lines have newlines for proper diff
        # Guard against empty lists
        if old_lines and not old_lines[-1].endswith('\n'):
            old_lines[-1] += '\n'
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'
        
        # Generate unified diff
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        diff_lines = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{rel_path}" if old_content else "/dev/null",
            tofile=f"b/{rel_path}",
            fromfiledate=timestamp if old_content else "",
            tofiledate=timestamp,
            lineterm='\n'
        ))
        
        if not diff_lines:
            return "(no changes)"
        
        return ''.join(diff_lines)
    
    def _create_backup(self, file_path: Path) -> Optional[Path]:
        """
        Create backup of existing file.
        
        Args:
            file_path: File to backup
            
        Returns:
            Path to backup file, or None if original doesn't exist
        """
        if not file_path.exists():
            return None
        
        backup_path = file_path.with_suffix(file_path.suffix + self.BACKUP_SUFFIX)
        
        # Remove old backup if exists
        if backup_path.exists():
            backup_path.unlink()
        
        shutil.copy2(file_path, backup_path)
        logger.debug(f"Created backup: {backup_path}")
        
        return backup_path
    
    def _atomic_write(
        self,
        file_path: Path,
        content: str,
        encoding: str = 'utf-8'
    ) -> None:
        """
        Write content to file atomically.
        
        Uses write-to-temp-then-rename pattern:
        1. Write content to temporary file in same directory
        2. Sync to disk (fsync)
        3. Atomic rename to target path
        
        This ensures no partial writes on crash/interrupt.
        
        IMPORTANT: Temp file is created in the same directory as target
        to ensure same-filesystem requirement for atomic rename.
        
        Args:
            file_path: Target file path
            content: Content to write
            encoding: Text encoding (default: utf-8)
            
        Raises:
            IOError: If write fails
        """
        # Create temp file in same directory (REQUIRED for atomic rename)
        # os.rename() is atomic only on same filesystem
        parent_dir = file_path.parent
        
        # Verify parent directory exists and is writable
        if not parent_dir.exists():
            raise IOError(f"Parent directory does not exist: {parent_dir}")
        if not os.access(parent_dir, os.W_OK):
            raise IOError(f"Parent directory is not writable: {parent_dir}")
        
        fd = None
        temp_path = None
        
        try:
            # Create temp file in SAME directory (critical for atomicity)
            fd, temp_path_str = tempfile.mkstemp(
                suffix='.tmp',
                prefix=f'.{file_path.name}.',
                dir=parent_dir  # Same directory = same filesystem
            )
            temp_path = Path(temp_path_str)
            
            # Verify same filesystem (belt and suspenders)
            if hasattr(os, 'stat'):
                try:
                    target_dev = parent_dir.stat().st_dev
                    temp_dev = temp_path.stat().st_dev
                    if target_dev != temp_dev:
                        raise IOError(
                            f"Temp file on different filesystem. "
                            f"Cannot guarantee atomic write."
                        )
                except OSError:
                    pass  # If stat fails, proceed anyway
            
            # Write content
            with os.fdopen(fd, 'w', encoding=encoding) as f:
                fd = None  # fdopen takes ownership of fd
                f.write(content)
                f.flush()
                os.fsync(f.fileno())  # Ensure written to disk
            
            # Set permissions (match original or use sensible default)
            if file_path.exists():
                original_mode = file_path.stat().st_mode
                os.chmod(temp_path, original_mode)
            else:
                os.chmod(temp_path, 0o644)  # rw-r--r--
            
            # Atomic rename
            # On POSIX: os.rename() is atomic on same filesystem
            # On Windows: os.replace() is closer to atomic (Python 3.3+)
            if sys.platform == 'win32':
                # Windows: use os.replace() for better atomicity
                # os.replace() will overwrite existing file atomically
                os.replace(temp_path, file_path)
            else:
                # POSIX: os.rename() is atomic on same filesystem
                os.rename(temp_path, file_path)
            
            temp_path = None  # Successfully moved
            
            # Optional: sync parent directory (ensures rename is persisted)
            # This is important for crash consistency on some filesystems
            try:
                dir_fd = os.open(str(parent_dir), os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except (OSError, AttributeError):
                # O_DIRECTORY not available on Windows, skip
                pass
            
            logger.debug(f"Atomic write completed: {file_path}")
            
        except Exception as e:
            # Clean up temp file on failure
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise IOError(f"Failed to write file '{file_path}': {e}") from e
    
    def _execute_replace(
        self,
        file_path: Path,
        old_text: str,
        new_text: str,
        create_backup: bool
    ) -> Tuple[str, str, str]:
        """
        Execute search/replace mode.
        
        Args:
            file_path: Target file path
            old_text: Text to find
            new_text: Replacement text
            create_backup: Whether to create backup
            
        Returns:
            Tuple of (new_content, diff, backup_path_or_empty)
            
        Raises:
            WriteConflictError: If old_text not found
            FileNotFoundError: If file doesn't exist
        """
        # Read existing content
        old_content = self._read_existing_content(file_path)
        
        if old_content is None:
            raise FileNotFoundError(
                f"Cannot use 'replace' mode on non-existent file: '{file_path}'. "
                "Use 'full' mode to create new files."
            )
        
        # Check if old_text exists
        if old_text not in old_content:
            raise WriteConflictError(
                f"Search text not found in file. "
                f"The text to replace does not exist in '{file_path}'.\n"
                f"Search text (first 100 chars): {old_text[:100]!r}"
            )
        
        # Count occurrences for info
        occurrence_count = old_content.count(old_text)
        
        # Replace first occurrence only
        new_content = old_content.replace(old_text, new_text, 1)
        
        # Generate diff
        diff = self._generate_diff(old_content, new_content, file_path)
        
        # Create backup if requested
        backup_path = ""
        if create_backup:
            bp = self._create_backup(file_path)
            if bp:
                backup_path = str(bp)
        
        # Atomic write with rollback on failure
        try:
            self._atomic_write(file_path, new_content)
        except Exception as e:
            # Rollback: restore from backup if available
            if backup_path and Path(backup_path).exists():
                try:
                    shutil.copy2(backup_path, file_path)
                    logger.warning(f"Write failed, restored from backup: {file_path}")
                except OSError as restore_err:
                    logger.error(f"Failed to restore backup: {restore_err}")
            raise
        
        return new_content, diff, backup_path, occurrence_count
    
    def _execute_full(
        self,
        file_path: Path,
        content: str,
        create_backup: bool,
        create_if_missing: bool
    ) -> Tuple[str, str, str, bool]:
        """
        Execute full write mode.
        
        Args:
            file_path: Target file path
            content: New file content
            create_backup: Whether to create backup
            create_if_missing: Whether to create new files
            
        Returns:
            Tuple of (content, diff, backup_path_or_empty, was_created)
            
        Raises:
            FileNotFoundError: If file doesn't exist and create_if_missing=False
        """
        # Read existing content
        old_content = self._read_existing_content(file_path)
        was_created = old_content is None
        
        if was_created and not create_if_missing:
            raise FileNotFoundError(
                f"File does not exist: '{file_path}'. "
                "Set create_if_missing=true to create new files."
            )
        
        # Generate diff
        diff = self._generate_diff(old_content, content, file_path)
        
        # Create backup if requested and file exists
        backup_path = ""
        if create_backup and not was_created:
            bp = self._create_backup(file_path)
            if bp:
                backup_path = str(bp)
        
        # Atomic write with rollback on failure
        try:
            self._atomic_write(file_path, content)
        except Exception as e:
            # Rollback: restore from backup if available
            if backup_path and Path(backup_path).exists():
                try:
                    shutil.copy2(backup_path, file_path)
                    logger.warning(f"Write failed, restored from backup: {file_path}")
                except OSError as restore_err:
                    logger.error(f"Failed to restore backup: {restore_err}")
            raise
        
        return content, diff, backup_path, was_created
    
    def _execute(
        self,
        path: str,
        mode: str,
        old_text: Optional[str] = None,
        new_text: Optional[str] = None,
        content: Optional[str] = None,
        create_backup: bool = False,
        create_if_missing: bool = True,
        **kwargs: Any
    ) -> ToolResult:
        """
        Execute the file write operation.
        
        Args:
            path: File path to write
            mode: Write mode ('replace' or 'full')
            old_text: Text to find (replace mode)
            new_text: Replacement text (replace mode)
            content: Full content (full mode)
            create_backup: Whether to create .backup file
            create_if_missing: Whether to create new files (full mode)
            **kwargs: Additional arguments (ignored)
            
        Returns:
            ToolResult with write results and diff
        """
        try:
            # Step 1: Resolve and validate path
            # For 'full' mode with create_if_missing, file doesn't need to exist
            must_exist = (mode == "replace") or not create_if_missing
            resolved_path = self._resolve_and_validate_path(path, must_exist=must_exist)
            
            # Step 2: Verify it's a regular file (or doesn't exist)
            self._check_file_type(resolved_path)
            
            # Step 3: Check content size
            if mode == "full":
                self._check_content_size(content)
            elif mode == "replace":
                # For replace, check the new_text isn't too large
                # (old file size + growth should be reasonable)
                existing = self._read_existing_content(resolved_path)
                if existing:
                    projected_size = len(existing) - len(old_text) + len(new_text)
                    if projected_size > self.MAX_FILE_SIZE_BYTES:
                        raise FileSecurityError(
                            f"Resulting file would exceed {self.MAX_FILE_SIZE_MB}MB limit."
                        )
            
            # Step 4: Execute based on mode
            relative_path = resolved_path.relative_to(self._workspace_root)
            
            if mode == "replace":
                new_content, diff, backup_path, occurrences = self._execute_replace(
                    resolved_path, old_text, new_text, create_backup
                )
                
                return ToolResult.ok(
                    data={
                        "diff": diff,
                        "occurrences_found": occurrences,
                        "occurrences_replaced": 1
                    },
                    path=str(resolved_path),
                    relative_path=str(relative_path),
                    mode="replace",
                    backup_path=backup_path if backup_path else None,
                    bytes_written=len(new_content.encode('utf-8')),
                    message=(
                        f"Successfully replaced text in '{relative_path}'. "
                        f"Found {occurrences} occurrence(s), replaced first one."
                    )
                )
            
            elif mode == "full":
                new_content, diff, backup_path, was_created = self._execute_full(
                    resolved_path, content, create_backup, create_if_missing
                )
                
                action = "Created" if was_created else "Updated"
                
                return ToolResult.ok(
                    data={
                        "diff": diff,
                        "was_created": was_created
                    },
                    path=str(resolved_path),
                    relative_path=str(relative_path),
                    mode="full",
                    backup_path=backup_path if backup_path else None,
                    bytes_written=len(new_content.encode('utf-8')),
                    lines_written=new_content.count('\n') + (1 if new_content else 0),
                    message=f"{action} file '{relative_path}'."
                )
        
        except FileSecurityError as e:
            logger.warning(f"Security violation in write_file: {e}")
            return ToolResult.fail(
                error=str(e),
                error_type="SecurityError",
                path=path
            )
        
        except FileNotFoundError as e:
            return ToolResult.fail(
                error=str(e),
                error_type="FileNotFoundError",
                path=path
            )
        
        except IsADirectoryError as e:
            return ToolResult.fail(
                error=str(e),
                error_type="IsADirectoryError",
                path=path
            )
        
        except WriteConflictError as e:
            return ToolResult.fail(
                error=str(e),
                error_type="WriteConflictError",
                path=path
            )
        
        except PermissionError as e:
            return ToolResult.fail(
                error=f"Permission denied: Cannot write to '{path}'. {e}",
                error_type="PermissionError",
                path=path
            )
        
        except IOError as e:
            return ToolResult.fail(
                error=f"IO error writing '{path}': {e}",
                error_type="IOError",
                path=path
            )


# =============================================================================
# Test / Demo Block
# =============================================================================
if __name__ == "__main__":
    import tempfile as tmp
    
    project_root = Path(__file__).parent.parent.parent
    
    print("=" * 60)
    print("WriteFileTool - Test Suite")
    print("=" * 60)
    
    # Create a temp directory for testing
    with tmp.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        tool = WriteFileTool(workspace_root=temp_path)
        
        print(f"\n✓ Tool initialized")
        print(f"  Workspace: {tool.workspace_root}")
        print(f"  Name: {tool.name}")
        print(f"  Category: {tool.category}")
        
        # Test 1: Create new file (full mode)
        print("\n" + "-" * 40)
        print("Test 1: Create new file (full mode)")
        result = tool.execute(
            path="test.txt",
            mode="full",
            content="Hello, World!\nThis is a test file.\n"
        )
        if result.success:
            print(f"  ✓ Success! Created file")
            print(f"  Bytes written: {result.metadata.get('bytes_written')}")
            print(f"  Diff:\n{result.data.get('diff')}")
        else:
            print(f"  ✗ Failed: {result.error}")
        
        # Test 2: Search/Replace
        print("\n" + "-" * 40)
        print("Test 2: Search/Replace mode")
        result = tool.execute(
            path="test.txt",
            mode="replace",
            old_text="World",
            new_text="Rocket"
        )
        if result.success:
            print(f"  ✓ Success!")
            print(f"  Occurrences found: {result.data.get('occurrences_found')}")
            print(f"  Diff:\n{result.data.get('diff')}")
        else:
            print(f"  ✗ Failed: {result.error}")
        
        # Verify content
        actual = (temp_path / "test.txt").read_text()
        expected = "Hello, Rocket!\nThis is a test file.\n"
        print(f"  Content matches expected: {actual == expected}")
        
        # Test 3: Replace with backup
        print("\n" + "-" * 40)
        print("Test 3: Replace with backup")
        result = tool.execute(
            path="test.txt",
            mode="replace",
            old_text="test file",
            new_text="production file",
            create_backup=True
        )
        if result.success:
            print(f"  ✓ Success!")
            print(f"  Backup path: {result.metadata.get('backup_path')}")
            backup_exists = Path(result.metadata.get('backup_path', '')).exists()
            print(f"  Backup exists: {backup_exists}")
        else:
            print(f"  ✗ Failed: {result.error}")
        
        # Test 4: Replace non-existent text (should fail)
        print("\n" + "-" * 40)
        print("Test 4: Replace non-existent text (should fail)")
        result = tool.execute(
            path="test.txt",
            mode="replace",
            old_text="NONEXISTENT_TEXT_12345",
            new_text="replacement"
        )
        if result.success:
            print(f"  ✗ Should have failed!")
        else:
            print(f"  ✓ Correctly failed: {result.error_type}")
        
        # Test 5: Path traversal attempt
        print("\n" + "-" * 40)
        print("Test 5: Path traversal attack")
        result = tool.execute(
            path="../../../etc/passwd",
            mode="full",
            content="malicious content"
        )
        if result.success:
            print(f"  ✗ SECURITY FAILURE!")
        else:
            print(f"  ✓ Blocked: {result.error_type}")
        
        # Test 6: Full overwrite existing
        print("\n" + "-" * 40)
        print("Test 6: Full overwrite existing file")
        result = tool.execute(
            path="test.txt",
            mode="full",
            content="Completely new content!\n"
        )
        if result.success:
            print(f"  ✓ Success!")
            print(f"  Was created: {result.data.get('was_created')}")
            print(f"  Diff:\n{result.data.get('diff')}")
        else:
            print(f"  ✗ Failed: {result.error}")
        
        # Test 7: Create in subdirectory
        print("\n" + "-" * 40)
        print("Test 7: Create file in subdirectory")
        subdir = temp_path / "src"
        subdir.mkdir()
        result = tool.execute(
            path="src/main.py",
            mode="full",
            content="#!/usr/bin/env python3\nprint('Hello')\n"
        )
        if result.success:
            print(f"  ✓ Success!")
            print(f"  Path: {result.metadata.get('relative_path')}")
        else:
            print(f"  ✗ Failed: {result.error}")
    
    print("\n" + "=" * 60)
    print("Test suite complete!")
    print("=" * 60)
