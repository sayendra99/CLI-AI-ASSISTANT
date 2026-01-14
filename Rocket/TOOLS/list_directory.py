"""
List Directory Tool for Rocket AI Coding Assistant.

Provides directory listing capabilities to explore codebase
structure. Supports both flat and recursive directory traversal.

Features:
    - List immediate children or recursive traversal
    - Returns file/directory info (name, size, type)
    - Cross-platform compatibility via pathlib
    - Safety limits to prevent huge outputs

Author: Rocket AI Team
"""

from __future__ import annotations

import os
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


class ListDirectoryTool(BaseTool):
    """
    Directory listing tool for exploring codebase structure.
    
    Lists files and directories with their metadata, supporting
    both flat listing of immediate children and recursive
    directory tree traversal.
    
    Safety Features:
        - Maximum 500 items limit to prevent huge outputs
        - Permission error handling
        - Path validation
    
    Example Usage:
        tool = ListDirectoryTool()
        
        # List immediate children
        result = tool.execute(path="./src")
        
        # Recursive listing
        result = tool.execute(path="./src", recursive=True)
    """
    
    # Configuration constants
    MAX_ITEMS: int = 500  # Maximum items to return (safety limit)
    
    def __init__(self) -> None:
        """Initialize the ListDirectoryTool."""
        super().__init__()
        logger.debug("ListDirectoryTool initialized")
    
    @property
    def name(self) -> str:
        """Unique tool identifier."""
        return "list_directory"
    
    @property
    def description(self) -> str:
        """Human-readable tool description for LLM to understand."""
        return (
            "List files and directories at a given path. "
            "Returns name, size (in bytes), and type (file/directory) for each item. "
            "Use recursive=True to traverse the entire directory tree. "
            "Limited to 500 items maximum to prevent huge outputs."
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
                        "Directory path to list. Can be absolute or relative "
                        "to the current working directory."
                    )
                },
                "recursive": {
                    "type": "boolean",
                    "description": (
                        "If True, recursively list all files and directories "
                        "in the directory tree. If False (default), only list "
                        "immediate children."
                    ),
                    "default": False
                }
            },
            "required": ["path"]
        }
    
    def validate_parameters(self, **kwargs: Any) -> Optional[str]:
        """Validate parameters before execution."""
        path = kwargs.get("path")
        
        if not path:
            return "path parameter is required"
        
        if not isinstance(path, str):
            return f"path must be a string, got {type(path).__name__}"
        
        recursive = kwargs.get("recursive", False)
        if not isinstance(recursive, bool):
            return f"recursive must be a boolean, got {type(recursive).__name__}"
        
        return None
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the directory listing.
        
        Args:
            path: Directory path to list
            recursive: Whether to list recursively (default: False)
            
        Returns:
            ToolResult with directory listing or error
        """
        path_str = kwargs.get("path", ".")
        recursive = kwargs.get("recursive", False)
        
        # Resolve the path
        try:
            dir_path = Path(path_str).resolve()
        except Exception as e:
            return ToolResult.fail(
                error=f"Invalid path: {path_str} - {e}",
                error_type="ValueError"
            )
        
        # Validate path exists
        if not dir_path.exists():
            return ToolResult.fail(
                error=f"Path does not exist: {dir_path}",
                error_type="FileNotFoundError"
            )
        
        # Validate path is a directory
        if not dir_path.is_dir():
            return ToolResult.fail(
                error=f"Path is not a directory: {dir_path}",
                error_type="NotADirectoryError"
            )
        
        # Collect items
        items: List[Dict[str, Any]] = []
        truncated = False
        
        try:
            if recursive:
                # Recursive listing using os.walk
                items, truncated = self._list_recursive(dir_path)
            else:
                # Flat listing of immediate children
                items, truncated = self._list_flat(dir_path)
        except PermissionError as e:
            return ToolResult.fail(
                error=f"Permission denied: {e}",
                error_type="PermissionError"
            )
        except OSError as e:
            return ToolResult.fail(
                error=f"OS error while listing directory: {e}",
                error_type="OSError"
            )
        
        return ToolResult.ok(
            data={
                "path": str(dir_path),
                "count": len(items),
                "items": items,
                "truncated": truncated
            },
            recursive=recursive
        )
    
    def _list_flat(self, dir_path: Path) -> tuple[List[Dict[str, Any]], bool]:
        """
        List immediate children of a directory.
        
        Args:
            dir_path: Directory path to list
            
        Returns:
            Tuple of (items list, truncated flag)
        """
        items: List[Dict[str, Any]] = []
        truncated = False
        
        try:
            for entry in sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if len(items) >= self.MAX_ITEMS:
                    truncated = True
                    break
                
                item_info = self._get_item_info(entry)
                if item_info:
                    items.append(item_info)
        except PermissionError:
            raise  # Re-raise to be handled by caller
        
        return items, truncated
    
    def _list_recursive(self, dir_path: Path) -> tuple[List[Dict[str, Any]], bool]:
        """
        Recursively list all files and directories.
        
        Args:
            dir_path: Root directory path
            
        Returns:
            Tuple of (items list, truncated flag)
        """
        items: List[Dict[str, Any]] = []
        truncated = False
        
        try:
            for root, dirs, files in os.walk(dir_path):
                root_path = Path(root)
                
                # Sort directories and files
                dirs.sort(key=str.lower)
                files.sort(key=str.lower)
                
                # Add directories
                for dir_name in dirs:
                    if len(items) >= self.MAX_ITEMS:
                        truncated = True
                        break
                    
                    item_path = root_path / dir_name
                    item_info = self._get_item_info(item_path)
                    if item_info:
                        # Add relative path from root
                        try:
                            item_info["path"] = str(item_path.relative_to(dir_path))
                        except ValueError:
                            item_info["path"] = str(item_path)
                        items.append(item_info)
                
                if truncated:
                    break
                
                # Add files
                for file_name in files:
                    if len(items) >= self.MAX_ITEMS:
                        truncated = True
                        break
                    
                    item_path = root_path / file_name
                    item_info = self._get_item_info(item_path)
                    if item_info:
                        # Add relative path from root
                        try:
                            item_info["path"] = str(item_path.relative_to(dir_path))
                        except ValueError:
                            item_info["path"] = str(item_path)
                        items.append(item_info)
                
                if truncated:
                    break
                    
        except PermissionError:
            raise  # Re-raise to be handled by caller
        
        return items, truncated
    
    def _get_item_info(self, item_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get information about a file or directory.
        
        Args:
            item_path: Path to the item
            
        Returns:
            Dictionary with item info or None if inaccessible
        """
        try:
            is_dir = item_path.is_dir()
            
            # Get size (0 for directories)
            if is_dir:
                size = 0
            else:
                try:
                    size = item_path.stat().st_size
                except (OSError, PermissionError):
                    size = 0
            
            return {
                "name": item_path.name,
                "size": size,
                "type": "directory" if is_dir else "file"
            }
            
        except (OSError, PermissionError) as e:
            logger.debug(f"Could not access {item_path}: {e}")
            return None


