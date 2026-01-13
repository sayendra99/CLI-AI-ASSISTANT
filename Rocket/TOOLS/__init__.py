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

__all__ = [
    # Base classes
    "ToolCategory",
    "ToolResult",
    "BaseTool",
    # Tools
    "ReadFileTool",
    # Exceptions
    "FileSecurityError",
]
