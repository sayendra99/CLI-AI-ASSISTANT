"""
Base Tool Interface for Rocket AI Coding Assistant.

This module provides the foundational abstractions for all tools
in the Rocket CLI system. Tools are executed by modes with permission
checks and return standardized ToolResult objects.

Design Patterns:
    - Template Method: execute() wraps _execute() for consistent behavior
    - Strategy: Different tool implementations provide varied behaviors
    - ABC: Abstract base class enforces interface contract

Example Usage:
    class ReadFileTool(BaseTool):
        @property
        def name(self) -> str:
            return "read_file"
        
        @property
        def description(self) -> str:
            return "Read contents of a file"
        
        @property
        def category(self) -> ToolCategory:
            return ToolCategory.READ
        
        def _execute(self, **kwargs) -> ToolResult:
            # Implementation here
            pass

Author: Rocket AI Team
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Type
import time
import traceback

from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)


class ToolCategory(Enum):
    """
    Categories of tools available in Rocket.
    
    Each category represents a type of operation with different
    permission levels and safety considerations.
    
    Attributes:
        READ: Tools that read data (files, configs, etc.) - Safe, no side effects
        WRITE: Tools that modify files or state - Requires confirmation
        EXECUTE: Tools that run commands or code - High risk, sandboxed
        ANALYZE: Tools that analyze code/data - Safe, read-only analysis
        TEST: Tools that run tests - Medium risk, controlled execution
    """
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    ANALYZE = auto()
    TEST = auto()
    
    def __str__(self) -> str:
        """Human-readable category name."""
        return self.name
    
    @property
    def is_safe(self) -> bool:
        """Check if category is considered safe (no side effects)."""
        return self in (ToolCategory.READ, ToolCategory.ANALYZE)
    
    @property
    def requires_confirmation(self) -> bool:
        """Check if category typically requires user confirmation."""
        return self in (ToolCategory.WRITE, ToolCategory.EXECUTE)
    
    @property
    def icon(self) -> str:
        """Get emoji icon for this category."""
        icons = {
            ToolCategory.READ: "📖",
            ToolCategory.WRITE: "✏️",
            ToolCategory.EXECUTE: "⚡",
            ToolCategory.ANALYZE: "🔍",
            ToolCategory.TEST: "🧪",
        }
        return icons.get(self, "🔧")


@dataclass
class ToolResult:
    """
    Standardized result from tool execution.
    
    All tools return ToolResult objects to ensure consistent
    handling of success, errors, and metadata across the system.
    
    Attributes:
        success: Whether the tool executed successfully
        data: The result data (type depends on tool)
        error: Error message if success is False
        error_type: Type/category of error (e.g., "FileNotFoundError")
        metadata: Additional context (timing, tool info, etc.)
        
    Example:
        # Successful result
        result = ToolResult(
            success=True,
            data={"content": "file contents here"},
            metadata={"lines": 42, "encoding": "utf-8"}
        )
        
        # Error result
        result = ToolResult(
            success=False,
            error="File not found: config.yaml",
            error_type="FileNotFoundError"
        )
    """
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate the result state."""
        # Ensure error is set if not successful (non-empty string)
        if not self.success:
            if not self.error or not self.error.strip():
                raise ValueError(
                    "ToolResult with success=False must have a non-empty error message"
                )
            # Ensure error_type is set for failed results
            if not self.error_type:
                self.error_type = "Error"
        
        # Ensure success=True doesn't have error set (contradiction)
        if self.success and self.error:
            raise ValueError(
                "ToolResult with success=True cannot have an error message. "
                f"Got error: {self.error}"
            )
        
        # Ensure metadata is always a dict
        if self.metadata is None:
            self.metadata = {}
        
        # Log the result creation (only at debug level to reduce overhead)
        if logger.isEnabledFor(10):  # DEBUG level
            if self.success:
                logger.debug(f"ToolResult: success, data_type={type(self.data).__name__}")
            else:
                logger.debug(f"ToolResult: failed, error_type={self.error_type}")
    
    @classmethod
    def ok(cls, data: Any = None, **metadata) -> "ToolResult":
        """
        Create a successful result.
        
        Args:
            data: The result data
            **metadata: Additional metadata key-value pairs
            
        Returns:
            ToolResult with success=True
            
        Example:
            return ToolResult.ok({"content": text}, lines=100)
        """
        return cls(success=True, data=data, metadata=metadata)
    
    @classmethod
    def fail(
        cls,
        error: str,
        error_type: Optional[str] = None,
        **metadata
    ) -> "ToolResult":
        """
        Create a failed result.
        
        Args:
            error: Error message describing what went wrong
            error_type: Category of error (e.g., exception class name)
            **metadata: Additional metadata key-value pairs
            
        Returns:
            ToolResult with success=False
            
        Example:
            return ToolResult.fail("File not found", "FileNotFoundError", path=filepath)
        """
        return cls(
            success=False,
            error=error,
            error_type=error_type or "Error",
            metadata=metadata
        )
    
    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        include_traceback: bool = True,
        max_traceback_lines: int = 50,
        **metadata
    ) -> "ToolResult":
        """
        Create a failed result from an exception.
        
        Args:
            exc: The exception that occurred
            include_traceback: Whether to include traceback in metadata
            max_traceback_lines: Maximum traceback lines to store (memory safety)
            **metadata: Additional metadata key-value pairs
            
        Returns:
            ToolResult with exception details
        """
        result_metadata = {**metadata}
        
        if include_traceback:
            tb_lines = traceback.format_exc().splitlines()
            if len(tb_lines) > max_traceback_lines:
                tb_lines = tb_lines[:max_traceback_lines] + [
                    f"... truncated ({len(tb_lines) - max_traceback_lines} more lines)"
                ]
            result_metadata["traceback"] = "\n".join(tb_lines)
        
        return cls(
            success=False,
            error=str(exc) or f"{type(exc).__name__} (no message)",
            error_type=type(exc).__name__,
            metadata=result_metadata
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert result to dictionary format.
        
        Useful for JSON serialization and LLM responses.
        
        Returns:
            Dictionary representation of the result
        """
        result = {
            "success": self.success,
            "data": self.data,
        }
        
        if not self.success:
            result["error"] = self.error
            result["error_type"] = self.error_type
        
        if self.metadata:
            result["metadata"] = self.metadata
        
        return result
    
    def __bool__(self) -> bool:
        """Allow using result in boolean context."""
        return self.success


class BaseTool(ABC):
    """
    Abstract base class for all Rocket tools.
    
    Tools are the fundamental building blocks that modes use to
    interact with files, execute code, analyze projects, etc.
    Each tool must define its name, description, category, and
    implement the _execute() method.
    
    Template Method Pattern:
        The execute() method provides consistent timing, logging,
        and error handling, while _execute() contains the actual
        tool-specific logic.
    
    Subclasses must implement:
        - name: Unique identifier for the tool
        - description: Human-readable description
        - category: ToolCategory enum value
        - _execute(): The actual tool logic
    
    Optional overrides:
        - parameters_schema: JSON schema for LLM function calling
        - validate_parameters(): Custom parameter validation
    
    Example:
        class ReadFileTool(BaseTool):
            @property
            def name(self) -> str:
                return "read_file"
            
            @property
            def description(self) -> str:
                return "Read the contents of a file from the filesystem"
            
            @property
            def category(self) -> ToolCategory:
                return ToolCategory.READ
            
            @property
            def parameters_schema(self) -> Dict[str, Any]:
                return {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to read"
                        },
                        "encoding": {
                            "type": "string",
                            "description": "File encoding",
                            "default": "utf-8"
                        }
                    },
                    "required": ["path"]
                }
            
            def _execute(self, path: str, encoding: str = "utf-8") -> ToolResult:
                content = Path(path).read_text(encoding=encoding)
                return ToolResult.ok(content, path=path, encoding=encoding)
    """
    
    # Cache for generated schemas (performance optimization)
    _schema_cache: Optional[Dict[str, Dict[str, Any]]] = None
    
    def __init__(self) -> None:
        """Initialize the tool and validate configuration."""
        self._schema_cache = {}
        self._validate_tool_config()
    
    def _validate_tool_config(self) -> None:
        """
        Validate tool configuration on initialization.
        
        Raises:
            ValueError: If name or description is invalid
        """
        # Validate name
        if not self.name or not self.name.strip():
            raise ValueError(f"{self.__class__.__name__}: Tool name cannot be empty")
        
        if not self.name.replace("_", "").isalnum():
            raise ValueError(
                f"{self.__class__.__name__}: Tool name must be alphanumeric with underscores, "
                f"got '{self.name}'"
            )
        
        # Validate description
        if not self.description or not self.description.strip():
            raise ValueError(f"{self.__class__.__name__}: Tool description cannot be empty")
        
        # Validate category type
        if not isinstance(self.category, ToolCategory):
            raise ValueError(
                f"{self.__class__.__name__}: category must be a ToolCategory enum, "
                f"got {type(self.category).__name__}"
            )
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique identifier for this tool.
        
        Should be lowercase with underscores (e.g., "read_file", "run_tests").
        Used for permission checks and LLM function calling.
        
        Returns:
            Tool name string
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Human-readable description of what this tool does.
        
        Used in help text and sent to LLM for function selection.
        Should be clear and concise.
        
        Returns:
            Description string
        """
        pass
    
    @property
    @abstractmethod
    def category(self) -> ToolCategory:
        """
        Category this tool belongs to.
        
        Determines permission requirements and safety considerations.
        
        Returns:
            ToolCategory enum value
        """
        pass
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """
        JSON Schema for tool parameters.
        
        Used for LLM function calling schema generation.
        Override this to define the expected parameters.
        
        Returns:
            JSON Schema dictionary describing parameters
            
        Example:
            return {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "recursive": {"type": "boolean", "default": False}
                },
                "required": ["path"]
            }
        """
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    @abstractmethod
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the tool logic.
        
        This is the core implementation that subclasses must provide.
        Called by execute() after timing setup and validation.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with success/error status and data
            
        Raises:
            Any exceptions will be caught by execute() and
            converted to ToolResult.fail()
        """
        pass
    
    def validate_parameters(self, **kwargs: Any) -> Optional[str]:
        """
        Validate parameters before execution.
        
        Override this method to add custom parameter validation.
        Return None if valid, or an error message string if invalid.
        
        Args:
            **kwargs: Parameters to validate
            
        Returns:
            None if valid, error message string if invalid
        """
        return None
    
    def execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the tool with timing, logging, and error handling.
        
        This is the Template Method that wraps _execute() with:
        - Parameter validation
        - Execution timing
        - Error catching and conversion to ToolResult
        - Logging
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with execution results
            
        Note:
            Do not override this method. Implement _execute() instead.
        """
        start_time = time.perf_counter()
        
        logger.info(f"Executing tool: {self.name}")
        logger.debug(f"Tool parameters: {kwargs}")
        
        try:
            # Validate parameters
            validation_error = self.validate_parameters(**kwargs)
            if validation_error:
                logger.warning(f"Parameter validation failed: {validation_error}")
                return ToolResult.fail(
                    error=validation_error,
                    error_type="ValidationError",
                    tool=self.name,
                    parameters=kwargs
                )
            
            # Execute the tool
            result = self._execute(**kwargs)
            
            # Add timing metadata
            execution_time = time.perf_counter() - start_time
            result.metadata["execution_time_ms"] = round(execution_time * 1000, 2)
            result.metadata["tool"] = self.name
            result.metadata["category"] = str(self.category)
            
            logger.info(
                f"Tool {self.name} completed: "
                f"success={result.success}, time={execution_time:.3f}s"
            )
            
            return result
            
        except Exception as exc:
            execution_time = time.perf_counter() - start_time
            
            logger.error(
                f"Tool {self.name} failed with {type(exc).__name__}: {exc}",
                exc_info=True
            )
            
            return ToolResult.from_exception(
                exc,
                tool=self.name,
                category=str(self.category),
                parameters=kwargs,
                execution_time_ms=round(execution_time * 1000, 2)
            )
    
    def _get_cached_schema(self, schema_type: str) -> Optional[Dict[str, Any]]:
        """Get cached schema if available."""
        if self._schema_cache is None:
            self._schema_cache = {}
        return self._schema_cache.get(schema_type)
    
    def _cache_schema(self, schema_type: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Cache and return schema."""
        if self._schema_cache is None:
            self._schema_cache = {}
        self._schema_cache[schema_type] = schema
        return schema
    
    def clear_schema_cache(self) -> None:
        """Clear cached schemas (call if parameters_schema changes dynamically)."""
        self._schema_cache = {}
    
    def to_function_schema(self) -> Dict[str, Any]:
        """
        Generate LLM function calling schema for this tool.
        
        Creates a schema compatible with OpenAI/Google function calling
        format for use with LLM integrations. Results are cached.
        
        Returns:
            Function schema dictionary
            
        Example output:
            {
                "name": "read_file",
                "description": "Read the contents of a file",
                "parameters": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        """
        cached = self._get_cached_schema("function")
        if cached:
            return cached
        
        return self._cache_schema("function", {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema
        })
    
    def to_gemini_schema(self) -> Dict[str, Any]:
        """
        Generate Google Gemini-compatible function declaration.
        
        Results are cached for performance.
        
        Returns:
            Gemini function declaration dictionary
        """
        cached = self._get_cached_schema("gemini")
        if cached:
            return cached
        
        return self._cache_schema("gemini", {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema
        })
    
    def to_openai_schema(self, legacy: bool = False) -> Dict[str, Any]:
        """
        Generate OpenAI-compatible function schema.
        
        Supports both the newer Responses API format (default) and
        the legacy Chat Completions API format. Results are cached.
        
        Args:
            legacy: If True, use Chat Completions format with nested
                   'function' key. If False (default), use Responses
                   API format with flat structure.
        
        Returns:
            OpenAI function schema dictionary
            
        Example (Responses API - default):
            {
                "type": "function",
                "name": "read_file",
                "description": "...",
                "parameters": {...}
            }
            
        Example (Chat Completions - legacy=True):
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "...",
                    "parameters": {...}
                }
            }
        """
        cache_key = "openai_legacy" if legacy else "openai"
        cached = self._get_cached_schema(cache_key)
        if cached:
            return cached
        
        if legacy:
            # Chat Completions API format (older)
            return self._cache_schema(cache_key, {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": self.parameters_schema
                }
            })
        
        # Responses API format (newer, recommended)
        return self._cache_schema(cache_key, {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema
        })
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.category.icon} {self.name}: {self.description}"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"<{self.__class__.__name__}("
            f"name='{self.name}', "
            f"category={self.category.name})>"
        )
    
    def get_help(self) -> str:
        """
        Get formatted help text for this tool.
        
        Returns:
            Multi-line help string
        """
        lines = [
            f"{self.category.icon} {self.name}",
            f"   {self.description}",
            f"   Category: {self.category.name}",
        ]
        
        # Add parameter info if available
        props = self.parameters_schema.get("properties", {})
        required = self.parameters_schema.get("required", [])
        
        if props:
            lines.append("   Parameters:")
            for param_name, param_info in props.items():
                req_marker = "*" if param_name in required else ""
                param_type = param_info.get("type", "any")
                param_desc = param_info.get("description", "")
                lines.append(f"     - {param_name}{req_marker} ({param_type}): {param_desc}")
        
        return "\n".join(lines)
