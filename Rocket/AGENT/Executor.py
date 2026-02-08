"""
Tool executor with mode-based permission checks.

Wraps tool execution to enforce mode restrictions.
Tracks all tool executions in context.

Performance Optimizations:
- LRU caching for tool registry lookups
- Cached permission checks
- Efficient tool resolution

Author: Rocket AI Team
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from functools import lru_cache

# Handle imports for both package and direct execution
try:
    from Rocket.TOOLS.Base import BaseTool, ToolResult, ToolCategory
    from Rocket.TOOLS.registry import get_registry, ToolRegistry
    from Rocket.AGENT.Context import ExecutionContext
    from Rocket.Utils.Log import get_logger
except ImportError:
    _project_root = Path(__file__).parent.parent.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))
    from Rocket.TOOLS.Base import BaseTool, ToolResult, ToolCategory
    from Rocket.TOOLS.registry import get_registry, ToolRegistry
    from Rocket.AGENT.Context import ExecutionContext
    from Rocket.Utils.Log import get_logger

if TYPE_CHECKING:
    from Rocket.MODES.Base import BaseMode

logger = get_logger(__name__)


# =============================================================================
# Exceptions
# =============================================================================

class ToolNotAllowedError(Exception):
    """
    Raised when attempting to use a tool not allowed by current mode.
    
    This is a security exception - permission denied situations should
    raise this error rather than returning a ToolResult.
    
    Attributes:
        tool_name: Name of the tool that was denied
        mode_name: Name of the mode that denied it
        allowed_tools: List of tools that are allowed
    """
    
    def __init__(
        self,
        tool_name: str,
        mode_name: str,
        allowed_tools: Optional[List[str]] = None,
    ):
        self.tool_name = tool_name
        self.mode_name = mode_name
        self.allowed_tools = allowed_tools or []
        
        message = (
            f"Tool '{tool_name}' is not allowed in {mode_name} mode. "
            f"Allowed tools: {', '.join(self.allowed_tools) or 'none'}"
        )
        super().__init__(message)


class ToolExecutionError(Exception):
    """Raised when tool execution fails unexpectedly."""
    pass


# =============================================================================
# Tool Executor
# =============================================================================

class ToolExecutor:
    """
    Tool executor with mode-based permission checks.
    
    Wraps tool execution to:
    - Enforce mode restrictions (READ mode can't use WRITE tools)
    - Track all tool executions in context
    - Handle file operation tracking
    
    Example:
        >>> from Rocket.MODES.Read_mode import ReadMode
        >>> mode = ReadMode()
        >>> context = ExecutionContext(user_prompt="...", mode_name="READ")
        >>> executor = ToolExecutor(mode=mode, context=context)
        >>> result = executor.execute("read_file", path="src/main.py")
    """
    
    def __init__(
        self,
        mode: "BaseMode",
        context: ExecutionContext,
        registry: Optional[ToolRegistry] = None,
    ) -> None:
        """
        Initialize the executor.
        
        Args:
            mode: The current operating mode (for permission checks)
            context: Execution context for tracking
            registry: Tool registry (uses global if not provided)
        """
        self._mode = mode
        self._context = context
        self._registry = registry or get_registry()
        
        logger.debug(
            f"ToolExecutor initialized for mode: {mode.config.name} "
            f"with {len(self._registry)} tools"
        )
    
    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------
    
    @property
    def mode(self) -> "BaseMode":
        """Get the current mode."""
        return self._mode
    
    @property
    def context(self) -> ExecutionContext:
        """Get the execution context."""
        return self._context
    
    @property
    def mode_name(self) -> str:
        """Get the current mode name."""
        return self._mode.config.name
    
    # -------------------------------------------------------------------------
    # Permission Checks
    # -------------------------------------------------------------------------
    
    @lru_cache(maxsize=128)
    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        Check if a tool is allowed by the current mode.
        
        Uses LRU cache to avoid repeated permission checks for same tool.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if tool is allowed
        """
        return self._mode.is_tool_allowed(tool_name)
    
    def check_permission(self, tool_name: str) -> None:
        """
        Check if a tool is allowed, raising if not.
        
        Args:
            tool_name: Name of the tool to check
            
        Raises:
            ToolNotAllowedError: If tool is not permitted
        """
        if not self.is_tool_allowed(tool_name):
            raise ToolNotAllowedError(
                tool_name=tool_name,
                mode_name=self.mode_name,
                allowed_tools=self._mode.get_allowed_tools()
            )
    
    # -------------------------------------------------------------------------
    # Tool Discovery
    # -------------------------------------------------------------------------
    
    @lru_cache(maxsize=1)
    def get_available_tools(self) -> List[BaseTool]:
        """
        Get tools available in the current mode.
        
        Cached to avoid repeated registry lookups.
        
        Returns:
            List of tools allowed by the current mode
        """
        available = []
        for tool in self._registry.list_all():
            if self.is_tool_allowed(tool.name):
                available.append(tool)
        
        logger.debug(f"Available tools for {self.mode_name}: {len(available)}")
        return available
    
    @lru_cache(maxsize=1)
    def get_available_tool_names(self) -> List[str]:
        """
        Get names of tools available in the current mode.
        
        Cached for performance.
        
        Returns:
            List of tool names allowed by current mode
        """
        return [tool.name for tool in self.get_available_tools()]
    
    @lru_cache(maxsize=64)
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool by name if it exists and is allowed.
        
        Cached to avoid repeated registry lookups.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool instance or None if not found/allowed
        """
        if not self.is_tool_allowed(tool_name):
            return None
        return self._registry.get(tool_name)
    
    # -------------------------------------------------------------------------
    # Schema Generation (for LLM)
    # -------------------------------------------------------------------------
    
    def get_tool_schemas(
        self,
        format: str = "openai",
        legacy: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get LLM function calling schemas for available tools.
        
        Only includes tools allowed by the current mode.
        
        Args:
            format: Schema format ("openai" or "gemini")
            legacy: Use legacy OpenAI format
            
        Returns:
            List of tool schemas for LLM function calling
        """
        available_tools = self.get_available_tools()
        schemas = []
        
        for tool in available_tools:
            if format.lower() == "openai":
                schema = tool.to_openai_schema(legacy=legacy)
            elif format.lower() == "gemini":
                schema = tool.to_gemini_schema()
            else:
                raise ValueError(f"Unknown schema format: {format}")
            schemas.append(schema)
        
        logger.debug(
            f"Generated {len(schemas)} schemas for {self.mode_name} "
            f"(format={format})"
        )
        return schemas
    
    # -------------------------------------------------------------------------
    # Tool Execution
    # -------------------------------------------------------------------------
    
    def execute(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """
        Execute a tool with permission checking and tracking.
        
        Permission Logic:
        1. Check: mode.is_tool_allowed(tool_name)
        2. If not allowed: raise ToolNotAllowedError
        3. If allowed: Get tool from registry and execute
        4. Track execution in context
        5. Track file operations (read/modify/create)
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult from tool execution
            
        Raises:
            ToolNotAllowedError: If tool is not permitted (security)
            
        Note:
            Tool not found returns ToolResult with error (doesn't raise).
            Tool execution failures return the tool's error result.
        """
        logger.info(f"Executing tool: {tool_name} (mode={self.mode_name})")
        
        # Step 1 & 2: Permission check (raises if not allowed)
        self.check_permission(tool_name)
        
        # Step 3: Get tool from registry
        tool = self._registry.get(tool_name)
        
        if tool is None:
            # Tool not found - return error result (don't raise)
            logger.warning(f"Tool not found: {tool_name}")
            result = ToolResult.fail(
                f"Tool '{tool_name}' not found in registry",
                error_type="ToolNotFoundError"
            )
            self._track_execution(tool_name, result, kwargs)
            return result
        
        # Execute the tool
        try:
            result = tool.execute(**kwargs)
        except Exception as e:
            # Unexpected execution error
            logger.error(f"Tool execution error: {tool_name} - {e}")
            result = ToolResult.from_exception(
                e,
                tool=tool_name,
                parameters=kwargs
            )
        
        # Step 4: Track execution in context
        self._track_execution(tool_name, result, kwargs)
        
        # Step 5: Track file operations
        self._track_file_operations(tool_name, result, kwargs)
        
        return result
    
    def _track_execution(
        self,
        tool_name: str,
        result: ToolResult,
        parameters: Dict[str, Any],
    ) -> None:
        """Track tool execution in context."""
        # Get execution time from result metadata
        execution_time_ms = result.metadata.get("execution_time_ms", 0.0)
        
        self._context.add_tool_execution(
            tool_name=tool_name,
            success=result.success,
            parameters=parameters,
            result=result.data if result.success else None,
            error=result.error if not result.success else None,
            execution_time_ms=execution_time_ms,
        )
    
    def _track_file_operations(
        self,
        tool_name: str,
        result: ToolResult,
        parameters: Dict[str, Any],
    ) -> None:
        """Track file operations in context based on tool execution."""
        if not result.success:
            return  # Don't track failed operations
        
        # Get file path from parameters or result
        path = parameters.get("path") or result.data.get("path") if result.data else None
        
        if not path:
            return
        
        # Determine operation type from tool name or category
        tool = self._registry.get(tool_name)
        
        if tool is None:
            return
        
        if tool.category == ToolCategory.READ:
            self._context.add_file_read(path)
        elif tool.category == ToolCategory.WRITE:
            # Check if it's a new file or modification
            was_created = result.data.get("created", False) if result.data else False
            if was_created:
                self._context.add_file_created(path)
            else:
                self._context.add_file_modified(path)
    
    # -------------------------------------------------------------------------
    # Batch Execution
    # -------------------------------------------------------------------------
    
    def execute_many(
        self,
        tool_calls: List[Dict[str, Any]],
        stop_on_error: bool = False,
    ) -> List[ToolResult]:
        """
        Execute multiple tools in sequence.
        
        Args:
            tool_calls: List of {"name": str, "parameters": dict}
            stop_on_error: Stop on first error if True
            
        Returns:
            List of ToolResult objects
        """
        results = []
        
        for call in tool_calls:
            tool_name = call.get("name")
            parameters = call.get("parameters", {})
            
            if not tool_name:
                results.append(ToolResult.fail("Missing tool name in call"))
                if stop_on_error:
                    break
                continue
            
            try:
                result = self.execute(tool_name, **parameters)
                results.append(result)
                
                if not result.success and stop_on_error:
                    logger.info("Stopping batch execution due to error")
                    break
                    
            except ToolNotAllowedError as e:
                # Permission errors stop execution
                results.append(ToolResult.fail(str(e), error_type="PermissionDenied"))
                if stop_on_error:
                    break
        
        return results
    
    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get executor summary.
        
        Returns:
            Dictionary with executor state
        """
        available = self.get_available_tool_names()
        all_tools = self._registry.list_names()
        
        return {
            "mode": self.mode_name,
            "available_tools": available,
            "blocked_tools": [t for t in all_tools if t not in available],
            "total_registered": len(all_tools),
            "total_available": len(available),
        }
    
    def __str__(self) -> str:
        """String representation."""
        available = len(self.get_available_tools())
        return f"ToolExecutor(mode={self.mode_name}, available_tools={available})"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"<ToolExecutor("
            f"mode='{self.mode_name}', "
            f"tools={len(self._registry)})>"
        )


# =============================================================================
# Self-Test
# =============================================================================

if __name__ == "__main__":
    from pathlib import Path
    import tempfile
    
    print("=" * 60)
    print("ToolExecutor Self-Test")
    print("=" * 60)
    
    # Create a mock mode for testing
    from dataclasses import dataclass, field
    from typing import List
    
    @dataclass
    class MockModeConfig:
        name: str = "TEST"
        description: str = "Test mode"
        temperature: float = 0.5
        max_tokens: int = 1000
        tools_allowed: List[str] = field(default_factory=lambda: ["read_file"])
        requires_git_branch: bool = False
        system_prompt: str = "You are a test assistant."
        icon: str = "🧪"
    
    class MockMode:
        def __init__(self, tools_allowed=None):
            self._config = MockModeConfig()
            if tools_allowed:
                self._config.tools_allowed = tools_allowed
        
        @property
        def config(self):
            return self._config
        
        def is_tool_allowed(self, tool_name):
            if "ALL" in self._config.tools_allowed:
                return True
            return tool_name in self._config.tools_allowed
        
        def get_allowed_tools(self):
            return self._config.tools_allowed.copy()
    
    # Setup test environment
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a test file
        test_file = temp_path / "test.py"
        test_file.write_text("print('hello')\n")
        
        # Register tools
        from Rocket.TOOLS.registry import ToolRegistry
        from Rocket.TOOLS.read_file import ReadFileTool
        from Rocket.TOOLS.write_file import WriteFileTool
        
        registry = ToolRegistry()
        registry.register(ReadFileTool(workspace_root=temp_path))
        registry.register(WriteFileTool(workspace_root=temp_path))
        
        # Test 1: Create executor with restricted mode
        print("\n--- Test 1: Create Executor (Restricted Mode) ---")
        mode = MockMode(tools_allowed=["read_file"])  # Only read allowed
        context = ExecutionContext(user_prompt="Test prompt", mode_name="TEST")
        executor = ToolExecutor(mode=mode, context=context, registry=registry)
        
        print(f"✓ Created executor: {executor}")
        print(f"  Available tools: {executor.get_available_tool_names()}")
        
        # Test 2: Execute allowed tool
        print("\n--- Test 2: Execute Allowed Tool ---")
        result = executor.execute("read_file", path="test.py")
        
        assert result.success
        print(f"✓ read_file executed successfully")
        # result.data is the file content or a dict depending on tool
        content = result.data if isinstance(result.data, str) else result.data.get('content', '')
        print(f"  Content preview: {content[:50]}...")
        
        # Test 3: Execute blocked tool (should raise)
        print("\n--- Test 3: Execute Blocked Tool ---")
        try:
            executor.execute("write_file", path="new.txt", mode="full", content="test")
            print("✗ Should have raised ToolNotAllowedError")
        except ToolNotAllowedError as e:
            print(f"✓ Correctly raised: {e.tool_name} blocked in {e.mode_name}")
        
        # Test 4: Execute non-existent tool
        print("\n--- Test 4: Execute Non-existent Tool ---")
        mode_all = MockMode(tools_allowed=["ALL"])  # Allow all for this test
        executor_all = ToolExecutor(mode=mode_all, context=context, registry=registry)
        
        result = executor_all.execute("nonexistent_tool")
        
        assert not result.success
        assert "not found" in result.error.lower()
        print(f"✓ Correctly returned error: {result.error}")
        
        # Test 5: Context tracking
        print("\n--- Test 5: Context Tracking ---")
        assert context.total_tool_executions >= 2
        print(f"✓ Tool executions tracked: {context.total_tool_executions}")
        print(f"  Successful: {context.successful_tool_executions}")
        print(f"  Failed: {context.failed_tool_executions}")
        
        # Test 6: File tracking
        print("\n--- Test 6: File Tracking ---")
        assert "test.py" in context.files_read
        print(f"✓ Files read tracked: {context.files_read}")
        
        # Test 7: Get tool schemas
        print("\n--- Test 7: Get Tool Schemas ---")
        schemas = executor.get_tool_schemas(format="openai")
        
        assert len(schemas) == 1  # Only read_file allowed
        assert schemas[0]["name"] == "read_file"
        print(f"✓ Generated {len(schemas)} schemas (only allowed tools)")
        
        # Test 8: ALL tools allowed mode
        print("\n--- Test 8: ALL Tools Mode ---")
        mode_all = MockMode(tools_allowed=["ALL"])
        executor_all = ToolExecutor(mode=mode_all, context=context, registry=registry)
        
        available = executor_all.get_available_tool_names()
        assert "read_file" in available
        assert "write_file" in available
        print(f"✓ ALL mode has access to: {available}")
        
        # Test 9: Batch execution
        print("\n--- Test 9: Batch Execution ---")
        context2 = ExecutionContext(user_prompt="Batch test", mode_name="TEST")
        executor2 = ToolExecutor(mode=mode_all, context=context2, registry=registry)
        
        calls = [
            {"name": "read_file", "parameters": {"path": "test.py"}},
            {"name": "write_file", "parameters": {"path": "new.txt", "mode": "full", "content": "new content"}},
        ]
        
        results = executor2.execute_many(calls)
        
        assert len(results) == 2
        assert results[0].success
        assert results[1].success
        print(f"✓ Batch execution: {len(results)} results")
        
        # Test 10: Executor summary
        print("\n--- Test 10: Executor Summary ---")
        summary = executor.get_summary()
        
        print(f"✓ Summary:")
        print(f"  Mode: {summary['mode']}")
        print(f"  Available: {summary['available_tools']}")
        print(f"  Blocked: {summary['blocked_tools']}")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
