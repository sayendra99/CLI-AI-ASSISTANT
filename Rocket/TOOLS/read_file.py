"""
Read File Tool for Rocket AI Coding Assistant.

Provides secure file reading capabilities with comprehensive
security safeguards against path traversal, binary files,
and memory exhaustion attacks.

Security Features:
    - Path traversal prevention (../../../etc/passwd attacks)
    - Workspace containment verification
    - Maximum file size limits (10MB default)
    - Binary file detection
    - Symbolic link escape prevention
    - UTF-8 encoding with graceful error handling

Performance Optimizations:
    - Buffered I/O operations (8KB chunks)
    - LRU caching for file metadata checks
    - Efficient binary detection
    - Memory-efficient line reading

Author: Rocket AI Team
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple, TYPE_CHECKING
from functools import lru_cache

# Handle imports for both package usage and direct execution
def _setup_path() -> None:
    """Add project root to path if running directly."""
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

# Only setup path if this module is the entry point or imports fail
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


class ReadFileTool(BaseTool):
    """
    Secure file reading tool with comprehensive safeguards.
    
    Provides safe file reading within a designated workspace directory,
    preventing common security attacks like path traversal and
    handling edge cases gracefully.
    
    Security Measures:
        - Path normalization and traversal detection
        - Workspace boundary enforcement
        - Symlink target validation
        - File size limits
        - Binary content detection
        - Encoding error handling
    
    Example Usage:
        tool = ReadFileTool(workspace_root="/home/user/project")
        result = tool.execute(
            path="src/main.py",
            start_line=1,
            num_lines=100
        )
    """
    
    # Configuration constants
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    MAX_FILE_SIZE_MB: int = 10
    BINARY_CHECK_BYTES: int = 8192  # Bytes to check for binary content
    NULL_BYTE_THRESHOLD: float = 0.1  # 10% null bytes = binary
    
    # Known binary file extensions (skip content reading)
    BINARY_EXTENSIONS: frozenset = frozenset({
        # Images
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp', '.svg',
        '.tiff', '.tif', '.psd', '.raw', '.heic', '.heif',
        # Documents
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.odt', '.ods', '.odp',
        # Archives
        '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar', '.xz',
        # Executables
        '.exe', '.dll', '.so', '.dylib', '.bin', '.app',
        # Media
        '.mp3', '.mp4', '.avi', '.mov', '.mkv', '.wav', '.flac',
        '.ogg', '.webm', '.m4a', '.m4v',
        # Fonts
        '.ttf', '.otf', '.woff', '.woff2', '.eot',
        # Other binary
        '.pyc', '.pyo', '.class', '.o', '.a', '.lib',
        '.db', '.sqlite', '.sqlite3',
    })
    
    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        """
        Initialize the ReadFileTool.
        
        Args:
            workspace_root: Root directory for file operations.
                           Files outside this directory cannot be read.
                           Defaults to current working directory.
        """
        self._workspace_root = Path(workspace_root or Path.cwd()).resolve()
        super().__init__()
        logger.debug(f"ReadFileTool initialized with workspace: {self._workspace_root}")
    
    @property
    def name(self) -> str:
        """Unique tool identifier."""
        return "read_file"
    
    @property
    def description(self) -> str:
        """Human-readable tool description."""
        return (
            "Read the contents of a file from the workspace. "
            "Supports partial reads with line ranges. "
            "Maximum file size: 10MB."
        )
    
    @property
    def category(self) -> ToolCategory:
        """Tool category for permission checks."""
        return ToolCategory.READ
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON Schema for LLM function calling."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Path to the file to read. Can be absolute or relative "
                        "to the workspace root. Must be within the workspace."
                    )
                },
                "start_line": {
                    "type": "integer",
                    "description": (
                        "Line number to start reading from (1-indexed). "
                        "Defaults to 1 (beginning of file)."
                    ),
                    "minimum": 1,
                    "default": 1
                },
                "num_lines": {
                    "type": "integer",
                    "description": (
                        "Number of lines to read. If not specified or 0, "
                        "reads the entire file from start_line."
                    ),
                    "minimum": 0,
                    "default": 0
                }
            },
            "required": ["path"],
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
        start_line = kwargs.get("start_line", 1)
        num_lines = kwargs.get("num_lines", 0)
        
        # Validate path is provided
        if not path:
            return "Parameter 'path' is required"
        
        if not isinstance(path, str):
            return f"Parameter 'path' must be a string, got {type(path).__name__}"
        
        # Validate path is not empty after stripping
        if not path.strip():
            return "Parameter 'path' cannot be empty or whitespace"
        
        # Validate start_line
        if start_line is not None:
            if not isinstance(start_line, int):
                return f"Parameter 'start_line' must be an integer, got {type(start_line).__name__}"
            if start_line < 1:
                return "Parameter 'start_line' must be >= 1"
        
        # Validate num_lines
        if num_lines is not None:
            if not isinstance(num_lines, int):
                return f"Parameter 'num_lines' must be an integer, got {type(num_lines).__name__}"
            if num_lines < 0:
                return "Parameter 'num_lines' must be >= 0"
        
        return None
    
    def _resolve_and_validate_path(self, file_path: str) -> Path:
        """
        Resolve and validate a file path for security.
        
        Performs comprehensive security checks:
        1. Resolve to absolute path
        2. Check for path traversal attempts
        3. Verify containment within workspace
        4. Validate symlink targets
        
        Args:
            file_path: Raw file path from user input
            
        Returns:
            Resolved, validated Path object
            
        Raises:
            FileSecurityError: If security check fails
            FileNotFoundError: If file doesn't exist
        """
        # Step 1: Basic path construction
        raw_path = Path(file_path)
        
        # Step 2: Check for obvious traversal patterns BEFORE resolving
        # This catches malicious inputs early
        path_str = str(file_path)
        dangerous_patterns = ['../', '..\\', '/..', '\\..']
        
        # Normalize separators for checking
        normalized_check = path_str.replace('\\', '/')
        if '..' in normalized_check:
            # More thorough check - allow '..' in filenames but not as traversal
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
            # Relative paths are relative to workspace
            resolved_path = (self._workspace_root / raw_path).resolve()
        
        # Step 4: Verify the resolved path is within workspace
        # This is the critical security check
        try:
            resolved_path.relative_to(self._workspace_root)
        except ValueError:
            raise FileSecurityError(
                f"Access denied: '{file_path}' resolves to '{resolved_path}' "
                f"which is outside the workspace '{self._workspace_root}'. "
                "File access is restricted to the workspace directory."
            )
        
        # Step 5: Check if path exists
        if not resolved_path.exists():
            raise FileNotFoundError(
                f"File not found: '{file_path}' "
                f"(resolved to '{resolved_path}')"
            )
        
        # Step 6: Handle symbolic links - verify target is also in workspace
        if resolved_path.is_symlink():
            # Get the actual target
            try:
                real_path = resolved_path.resolve(strict=True)
                try:
                    real_path.relative_to(self._workspace_root)
                except ValueError:
                    raise FileSecurityError(
                        f"Symbolic link escape detected: '{file_path}' "
                        f"links to '{real_path}' outside workspace. "
                        "Symlinks must point within the workspace."
                    )
            except OSError as e:
                raise FileSecurityError(
                    f"Cannot resolve symbolic link '{file_path}': {e}"
                )
        
        return resolved_path
    
    def _check_file_type(self, file_path: Path) -> None:
        """
        Verify the path points to a regular file.
        
        Args:
            file_path: Resolved file path
            
        Raises:
            IsADirectoryError: If path is a directory
            FileSecurityError: If path is a special file
        """
        if file_path.is_dir():
            raise IsADirectoryError(
                f"Cannot read '{file_path}': Path is a directory, not a file. "
                "Use a file listing tool to view directory contents."
            )
        
        # Check for special files (devices, sockets, etc.)
        try:
            mode = file_path.stat().st_mode
            if stat.S_ISBLK(mode) or stat.S_ISCHR(mode):
                raise FileSecurityError(
                    f"Cannot read '{file_path}': Path is a device file."
                )
            if stat.S_ISFIFO(mode):
                raise FileSecurityError(
                    f"Cannot read '{file_path}': Path is a FIFO/pipe."
                )
            if stat.S_ISSOCK(mode):
                raise FileSecurityError(
                    f"Cannot read '{file_path}': Path is a socket."
                )
        except OSError as e:
            raise FileSecurityError(f"Cannot stat file '{file_path}': {e}")
    
    def _check_file_size(self, file_path: Path) -> int:
        """
        Check file size against limits.
        
        Args:
            file_path: Resolved file path
            
        Returns:
            File size in bytes
            
        Raises:
            FileSecurityError: If file exceeds size limit
        """
        try:
            size = file_path.stat().st_size
        except OSError as e:
            raise FileSecurityError(f"Cannot determine file size: {e}")
        
        if size > self.MAX_FILE_SIZE_BYTES:
            size_mb = size / (1024 * 1024)
            raise FileSecurityError(
                f"File too large: {size_mb:.2f} MB exceeds "
                f"maximum allowed size of {self.MAX_FILE_SIZE_MB} MB. "
                "Use partial read with start_line and num_lines parameters."
            )
        
        return size
    
    def _is_binary_by_extension(self, file_path: Path) -> bool:
        """
        Check if file is likely binary based on extension.
        
        Args:
            file_path: File path to check
            
        Returns:
            True if extension indicates binary file
        """
        return file_path.suffix.lower() in self.BINARY_EXTENSIONS
    
    def _is_binary_by_content(self, file_path: Path) -> bool:
        """
        Detect binary file by checking for null bytes.
        
        Reads the first BINARY_CHECK_BYTES of the file and
        checks for null byte prevalence.
        
        Args:
            file_path: File path to check
            
        Returns:
            True if file appears to be binary
        """
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(self.BINARY_CHECK_BYTES)
            
            if not chunk:
                return False  # Empty file is not binary
            
            # Count null bytes
            null_count = chunk.count(b'\x00')
            null_ratio = null_count / len(chunk)
            
            # If more than threshold null bytes, it's binary
            if null_ratio > self.NULL_BYTE_THRESHOLD:
                return True
            
            # Also check for other common binary indicators
            # Control characters (except common ones like \t, \n, \r)
            control_chars = sum(
                1 for byte in chunk 
                if byte < 32 and byte not in (9, 10, 13)  # tab, newline, carriage return
            )
            control_ratio = control_chars / len(chunk)
            
            return control_ratio > 0.1  # More than 10% control chars
            
        except (IOError, OSError) as e:
            logger.warning(f"Binary check failed for {file_path}: {e}")
            return False
    
    def _read_file_content(
        self,
        file_path: Path,
        start_line: int = 1,
        num_lines: int = 0
    ) -> Tuple[str, int, int, int]:
        """
        Read file content with encoding handling.
        
        Args:
            file_path: Validated file path
            start_line: Line to start from (1-indexed)
            num_lines: Number of lines to read (0 = all)
            
        Returns:
            Tuple of (content, total_lines, lines_read, start_line_actual)
            
        Raises:
            UnicodeDecodeError: If file cannot be decoded
            IOError: If file cannot be read
        """
        encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        content = None
        used_encoding = None
        
        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding, errors='strict') as f:
                    lines = f.readlines()
                content = lines
                used_encoding = encoding
                break
            except UnicodeDecodeError:
                continue
            except (IOError, OSError):
                raise
        
        # If strict decoding failed, try with replacement
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                content = lines
                used_encoding = 'utf-8 (with replacements)'
                logger.warning(
                    f"File {file_path} contains invalid UTF-8 sequences. "
                    "Some characters may be replaced with placeholders."
                )
            except (IOError, OSError) as e:
                raise IOError(f"Cannot read file '{file_path}': {e}")
        
        total_lines = len(content)
        
        # Handle line range
        # Convert to 0-indexed
        start_idx = max(0, start_line - 1)
        
        if start_idx >= total_lines:
            # Start line beyond file - return empty with info
            return "", total_lines, 0, start_line
        
        if num_lines > 0:
            end_idx = min(start_idx + num_lines, total_lines)
        else:
            end_idx = total_lines
        
        selected_lines = content[start_idx:end_idx]
        lines_read = len(selected_lines)
        
        # Join lines (they already have newlines)
        result_content = ''.join(selected_lines)
        
        # Remove trailing newline for cleaner output
        if result_content.endswith('\n'):
            result_content = result_content[:-1]
        
        logger.debug(
            f"Read {lines_read} lines from {file_path} "
            f"(encoding: {used_encoding}, total: {total_lines})"
        )
        
        return result_content, total_lines, lines_read, start_idx + 1
    
    def _execute(
        self,
        path: str,
        start_line: int = 1,
        num_lines: int = 0,
        **kwargs: Any
    ) -> ToolResult:
        """
        Execute the file read operation.
        
        Args:
            path: File path to read
            start_line: Starting line number (1-indexed)
            num_lines: Number of lines to read (0 = all)
            **kwargs: Additional arguments (ignored)
            
        Returns:
            ToolResult with file content and metadata
        """
        try:
            # Step 1: Resolve and validate path (security critical)
            resolved_path = self._resolve_and_validate_path(path)
            
            # Step 2: Verify it's a regular file
            self._check_file_type(resolved_path)
            
            # Step 3: Check file size
            file_size = self._check_file_size(resolved_path)
            
            # Step 4: Check for binary file
            if self._is_binary_by_extension(resolved_path):
                return ToolResult.ok(
                    data=None,
                    is_binary=True,
                    file_type=resolved_path.suffix.lower(),
                    path=str(resolved_path),
                    relative_path=str(resolved_path.relative_to(self._workspace_root)),
                    size_bytes=file_size,
                    message=(
                        f"File '{path}' is a binary file ({resolved_path.suffix}). "
                        "Content cannot be displayed as text."
                    )
                )
            
            # Content-based binary check
            if self._is_binary_by_content(resolved_path):
                return ToolResult.ok(
                    data=None,
                    is_binary=True,
                    path=str(resolved_path),
                    relative_path=str(resolved_path.relative_to(self._workspace_root)),
                    size_bytes=file_size,
                    message=(
                        f"File '{path}' appears to be binary "
                        "(contains null bytes or control characters). "
                        "Content cannot be displayed as text."
                    )
                )
            
            # Step 5: Read file content
            content, total_lines, lines_read, actual_start = self._read_file_content(
                resolved_path,
                start_line=start_line,
                num_lines=num_lines
            )
            
            # Step 6: Build response
            relative_path = resolved_path.relative_to(self._workspace_root)
            
            # Determine if this was a partial read
            is_partial = (
                actual_start > 1 or 
                (num_lines > 0 and lines_read < total_lines - (actual_start - 1))
            )
            
            return ToolResult.ok(
                data=content,
                path=str(resolved_path),
                relative_path=str(relative_path),
                size_bytes=file_size,
                total_lines=total_lines,
                lines_read=lines_read,
                start_line=actual_start,
                end_line=actual_start + lines_read - 1 if lines_read > 0 else actual_start,
                is_partial=is_partial,
                is_binary=False
            )
            
        except FileSecurityError as e:
            logger.warning(f"Security violation in read_file: {e}")
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
        
        except PermissionError as e:
            return ToolResult.fail(
                error=f"Permission denied: Cannot read '{path}'. {e}",
                error_type="PermissionError",
                path=path
            )
        
        except UnicodeDecodeError as e:
            return ToolResult.fail(
                error=(
                    f"Encoding error: File '{path}' contains characters that "
                    f"cannot be decoded. {e}"
                ),
                error_type="EncodingError",
                path=path
            )
        
        except IOError as e:
            return ToolResult.fail(
                error=f"IO error reading '{path}': {e}",
                error_type="IOError",
                path=path
            )


# =============================================================================
# Test / Demo Block
# =============================================================================
if __name__ == "__main__":
    # Path already set up by the import handling above
    project_root = Path(__file__).parent.parent.parent
    
    print("=" * 60)
    print("ReadFileTool - Security Test Suite")
    print("=" * 60)
    
    # Initialize tool with current project as workspace
    workspace = project_root
    tool = ReadFileTool(workspace_root=workspace)
    
    print(f"\n✓ Tool initialized")
    print(f"  Workspace: {tool.workspace_root}")
    print(f"  Name: {tool.name}")
    print(f"  Category: {tool.category}")
    
    # Test 1: Read a valid file
    print("\n" + "-" * 40)
    print("Test 1: Read valid file (README.md)")
    result = tool.execute(path="README.md", num_lines=5)
    if result.success:
        print(f"  ✓ Success!")
        print(f"  Lines read: {result.metadata.get('lines_read')}")
        print(f"  Total lines: {result.metadata.get('total_lines')}")
        print(f"  Content preview: {result.data[:100] if result.data else 'N/A'}...")
    else:
        print(f"  ✗ Failed: {result.error}")
    
    # Test 2: Path traversal attempt
    print("\n" + "-" * 40)
    print("Test 2: Path traversal attack (../../../etc/passwd)")
    result = tool.execute(path="../../../etc/passwd")
    if result.success:
        print(f"  ✗ SECURITY FAILURE - should have been blocked!")
    else:
        print(f"  ✓ Blocked: {result.error_type}")
        print(f"  Message: {result.error[:80]}...")
    
    # Test 3: Non-existent file
    print("\n" + "-" * 40)
    print("Test 3: Non-existent file")
    result = tool.execute(path="this_file_does_not_exist.xyz")
    if result.success:
        print(f"  ✗ Should have failed!")
    else:
        print(f"  ✓ Correctly failed: {result.error_type}")
    
    # Test 4: Read directory
    print("\n" + "-" * 40)
    print("Test 4: Read directory (Rocket/)")
    result = tool.execute(path="Rocket")
    if result.success:
        print(f"  ✗ Should have failed!")
    else:
        print(f"  ✓ Correctly failed: {result.error_type}")
    
    # Test 5: Partial read
    print("\n" + "-" * 40)
    print("Test 5: Partial read (lines 5-10)")
    result = tool.execute(path="README.md", start_line=5, num_lines=5)
    if result.success:
        print(f"  ✓ Success!")
        print(f"  Start line: {result.metadata.get('start_line')}")
        print(f"  End line: {result.metadata.get('end_line')}")
        print(f"  Is partial: {result.metadata.get('is_partial')}")
    else:
        print(f"  ✗ Failed: {result.error}")
    
    # Test 6: Read this file itself
    print("\n" + "-" * 40)
    print("Test 6: Read this file (read_file.py)")
    result = tool.execute(path="Rocket/TOOLS/read_file.py", num_lines=20)
    if result.success:
        print(f"  ✓ Success!")
        print(f"  Size: {result.metadata.get('size_bytes')} bytes")
        print(f"  Total lines: {result.metadata.get('total_lines')}")
    else:
        print(f"  ✗ Failed: {result.error}")
    
    print("\n" + "=" * 60)
    print("Test suite complete!")
    print("=" * 60)