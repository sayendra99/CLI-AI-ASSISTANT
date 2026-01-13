"""
Rocket Tools Package.

Provides the base tool interface and implementations for
the Rocket AI Coding Assistant.
"""

from Rocket.TOOLS.Base import (
    ToolCategory,
    ToolResult,
    BaseTool,
)
from Rocket.TOOLS.read_file import (
    ReadFileTool,
    FileSecurityError,
)
from Rocket.TOOLS.write_file import (
    WriteFileTool,
    WriteConflictError,
)
from Rocket.TOOLS.registry import (
    ToolRegistry,
    ToolRegistryError,
    get_registry,
    reset_registry,
    register_tool,
    get_tool,
    list_tools,
    get_tool_schemas,
)

__all__ = [
    # Base classes
    "ToolCategory",
    "ToolResult",
    "BaseTool",
    # Tools
    "ReadFileTool",
    "WriteFileTool",
    # Registry
    "ToolRegistry",
    "ToolRegistryError",
    "get_registry",
    "reset_registry",
    "register_tool",
    "get_tool",
    "list_tools",
    "get_tool_schemas",
    # Exceptions
    "FileSecurityError",
    "WriteConflictError",
]
