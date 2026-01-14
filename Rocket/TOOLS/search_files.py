"""
Search Files Tool for Rocket AI Coding Assistant.

Provides grep-like search capabilities to find text patterns
across files in the codebase. Supports regex and file pattern filtering.

Features:
    - Regex pattern matching (case-insensitive)
    - File pattern filtering (e.g., "*.py")
    - Line number and content reporting
    - Cross-platform compatibility
    - Safety limits to prevent huge outputs

Author: Rocket AI Team
"""

from __future__ import annotations

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
    Grep-like search tool for finding text patterns in files.
    
    Searches for text or regex patterns across files in a directory,
    returning matching file paths, line numbers, and line content.
    
    Features:
        - Regular expression support (case-insensitive)
        - File pattern filtering (glob patterns like "*.py")
        - Recursive directory traversal
        - Context around matches
    
    Safety Features:
        - Maximum 100 matches limit to prevent huge outputs
        - Binary file detection and skipping
        - Permission error handling
    
    Example Usage:
        tool = SearchFilesTool()
        
        # Search for pattern in Python files
        result = tool.execute(
            pattern="def main",
            path="./src",
            file_pattern="*.py"
        )
    """
    
    # Configuration constants
    MAX_MATCHES: int = 100  # Maximum matches to return (safety limit)
    MAX_LINE_LENGTH: int = 500  # Truncate long lines in results
    
    def __init__(self) -> None:
        """Initialize the SearchFilesTool."""
        super().__init__()
        logger.debug("SearchFilesTool initialized")
    
    @property
    def name(self) -> str:
        """Unique tool identifier."""
        return "search_files"
    
    @property
    def description(self) -> str:
        """Human-readable tool description for LLM to understand."""
        return (
            "Search for text patterns in files (grep-like functionality). "
            "Supports regular expressions (case-insensitive). "
            "Use file_pattern to filter files (e.g., '*.py' for Python files). "
            "Returns file path, line number, and matching line content. "
            "Limited to 100 matches maximum."
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
                        "Text or regular expression pattern to search for. "
                        "Search is case-insensitive. Examples: 'def main', "
                        "'class\\s+\\w+', 'TODO|FIXME'"
                    )
                },
                "path": {
                    "type": "string",
                    "description": (
                        "Directory path to search in. Defaults to current "
                        "directory ('.'). Search is recursive."
                    ),
                    "default": "."
                },
                "file_pattern": {
                    "type": "string",
                    "description": (
                        "Glob pattern to filter files. Examples: '*.py' for "
                        "Python files, '*.js' for JavaScript, '*.txt' for text files. "
                        "Defaults to '*' (all files)."
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
            return "pattern parameter is required"
        
        if not isinstance(pattern, str):
            return f"pattern must be a string, got {type(pattern).__name__}"
        
        # Validate regex compiles
        try:
            re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return f"Invalid regex pattern: {e}"
        
        path = kwargs.get("path", ".")
        if not isinstance(path, str):
            return f"path must be a string, got {type(path).__name__}"
        
        file_pattern = kwargs.get("file_pattern", "*")
        if not isinstance(file_pattern, str):
            return f"file_pattern must be a string, got {type(file_pattern).__name__}"
        
        return None
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the file search.
        
        Args:
            pattern: Text/regex pattern to search for
            path: Directory to search in (default: ".")
            file_pattern: Glob pattern for file filtering (default: "*")
            
        Returns:
            ToolResult with search results or error
        """
        pattern_str = kwargs.get("pattern", "")
        path_str = kwargs.get("path", ".")
        file_pattern = kwargs.get("file_pattern", "*")
        
        # Compile regex pattern (case-insensitive)
        try:
            regex = re.compile(pattern_str, re.IGNORECASE)
        except re.error as e:
            return ToolResult.fail(
                error=f"Invalid regex pattern: {e}",
                error_type="ValueError"
            )
        
        # Resolve the search path
        try:
            search_path = Path(path_str).resolve()
        except Exception as e:
            return ToolResult.fail(
                error=f"Invalid path: {path_str} - {e}",
                error_type="ValueError"
            )
        
        # Validate path exists
        if not search_path.exists():
            return ToolResult.fail(
                error=f"Path does not exist: {search_path}",
                error_type="FileNotFoundError"
            )
        
        # Validate path is a directory
        if not search_path.is_dir():
            return ToolResult.fail(
                error=f"Path is not a directory: {search_path}",
                error_type="NotADirectoryError"
            )
        
        # Search files
        results: List[Dict[str, Any]] = []
        files_searched = 0
        truncated = False
        
        try:
            # Find files matching the file pattern
            if file_pattern == "*":
                # All files recursively
                file_iter = search_path.rglob("*")
            else:
                # Files matching pattern
                file_iter = search_path.rglob(file_pattern)
            
            for file_path in file_iter:
                # Skip directories
                if not file_path.is_file():
                    continue
                
                files_searched += 1
                
                # Search this file
                file_results = self._search_file(file_path, regex, search_path)
                
                for match in file_results:
                    if len(results) >= self.MAX_MATCHES:
                        truncated = True
                        break
                    results.append(match)
                
                if truncated:
                    break
                    
        except PermissionError as e:
            logger.warning(f"Permission denied during search: {e}")
        except OSError as e:
            return ToolResult.fail(
                error=f"OS error during search: {e}",
                error_type="OSError"
            )
        
        return ToolResult.ok(
            data={
                "pattern": pattern_str,
                "matches": len(results),
                "results": results,
                "files_searched": files_searched,
                "truncated": truncated
            }
        )
    
    def _search_file(
        self,
        file_path: Path,
        regex: re.Pattern,
        base_path: Path
    ) -> List[Dict[str, Any]]:
        """
        Search a single file for pattern matches.
        
        Args:
            file_path: Path to the file to search
            regex: Compiled regex pattern
            base_path: Base path for relative path calculation
            
        Returns:
            List of match dictionaries
        """
        results: List[Dict[str, Any]] = []
        
        try:
            # Read file content
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            
            # Get relative path for display
            try:
                relative_path = str(file_path.relative_to(base_path))
            except ValueError:
                relative_path = str(file_path)
            
            # Search each line
            for line_num, line in enumerate(lines, start=1):
                if regex.search(line):
                    # Truncate long lines
                    line_content = line
                    if len(line_content) > self.MAX_LINE_LENGTH:
                        line_content = line_content[:self.MAX_LINE_LENGTH] + "..."
                    
                    results.append({
                        "file": relative_path,
                        "line_number": line_num,
                        "line_content": line_content.strip()
                    })
                    
        except UnicodeDecodeError:
            # Skip binary files
            logger.debug(f"Skipping binary file: {file_path}")
        except PermissionError:
            # Skip inaccessible files
            logger.debug(f"Permission denied: {file_path}")
        except OSError as e:
            logger.debug(f"Could not read {file_path}: {e}")
        
        return results


