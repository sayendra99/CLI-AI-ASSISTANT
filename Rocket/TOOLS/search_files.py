"""
Search Files Tool for Rocket AI Coding Assistant.

Provides grep-like file searching capabilities with regex support
for finding text patterns across files in a directory.

Features:
    - Regex pattern matching (case-insensitive)
    - File pattern filtering (e.g., "*.py")
    - Recursive directory search
    - Binary file detection and skipping
    - Safety limits to prevent huge outputs

Author: Rocket AI Team
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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


class SearchFilesTool(BaseTool):
    """
    Grep-like file search tool with regex support.
    
    Provides powerful text search capabilities across files,
    supporting regex patterns and file filtering.
    
    Features:
        - Case-insensitive regex pattern matching
        - File pattern filtering (glob patterns like "*.py")
        - Recursive directory search
        - Automatic binary file skipping
        - Safety limit of 100 matches maximum
    
    Example Usage:
        tool = SearchFilesTool()
        result = tool.execute(
            pattern="def .*\\(self",
            path="./src",
            file_pattern="*.py"
        )
    """
    
    # Configuration constants
    MAX_MATCHES: int = 100  # Maximum number of matches to return
    MAX_LINE_LENGTH: int = 500  # Truncate long lines in output
    
    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        """
        Initialize the SearchFilesTool.
        
        Args:
            workspace_root: Root directory for operations.
                           Defaults to current working directory.
        """
        self._workspace_root = Path(workspace_root or Path.cwd()).resolve()
        super().__init__()
        logger.debug(f"SearchFilesTool initialized with workspace: {self._workspace_root}")
    
    @property
    def name(self) -> str:
        """Unique tool identifier."""
        return "search_files"
    
    @property
    def description(self) -> str:
        """Human-readable tool description."""
        return (
            "Search for text patterns in files using regex. "
            "Searches recursively through directories, returning matching lines "
            "with file paths and line numbers. "
            "Supports file pattern filtering (e.g., '*.py' for Python files). "
            "Case-insensitive matching. Useful for finding code, definitions, or references."
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
                "pattern": {
                    "type": "string",
                    "description": (
                        "Text or regex pattern to search for. "
                        "Supports Python regex syntax. Case-insensitive."
                    )
                },
                "path": {
                    "type": "string",
                    "description": (
                        "Directory path to search in. Searches recursively. "
                        "Default is current directory ('.')."
                    ),
                    "default": "."
                },
                "file_pattern": {
                    "type": "string",
                    "description": (
                        "Glob pattern to filter files (e.g., '*.py' for Python files, "
                        "'*.txt' for text files). Default is '*' (all files)."
                    ),
                    "default": "*"
                }
            },
            "required": ["pattern"]
        }
    
    def validate_parameters(self, **kwargs: Any) -> Optional[str]:
        """Validate parameters before execution."""
        pattern = kwargs.get("pattern")
        
        if not pattern:
            return "Parameter 'pattern' is required"
        
        if not isinstance(pattern, str):
            return f"Parameter 'pattern' must be a string, got {type(pattern).__name__}"
        
        # Validate regex pattern
        try:
            re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return f"Invalid regex pattern: {e}"
        
        return None
    
    def _search_file(
        self,
        file_path: Path,
        pattern: re.Pattern,
        base_path: Path
    ) -> List[Dict[str, Any]]:
        """
        Search a single file for pattern matches.
        
        Args:
            file_path: Path to the file to search
            pattern: Compiled regex pattern
            base_path: Base path for relative path calculation
            
        Returns:
            List of match dictionaries
        """
        matches = []
        
        try:
            # Calculate relative path for output
            try:
                rel_path = file_path.relative_to(base_path)
            except ValueError:
                rel_path = file_path
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, start=1):
                    if pattern.search(line):
                        # Truncate long lines
                        line_content = line.rstrip('\n\r')
                        if len(line_content) > self.MAX_LINE_LENGTH:
                            line_content = line_content[:self.MAX_LINE_LENGTH] + "..."
                        
                        matches.append({
                            "file": str(rel_path),
                            "line_number": line_num,
                            "line_content": line_content
                        })
                        
        except UnicodeDecodeError:
            # Binary file - skip silently
            logger.debug(f"Skipping binary file: {file_path}")
        except PermissionError:
            logger.warning(f"Permission denied reading: {file_path}")
        except OSError as e:
            logger.warning(f"Error reading {file_path}: {e}")
        
        return matches
    
    def _find_files(self, search_path: Path, file_pattern: str) -> List[Path]:
        """
        Find all files matching the pattern.
        
        Args:
            search_path: Directory to search
            file_pattern: Glob pattern for filtering
            
        Returns:
            List of matching file paths
        """
        files = []
        
        try:
            # Use rglob for recursive search
            for item in search_path.rglob(file_pattern):
                if item.is_file():
                    files.append(item)
        except PermissionError:
            logger.warning(f"Permission denied accessing: {search_path}")
        except OSError as e:
            logger.warning(f"Error accessing {search_path}: {e}")
        
        return sorted(files)
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the file search operation.
        
        Args:
            pattern: Text/regex pattern to search for
            path: Directory to search in (default: ".")
            file_pattern: File pattern filter (default: "*")
            
        Returns:
            ToolResult with search results
        """
        pattern_str = kwargs.get("pattern", "")
        path_str = kwargs.get("path", ".")
        file_pattern = kwargs.get("file_pattern", "*")
        
        # Compile the regex pattern
        try:
            pattern = re.compile(pattern_str, re.IGNORECASE)
        except re.error as e:
            return ToolResult.fail(
                error=f"Invalid regex pattern '{pattern_str}': {e}",
                error_type="RegexError"
            )
        
        # Resolve the search path
        try:
            search_path = Path(path_str).resolve()
        except Exception as e:
            return ToolResult.fail(
                error=f"Invalid path: {path_str} - {e}",
                error_type="InvalidPathError"
            )
        
        # Check if path exists
        if not search_path.exists():
            return ToolResult.fail(
                error=f"Path does not exist: {search_path}",
                error_type="FileNotFoundError"
            )
        
        # Ensure it's a directory
        if not search_path.is_dir():
            return ToolResult.fail(
                error=f"Path is not a directory: {search_path}",
                error_type="NotADirectoryError"
            )
        
        # Find files matching the pattern
        files = self._find_files(search_path, file_pattern)
        logger.debug(f"Found {len(files)} files matching '{file_pattern}'")
        
        # Search files
        all_matches = []
        files_searched = 0
        
        for file_path in files:
            matches = self._search_file(file_path, pattern, search_path)
            all_matches.extend(matches)
            files_searched += 1
            
            if len(all_matches) >= self.MAX_MATCHES:
                logger.warning(f"Hit max matches limit ({self.MAX_MATCHES})")
                all_matches = all_matches[:self.MAX_MATCHES]
                break
        
        return ToolResult.ok(
            data={
                "pattern": pattern_str,
                "matches": len(all_matches),
                "files_searched": files_searched,
                "results": all_matches,
                "truncated": len(all_matches) >= self.MAX_MATCHES
            }
        )


# =============================================================================
# Direct Execution Support
# =============================================================================

if __name__ == "__main__":
    # Allow running this file directly for testing
    import json
    
    tool = SearchFilesTool()
    
    # Test 1: Search for "def" in Python files
    print("Test 1: Search for 'def' in Python files")
    result = tool.execute(pattern="def ", path=".", file_pattern="*.py")
    print(f"Success: {result.success}")
    if result.success:
        print(f"Found {result.data['matches']} matches in {result.data['files_searched']} files")
        for match in result.data['results'][:5]:
            print(f"  {match['file']}:{match['line_number']}: {match['line_content'][:60]}...")
    else:
        print(f"Error: {result.error}")
    
    print()
    
    # Test 2: Search with regex
    print("Test 2: Search with regex pattern")
    result = tool.execute(pattern="class.*Tool", path=".", file_pattern="*.py")
    print(f"Success: {result.success}")
    if result.success:
        print(f"Found {result.data['matches']} matches")
        for match in result.data['results'][:5]:
            print(f"  {match['file']}:{match['line_number']}: {match['line_content'][:60]}...")
    else:
        print(f"Error: {result.error}")