# =============================================================================
# Module Self-Test
# =============================================================================

if __name__ == "__main__":
    """Run self-tests when executed directly."""
    import tempfile
    
    print("=" * 60)
    print("ListDirectoryTool Self-Test")
    print("=" * 60)
    
    # Create test directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create test structure
        (tmp_path / "file1.txt").write_text("Hello")
        (tmp_path / "file2.py").write_text("print('test')")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "nested.txt").write_text("Nested file")
        
        tool = ListDirectoryTool()
        
        # Test 1: Flat listing
        print("\n--- Test 1: Flat Listing ---")
        result = tool.execute(path=str(tmp_path))
        assert result.success, f"Failed: {result.error}"
        print(f"  Found {result.data['count']} items")
        for item in result.data['items']:
            print(f"    - {item['name']} ({item['type']}, {item['size']} bytes)")
        print("✓ Flat listing works")
        
        # Test 2: Recursive listing
        print("\n--- Test 2: Recursive Listing ---")
        result = tool.execute(path=str(tmp_path), recursive=True)
        assert result.success, f"Failed: {result.error}"
        print(f"  Found {result.data['count']} items")
        for item in result.data['items']:
            path_info = item.get('path', item['name'])
            print(f"    - {path_info} ({item['type']})")
        print("✓ Recursive listing works")
        
        # Test 3: Non-existent path
        print("\n--- Test 3: Non-existent Path ---")
        result = tool.execute(path="/nonexistent/path")
        assert not result.success
        assert "does not exist" in result.error
        print(f"✓ Correctly handled non-existent path: {result.error}")
        
        # Test 4: File instead of directory
        print("\n--- Test 4: File Path ---")
        result = tool.execute(path=str(tmp_path / "file1.txt"))
        assert not result.success
        assert "not a directory" in result.error
        print(f"✓ Correctly handled file path: {result.error}")
        
        # Test 5: Schema generation
        print("\n--- Test 5: Schema Generation ---")
        schema = tool.to_gemini_schema()
        assert "name" in schema
        assert schema["name"] == "list_directory"
        assert "parameters" in schema
        print(f"✓ Schema generated: {schema['name']}")
    
    print("\n" + "=" * 60)
    print("All ListDirectoryTool tests passed! ✓")
    print("=" * 60)