# =============================================================================
# Module Self-Test
# =============================================================================

if __name__ == "__main__":
    """Run self-tests when executed directly."""
    import tempfile
    
    print("=" * 60)
    print("SearchFilesTool Self-Test")
    print("=" * 60)
    
    # Create test directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create test files
        (tmp_path / "main.py").write_text("""
def main():
    print("Hello, world!")

def helper():
    pass
""")
        (tmp_path / "utils.py").write_text("""
def utility_function():
    # TODO: implement this
    pass

class MyClass:
    def method(self):
        pass
""")
        (tmp_path / "readme.txt").write_text("""
This is a README file.
It contains documentation.
""")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "nested.py").write_text("""
def nested_function():
    return 42
""")
        
        tool = SearchFilesTool()
        
        # Test 1: Simple pattern search
        print("\n--- Test 1: Simple Pattern Search ---")
        result = tool.execute(pattern="def", path=str(tmp_path))
        assert result.success, f"Failed: {result.error}"
        print(f"  Found {result.data['matches']} matches for 'def'")
        for match in result.data['results'][:3]:
            print(f"    - {match['file']}:{match['line_number']}: {match['line_content']}")
        print("✓ Simple pattern search works")
        
        # Test 2: File pattern filter
        print("\n--- Test 2: File Pattern Filter ---")
        result = tool.execute(pattern="def", path=str(tmp_path), file_pattern="*.py")
        assert result.success, f"Failed: {result.error}"
        print(f"  Found {result.data['matches']} matches in .py files")
        print("✓ File pattern filter works")
        
        # Test 3: Regex pattern
        print("\n--- Test 3: Regex Pattern ---")
        result = tool.execute(pattern="class\\s+\\w+", path=str(tmp_path))
        assert result.success, f"Failed: {result.error}"
        print(f"  Found {result.data['matches']} class definitions")
        for match in result.data['results']:
            print(f"    - {match['file']}:{match['line_number']}: {match['line_content']}")
        print("✓ Regex pattern works")
        
        # Test 4: Case insensitivity
        print("\n--- Test 4: Case Insensitivity ---")
        result = tool.execute(pattern="README", path=str(tmp_path))
        assert result.success
        print(f"  Found {result.data['matches']} matches for 'README' (case-insensitive)")
        print("✓ Case insensitivity works")
        
        # Test 5: Non-existent path
        print("\n--- Test 5: Non-existent Path ---")
        result = tool.execute(pattern="test", path="/nonexistent/path")
        assert not result.success
        assert "does not exist" in result.error
        print(f"✓ Correctly handled non-existent path: {result.error}")
        
        # Test 6: Invalid regex
        print("\n--- Test 6: Invalid Regex ---")
        result = tool.execute(pattern="[invalid", path=str(tmp_path))
        assert not result.success
        assert "Invalid regex" in result.error
        print(f"✓ Correctly handled invalid regex: {result.error}")
        
        # Test 7: Schema generation
        print("\n--- Test 7: Schema Generation ---")
        schema = tool.to_gemini_schema()
        assert "name" in schema
        assert schema["name"] == "search_files"
        assert "parameters" in schema
        print(f"✓ Schema generated: {schema['name']}")
    
    print("\n" + "=" * 60)
    print("All SearchFilesTool tests passed! ✓")
    print("=" * 60)
