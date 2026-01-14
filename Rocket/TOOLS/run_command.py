"""
Run Command Tool for Rocket AI Coding Assistant.

Provides shell command execution capabilities for running
tests, linters, git commands, and other development tools.

Features:
    - Safe command parsing (prevents injection)
    - Working directory support
    - Timeout handling
    - Stdout/stderr capture
    - Exit code reporting

Security:
    - Uses shlex.split for safe command parsing
    - Does NOT use shell=True to prevent injection
    - Configurable timeout to prevent hangs

Author: Rocket AI Team
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

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


class RunCommandTool(BaseTool):
    """
    Shell command execution tool for development tasks.
    
    Executes shell commands safely with timeout protection
    and output capture. Useful for running tests, linters,
    build tools, git commands, etc.
    
    Security Features:
        - Safe command parsing with shlex.split
        - No shell=True (prevents shell injection)
        - Configurable timeout (default 30s)
    
    Example Usage:
        tool = RunCommandTool()
        
        # Run tests
        result = tool.execute(command="pytest -v")
        
        # Run with specific directory
        result = tool.execute(
            command="npm test",
            cwd="./frontend"
        )
        
        # Run with custom timeout
        result = tool.execute(
            command="long_running_script.py",
            timeout=120
        )
    """
    
    # Configuration constants
    DEFAULT_TIMEOUT: int = 30  # Default timeout in seconds
    MAX_OUTPUT_SIZE: int = 100000  # Max output size in characters (safety limit)
    
    def __init__(self) -> None:
        """Initialize the RunCommandTool."""
        super().__init__()
        logger.debug("RunCommandTool initialized")
    
    @property
    def name(self) -> str:
        """Unique tool identifier."""
        return "run_command"
    
    @property
    def description(self) -> str:
        """Human-readable tool description for LLM to understand."""
        return (
            "Execute shell commands for development tasks like running tests, "
            "linters, git commands, build tools, etc. "
            "Returns stdout, stderr, and exit code. "
            "Use 'cwd' to specify working directory. "
            "Default timeout is 30 seconds (configurable). "
            "Example commands: 'pytest -v', 'npm test', 'git status', 'python script.py'"
        )
    
    @property
    def category(self) -> ToolCategory:
        """Tool category for permission checks."""
        return ToolCategory.EXECUTE
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON Schema for LLM function calling."""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "Shell command to execute. Examples: 'pytest -v', "
                        "'npm test', 'git status', 'python script.py', 'ls -la'"
                    )
                },
                "cwd": {
                    "type": "string",
                    "description": (
                        "Working directory for command execution. "
                        "Defaults to current directory ('.'). "
                        "Can be absolute or relative path."
                    ),
                    "default": "."
                },
                "timeout": {
                    "type": "integer",
                    "description": (
                        "Maximum time in seconds to wait for command completion. "
                        "Defaults to 30 seconds. Use higher values for long-running "
                        "commands like builds or extensive test suites."
                    ),
                    "default": 30
                }
            },
            "required": ["command"]
        }
    
    def validate_parameters(self, **kwargs: Any) -> Optional[str]:
        """Validate parameters before execution."""
        command = kwargs.get("command")
        
        if not command:
            return "command parameter is required"
        
        if not isinstance(command, str):
            return f"command must be a string, got {type(command).__name__}"
        
        if not command.strip():
            return "command cannot be empty"
        
        cwd = kwargs.get("cwd", ".")
        if not isinstance(cwd, str):
            return f"cwd must be a string, got {type(cwd).__name__}"
        
        timeout = kwargs.get("timeout", self.DEFAULT_TIMEOUT)
        if not isinstance(timeout, (int, float)):
            return f"timeout must be a number, got {type(timeout).__name__}"
        if timeout <= 0:
            return "timeout must be positive"
        
        return None
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the shell command.
        
        Args:
            command: Shell command to execute
            cwd: Working directory (default: ".")
            timeout: Timeout in seconds (default: 30)
            
        Returns:
            ToolResult with command output or error
        """
        command_str = kwargs.get("command", "")
        cwd_str = kwargs.get("cwd", ".")
        timeout = kwargs.get("timeout", self.DEFAULT_TIMEOUT)
        
        # Resolve working directory
        try:
            cwd_path = Path(cwd_str).resolve()
        except Exception as e:
            return ToolResult.fail(
                error=f"Invalid working directory: {cwd_str} - {e}",
                error_type="ValueError"
            )
        
        # Validate working directory exists
        if not cwd_path.exists():
            return ToolResult.fail(
                error=f"Working directory does not exist: {cwd_path}",
                error_type="FileNotFoundError"
            )
        
        if not cwd_path.is_dir():
            return ToolResult.fail(
                error=f"Working directory is not a directory: {cwd_path}",
                error_type="NotADirectoryError"
            )
        
        # Parse command safely using shlex
        try:
            # Handle Windows-specific command parsing
            if sys.platform == "win32":
                # On Windows, shlex.split may not work well with some commands
                # Use a simpler split or keep the command as-is for subprocess
                args = self._parse_command_windows(command_str)
            else:
                args = shlex.split(command_str)
        except ValueError as e:
            return ToolResult.fail(
                error=f"Invalid command syntax: {e}",
                error_type="ValueError"
            )
        
        if not args:
            return ToolResult.fail(
                error="Command parsed to empty list",
                error_type="ValueError"
            )
        
        logger.info(f"Executing command: {args}")
        logger.debug(f"Working directory: {cwd_path}")
        logger.debug(f"Timeout: {timeout}s")
        
        # Execute command
        try:
            result = subprocess.run(
                args,
                cwd=str(cwd_path),
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False  # Security: never use shell=True
            )
            
            # Truncate output if too large
            stdout = result.stdout
            stderr = result.stderr
            
            if len(stdout) > self.MAX_OUTPUT_SIZE:
                stdout = stdout[:self.MAX_OUTPUT_SIZE] + "\n... (output truncated)"
            if len(stderr) > self.MAX_OUTPUT_SIZE:
                stderr = stderr[:self.MAX_OUTPUT_SIZE] + "\n... (output truncated)"
            
            # Determine success based on exit code
            success = result.returncode == 0
            
            return ToolResult(
                success=success,
                data={
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": result.returncode
                },
                error=f"Command exited with code {result.returncode}" if not success else None,
                error_type="CommandError" if not success else None,
                metadata={
                    "command": command_str,
                    "cwd": str(cwd_path)
                }
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult.fail(
                error=f"Command timed out after {timeout} seconds",
                error_type="TimeoutError",
                command=command_str,
                timeout=timeout
            )
        except FileNotFoundError as e:
            return ToolResult.fail(
                error=f"Command not found: {args[0]}",
                error_type="FileNotFoundError",
                command=command_str
            )
        except PermissionError as e:
            return ToolResult.fail(
                error=f"Permission denied: {e}",
                error_type="PermissionError",
                command=command_str
            )
        except OSError as e:
            return ToolResult.fail(
                error=f"OS error executing command: {e}",
                error_type="OSError",
                command=command_str
            )
    
    def _parse_command_windows(self, command_str: str) -> list:
        """
        Parse command string for Windows.
        
        Windows command parsing is different from POSIX.
        This handles common cases while maintaining security.
        
        Args:
            command_str: Command string to parse
            
        Returns:
            List of command arguments
        """
        # Try shlex first with posix=False for Windows compatibility
        try:
            return shlex.split(command_str, posix=False)
        except ValueError:
            # Fallback: simple split (less robust but safer than shell=True)
            return command_str.split()


# =============================================================================
# Module Self-Test
# =============================================================================

if __name__ == "__main__":
    """Run self-tests when executed directly."""
    import tempfile
    
    print("=" * 60)
    print("RunCommandTool Self-Test")
    print("=" * 60)
    
    tool = RunCommandTool()
    
    # Test 1: Simple echo command
    print("\n--- Test 1: Simple Echo Command ---")
    if sys.platform == "win32":
        result = tool.execute(command="cmd /c echo hello")
    else:
        result = tool.execute(command="echo hello")
    
    assert result.success, f"Failed: {result.error}"
    assert "hello" in result.data["stdout"].lower()
    print(f"  stdout: {result.data['stdout'].strip()}")
    print(f"  exit_code: {result.data['exit_code']}")
    print("✓ Simple echo command works")
    
    # Test 2: Command with arguments
    print("\n--- Test 2: Command with Arguments ---")
    if sys.platform == "win32":
        result = tool.execute(command="python --version")
    else:
        result = tool.execute(command="python3 --version")
    
    # Should succeed (Python is available if running this test)
    if result.success:
        print(f"  stdout: {result.data['stdout'].strip()}")
        print("✓ Command with arguments works")
    else:
        print(f"  Note: python3 not found, trying python")
        result = tool.execute(command="python --version")
        if result.success:
            print(f"  stdout: {result.data['stdout'].strip()}")
            print("✓ Command with arguments works")
    
    # Test 3: Working directory
    print("\n--- Test 3: Working Directory ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        if sys.platform == "win32":
            result = tool.execute(command="cmd /c cd", cwd=tmpdir)
        else:
            result = tool.execute(command="pwd", cwd=tmpdir)
        
        if result.success:
            print(f"  Working dir output: {result.data['stdout'].strip()}")
            print("✓ Working directory works")
    
    # Test 4: Failed command
    print("\n--- Test 4: Failed Command (non-zero exit) ---")
    if sys.platform == "win32":
        result = tool.execute(command="cmd /c exit 1")
    else:
        result = tool.execute(command="false")
    
    assert not result.success
    assert result.data["exit_code"] != 0
    print(f"  exit_code: {result.data['exit_code']}")
    print("✓ Failed command correctly detected")
    
    # Test 5: Command not found
    print("\n--- Test 5: Command Not Found ---")
    result = tool.execute(command="nonexistent_command_xyz123")
    assert not result.success
    assert "not found" in result.error.lower() or "FileNotFoundError" in result.error_type
    print(f"✓ Correctly handled command not found: {result.error}")
    
    # Test 6: Invalid working directory
    print("\n--- Test 6: Invalid Working Directory ---")
    result = tool.execute(command="echo test", cwd="/nonexistent/path")
    assert not result.success
    assert "does not exist" in result.error
    print(f"✓ Correctly handled invalid cwd: {result.error}")
    
    # Test 7: Schema generation
    print("\n--- Test 7: Schema Generation ---")
    schema = tool.to_gemini_schema()
    assert "name" in schema
    assert schema["name"] == "run_command"
    assert "parameters" in schema
    print(f"✓ Schema generated: {schema['name']}")
    
    print("\n" + "=" * 60)
    print("All RunCommandTool tests passed! ✓")
    print("=" * 60)
