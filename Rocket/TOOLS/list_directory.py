"""
List Directory Tool for Rocket AI Coding Assistant.

Provides directory listing capabilities with support for
recursive traversal and file metadata collection.

Features:
    - List immediate children or recursive traversal
    - File size and type information
    - Cross-platform path handling
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
    Directory listing tool with recursive support.
    
    Provides safe directory listing within the filesystem,
    with optional recursive traversal and file metadata.
    
    Features:
        - List immediate children or full directory tree
        - Return file name, size, and type for each item
        - Safety limit of 500 items maximum
        - Cross-platform path handling via pathlib
    
    Example Usage:
        tool = ListDirectoryTool()
        result = tool.execute(
            path="./src",
            recursive=False
        )
    """
    
    # Configuration constants
    MAX_ITEMS: int = 500  # Maximum number of items to return
    
    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        """
        Initialize the ListDirectoryTool.
        
        Args:
            workspace_root: Root directory for operations.
                           Defaults to current working directory.
        """
        self._workspace_root = Path(workspace_root or Path.cwd()).resolve()
        super().__init__()
        logger.debug(f"ListDirectoryTool initialized with workspace: {self._workspace_root}")
    
    @property
    def name(self) -> str:
        """Unique tool identifier."""
        return "list_directory"
    
    @property
    def description(self) -> str:
        """Human-readable tool description."""
        return (
            "List files and directories in a specified path. "
            "Can list immediate children only or recursively traverse subdirectories. "
            "Returns name, size (in bytes), and type (file/directory) for each item. "
            "Useful for exploring project structure and finding files."
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
                        "Whether to list recursively. If False, only immediate "
                        "children are listed. If True, traverses all subdirectories. "
                        "Default is False."
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
            return "Parameter 'path' is required"
        
        if not isinstance(path, str):
            return f"Parameter 'path' must be a string, got {type(path).__name__}"
        
        recursive = kwargs.get("recursive", False)
        if not isinstance(recursive, bool):
            return f"Parameter 'recursive' must be a boolean, got {type(recursive).__name__}"
        
        return None
    
    def _get_item_info(self, item_path: Path) -> Dict[str, Any]:
        """
        Get information about a file or directory.
        
        Args:
            item_path: Path to the item
            
        Returns:
            Dictionary with name, size, and type
        """
        try:
            stat_info = item_path.stat()
            is_dir = item_path.is_dir()
            
            return {
                "name": item_path.name,
                "size": stat_info.st_size if not is_dir else 0,
                "type": "directory" if is_dir else "file"
            }
        except (PermissionError, OSError) as e:
            # Return basic info even if stat fails
            logger.warning(f"Could not stat {item_path}: {e}")
            return {
                "name": item_path.name,
                "size": 0,
                "type": "unknown"
            }
    
    def _list_immediate(self, dir_path: Path) -> List[Dict[str, Any]]:
        """
        List immediate children of a directory.
        
        Args:
            dir_path: Directory to list
            
        Returns:
            List of item info dictionaries
        """
        items = []
        
        try:
            for item in sorted(dir_path.iterdir()):
                items.append(self._get_item_info(item))
                
                if len(items) >= self.MAX_ITEMS:
                    logger.warning(f"Hit max items limit ({self.MAX_ITEMS})")
                    break
        except PermissionError as e:
            logger.error(f"Permission denied listing {dir_path}: {e}")
            raise
        
        return items
    
    def _list_recursive(self, dir_path: Path) -> List[Dict[str, Any]]:
        """
        Recursively list all items in a directory tree.
        
        Args:
            dir_path: Root directory to traverse
            
        Returns:
            List of item info dictionaries with relative paths
        """
        items = []
        
        try:
            for root, dirs, files in os.walk(dir_path):
                root_path = Path(root)
                
                # Sort for consistent output
                dirs.sort()
                files.sort()
                
                # Add directories
                for d in dirs:
                    item_path = root_path / d
                    rel_path = item_path.relative_to(dir_path)
                    info = self._get_item_info(item_path)
                    info["name"] = str(rel_path)
                    items.append(info)
                    
                    if len(items) >= self.MAX_ITEMS:
                        break
                
                # Add files
                for f in files:
                    item_path = root_path / f
                    rel_path = item_path.relative_to(dir_path)
                    info = self._get_item_info(item_path)
                    info["name"] = str(rel_path)
                    items.append(info)
                    
                    if len(items) >= self.MAX_ITEMS:
                        break
                
                if len(items) >= self.MAX_ITEMS:
                    logger.warning(f"Hit max items limit ({self.MAX_ITEMS})")
                    break
                    
        except PermissionError as e:
            logger.error(f"Permission denied during recursive walk: {e}")
            raise
        
        return items
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the list directory operation.
        
        Args:
            path: Directory path to list
            recursive: Whether to list recursively (default: False)
            
        Returns:
            ToolResult with directory listing
        """
        path_str = kwargs.get("path", "")
        recursive = kwargs.get("recursive", False)
        
        # Resolve the path
        try:
            dir_path = Path(path_str).resolve()
        except Exception as e:
            return ToolResult.fail(
                error=f"Invalid path: {path_str} - {e}",
                error_type="InvalidPathError"
            )
        
        # Check if path exists
        if not dir_path.exists():
            return ToolResult.fail(
                error=f"Path does not exist: {dir_path}",
                error_type="FileNotFoundError"
            )
        
        # Check if path is a directory
        if not dir_path.is_dir():
            return ToolResult.fail(
                error=f"Path is not a directory: {dir_path}",
                error_type="NotADirectoryError"
            )
        
        # List the directory
        try:
            if recursive:
                items = self._list_recursive(dir_path)
            else:
                items = self._list_immediate(dir_path)
            
            return ToolResult.ok(
                data={
                    "path": str(dir_path),
                    "count": len(items),
                    "items": items,
                    "truncated": len(items) >= self.MAX_ITEMS
                }
            )
            
        except PermissionError as e:
            return ToolResult.fail(
                error=f"Permission denied: {e}",
                error_type="PermissionError"
            )
        except OSError as e:
            return ToolResult.fail(
                error=f"OS error listing directory: {e}",
                error_type="OSError"
            )


# =============================================================================
# Direct Execution Support
# =============================================================================

if __name__ == "__main__":
    # Allow running this file directly for testing
    import json
    
    tool = ListDirectoryTool()
    
    # Test 1: List current directory
    print("Test 1: List current directory (non-recursive)")
    result = tool.execute(path=".")
    print(f"Success: {result.success}")
    if result.success:
        print(f"Found {result.data['count']} items")
        for item in result.data['items'][:10]:
            print(f"  {item['type']}: {item['name']} ({item['size']} bytes)")
    else:
        print(f"Error: {result.error}")
    
    print()
    
    # Test 2: List recursive
    print("Test 2: List current directory (recursive)")
    result = tool.execute(path=".", recursive=True)
    print(f"Success: {result.success}")
    if result.success:
        print(f"Found {result.data['count']} items")
        print(f"Truncated: {result.data['truncated']}")
    else:
        print(f"Error: {result.error}")
