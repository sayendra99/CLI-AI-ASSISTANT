"""
Run Command Tool for Rocket AI Coding Assistant.

Provides secure shell command execution capabilities with
timeout support and output capture.

Features:
    - Safe command parsing (no shell injection)
    - Configurable timeout
    - Working directory support
    - Stdout/stderr capture
    - Exit code tracking

Security:
    - Uses shlex.split() for safe command parsing
    - Does NOT use shell=True (prevents injection attacks)
    - Timeout enforcement prevents hangs

Author: Rocket AI Team
"""

from __future__ import annotations

import os
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
    Secure shell command execution tool.
    
    Executes shell commands safely with timeout support and
    output capture. Uses safe command parsing to prevent
    shell injection attacks.
    
    Security Features:
        - Command parsing via shlex.split() (no shell expansion)
        - No shell=True (prevents injection)
        - Configurable timeout to prevent hangs
        - Working directory validation
    
    Use Cases:
        - Running tests (pytest, unittest)
        - Running linters (flake8, pylint, mypy)
        - Git commands (git status, git diff)
        - Build commands (make, npm build)
        - Any CLI tool invocation
    
    Example Usage:
        tool = RunCommandTool()
        result = tool.execute(
            command="pytest -v tests/",
            working_dir="./project",
            timeout=60
        )
    """
    
    # Configuration constants
    DEFAULT_TIMEOUT: int = 30  # Default timeout in seconds
    MAX_OUTPUT_SIZE: int = 100 * 1024  # 100KB max output
    
    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        """
        Initialize the RunCommandTool.
        
        Args:
            workspace_root: Root directory for operations.
                           Defaults to current working directory.
        """
        self._workspace_root = Path(workspace_root or Path.cwd()).resolve()
        super().__init__()
        logger.debug(f"RunCommandTool initialized with workspace: {self._workspace_root}")
    
    @property
    def name(self) -> str:
        """Unique tool identifier."""
        return "run_command"
    
    @property
    def description(self) -> str:
        """Human-readable tool description."""
        return (
            "Execute shell commands and capture output. "
            "Useful for running tests (pytest), linters (flake8, mypy), "
            "git commands, build tools, and any CLI operations. "
            "Returns stdout, stderr, and exit code. "
            "Commands are parsed safely to prevent injection attacks."
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
                        "Shell command to execute. Will be safely parsed. "
                        "Examples: 'pytest tests/', 'git status', 'python script.py'"
                    )
                },
                "working_dir": {
                    "type": "string",
                    "description": (
                        "Working directory for command execution. "
                        "Default is current directory ('.')."
                    ),
                    "default": "."
                },
                "timeout": {
                    "type": "integer",
                    "description": (
                        "Maximum time in seconds to wait for command completion. "
                        "Default is 30 seconds."
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
            return "Parameter 'command' is required"
        
        if not isinstance(command, str):
            return f"Parameter 'command' must be a string, got {type(command).__name__}"
        
        if not command.strip():
            return "Parameter 'command' cannot be empty"
        
        timeout = kwargs.get("timeout", self.DEFAULT_TIMEOUT)
        if not isinstance(timeout, (int, float)):
            return f"Parameter 'timeout' must be a number, got {type(timeout).__name__}"
        
        if timeout <= 0:
            return "Parameter 'timeout' must be positive"
        
        return None
    
    def _parse_command(self, command: str) -> list:
        """
        Safely parse a command string into arguments.
        
        Args:
            command: Command string to parse
            
        Returns:
            List of command arguments
            
        Raises:
            ValueError: If command cannot be parsed
        """
        try:
            # Use shlex.split for safe parsing
            # This handles quotes and escapes properly
            if sys.platform == 'win32':
                # On Windows, shlex doesn't handle all cases well
                # Use posix=False for better compatibility
                args = shlex.split(command, posix=False)
            else:
                args = shlex.split(command)
            
            return args
        except ValueError as e:
            raise ValueError(f"Failed to parse command: {e}")
    
    def _truncate_output(self, output: str) -> str:
        """
        Truncate output if it exceeds maximum size.
        
        Args:
            output: Output string to truncate
            
        Returns:
            Truncated output string
        """
        if len(output) > self.MAX_OUTPUT_SIZE:
            truncated = output[:self.MAX_OUTPUT_SIZE]
            return truncated + f"\n... [truncated, {len(output) - self.MAX_OUTPUT_SIZE} bytes omitted]"
        return output
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the shell command.
        
        Args:
            command: Shell command to execute
            working_dir: Working directory (default: ".")
            timeout: Timeout in seconds (default: 30)
            
        Returns:
            ToolResult with command output
        """
        command_str = kwargs.get("command", "")
        working_dir_str = kwargs.get("working_dir", ".")
        timeout = kwargs.get("timeout", self.DEFAULT_TIMEOUT)
        
        # Parse the command safely
        try:
            args = self._parse_command(command_str)
        except ValueError as e:
            return ToolResult.fail(
                error=f"Invalid command: {e}",
                error_type="CommandParseError"
            )
        
        if not args:
            return ToolResult.fail(
                error="Empty command after parsing",
                error_type="CommandParseError"
            )
        
        # Resolve working directory
        try:
            working_dir = Path(working_dir_str).resolve()
        except Exception as e:
            return ToolResult.fail(
                error=f"Invalid working directory: {working_dir_str} - {e}",
                error_type="InvalidPathError"
            )
        
        # Validate working directory exists
        if not working_dir.exists():
            return ToolResult.fail(
                error=f"Working directory does not exist: {working_dir}",
                error_type="FileNotFoundError"
            )
        
        if not working_dir.is_dir():
            return ToolResult.fail(
                error=f"Working directory is not a directory: {working_dir}",
                error_type="NotADirectoryError"
            )
        
        # Execute the command
        logger.info(f"Executing command: {args}")
        logger.debug(f"Working directory: {working_dir}")
        logger.debug(f"Timeout: {timeout}s")
        
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
                # Security: Do NOT use shell=True
                shell=False
            )
            
            stdout = self._truncate_output(result.stdout)
            stderr = self._truncate_output(result.stderr)
            
            # Success is based on exit code
            success = result.returncode == 0
            
            return ToolResult(
                success=success,
                data={
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": result.returncode
                },
                error=None if success else f"Command exited with code {result.returncode}",
                error_type=None if success else "CommandError"
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult.fail(
                error=f"Command timed out after {timeout} seconds",
                error_type="TimeoutError"
            )
        except FileNotFoundError as e:
            return ToolResult.fail(
                error=f"Command not found: {args[0]}",
                error_type="CommandNotFoundError"
            )
        except PermissionError as e:
            return ToolResult.fail(
                error=f"Permission denied executing command: {e}",
                error_type="PermissionError"
            )
        except OSError as e:
            return ToolResult.fail(
                error=f"OS error executing command: {e}",
                error_type="OSError"
            )


# =============================================================================
# Direct Execution Support
# =============================================================================

if __name__ == "__main__":
    # Allow running this file directly for testing
    import json
    
    tool = RunCommandTool()
    
    # Test 1: Simple echo command
    print("Test 1: Echo command")
    if sys.platform == 'win32':
        result = tool.execute(command="cmd /c echo hello world")
    else:
        result = tool.execute(command="echo hello world")
    print(f"Success: {result.success}")
    if result.success:
        print(f"stdout: {result.data['stdout'].strip()}")
        print(f"exit_code: {result.data['exit_code']}")
    else:
        print(f"Error: {result.error}")
    
    print()
    
    # Test 2: Python version
    print("Test 2: Python version")
    result = tool.execute(command="python --version")
    print(f"Success: {result.success}")
    if result.success or result.data:
        data = result.data
        output = data.get('stdout', '') + data.get('stderr', '')
        print(f"Output: {output.strip()}")
        print(f"exit_code: {data.get('exit_code', 'N/A')}")
    else:
        print(f"Error: {result.error}")
    
    print()
    
    # Test 3: Non-existent command
    print("Test 3: Non-existent command")
    result = tool.execute(command="nonexistent_command_12345")
    print(f"Success: {result.success}")
    print(f"Error: {result.error}")
