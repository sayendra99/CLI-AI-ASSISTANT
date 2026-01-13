"""
Tool registry for managing available tools.

Centralized registry pattern for tool management.
Provides tool lookup and LLM schema generation.

Author: Rocket AI Team
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING

# Handle imports for both package and direct execution
try:
    from Rocket.TOOLS.Base import BaseTool, ToolCategory
    from Rocket.Utils.Log import get_logger
except ImportError:
    # Direct execution - add project root to path
    _project_root = Path(__file__).parent.parent.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))
    from Rocket.TOOLS.Base import BaseTool, ToolCategory
    from Rocket.Utils.Log import get_logger

if TYPE_CHECKING:
    from Rocket.TOOLS.Base import BaseTool, ToolCategory

logger = get_logger(__name__)


# =============================================================================
# Exceptions
# =============================================================================

class ToolRegistryError(Exception):
    """Tool registry operation failed."""
    pass


# =============================================================================
# Tool Registry
# =============================================================================

class ToolRegistry:
    """
    Registry for managing available tools.
    
    Provides centralized storage and retrieval of tools,
    with support for LLM function calling schema generation.
    
    Example:
        >>> registry = ToolRegistry()
        >>> registry.register(ReadFileTool())
        >>> tool = registry.get("read_file")
        >>> schemas = registry.get_schemas()
    """
    
    def __init__(self) -> None:
        """Initialize empty registry."""
        self._tools: Dict[str, BaseTool] = {}
        logger.debug("ToolRegistry initialized")
    
    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------
    
    def register(self, tool: BaseTool) -> None:
        """
        Register a tool.
        
        Args:
            tool: Tool instance to register
            
        Raises:
            ToolRegistryError: If tool already registered
            TypeError: If tool is not a BaseTool instance
        """
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Expected BaseTool, got {type(tool).__name__}")
        
        tool_name = tool.name
        
        if tool_name in self._tools:
            raise ToolRegistryError(f"Tool '{tool_name}' is already registered")
        
        self._tools[tool_name] = tool
        logger.info(f"Registered tool: {tool_name} ({tool.category.value})")
    
    def register_many(self, tools: List[BaseTool]) -> None:
        """
        Register multiple tools at once.
        
        Args:
            tools: List of tool instances to register
            
        Raises:
            ToolRegistryError: If any tool already registered
        """
        for tool in tools:
            self.register(tool)
    
    def unregister(self, tool_name: str) -> bool:
        """
        Remove a tool from the registry.
        
        Args:
            tool_name: Name of tool to remove
            
        Returns:
            True if tool was removed, False if not found
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
            return True
        return False
    
    # -------------------------------------------------------------------------
    # Retrieval
    # -------------------------------------------------------------------------
    
    def get(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Args:
            tool_name: Name of tool to retrieve
            
        Returns:
            Tool instance or None if not found
        """
        tool = self._tools.get(tool_name)
        
        if tool:
            logger.debug(f"Retrieved tool: {tool_name}")
        else:
            logger.warning(f"Tool not found: {tool_name}")
        
        return tool
    
    def get_or_raise(self, tool_name: str) -> BaseTool:
        """
        Get a tool by name, raising if not found.
        
        Args:
            tool_name: Name of tool to retrieve
            
        Returns:
            Tool instance
            
        Raises:
            ToolRegistryError: If tool not found
        """
        tool = self.get(tool_name)
        if tool is None:
            raise ToolRegistryError(f"Tool '{tool_name}' not found")
        return tool
    
    def exists(self, tool_name: str) -> bool:
        """
        Check if a tool is registered.
        
        Args:
            tool_name: Name to check
            
        Returns:
            True if tool exists
        """
        return tool_name in self._tools
    
    # -------------------------------------------------------------------------
    # Listing
    # -------------------------------------------------------------------------
    
    def list_all(self) -> List[BaseTool]:
        """
        Get list of all registered tools.
        
        Returns:
            List of tool instances
        """
        return list(self._tools.values())
    
    def list_names(self) -> List[str]:
        """
        Get list of all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def list_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """
        Get all tools in a specific category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of tools in that category
        """
        return [
            tool for tool in self._tools.values()
            if tool.category == category
        ]
    
    def list_safe(self) -> List[BaseTool]:
        """
        Get all tools that are safe (read-only).
        
        Returns:
            List of safe tools
        """
        return [
            tool for tool in self._tools.values()
            if tool.category.is_safe
        ]
    
    def list_dangerous(self) -> List[BaseTool]:
        """
        Get all tools that require confirmation.
        
        Returns:
            List of dangerous tools
        """
        return [
            tool for tool in self._tools.values()
            if tool.category.requires_confirmation
        ]
    
    # -------------------------------------------------------------------------
    # Schema Generation (for LLM function calling)
    # -------------------------------------------------------------------------
    
    def get_schemas(
        self,
        *,
        format: str = "openai",
        legacy: bool = False,
        category: Optional[ToolCategory] = None,
        tool_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get LLM function calling schemas for registered tools.
        
        Args:
            format: Schema format - "openai" or "gemini"
            legacy: For OpenAI, use legacy Chat Completions format
            category: Optional category filter
            tool_names: Optional list of specific tool names
            
        Returns:
            List of tool schemas for LLM function calling
            
        Example:
            >>> schemas = registry.get_schemas(format="openai")
            >>> # Use in OpenAI API call:
            >>> response = client.chat.completions.create(
            ...     model="gpt-4",
            ...     messages=[...],
            ...     tools=schemas
            ... )
        """
        # Determine which tools to include
        if tool_names is not None:
            tools = [
                self._tools[name] 
                for name in tool_names 
                if name in self._tools
            ]
        elif category is not None:
            tools = self.list_by_category(category)
        else:
            tools = self.list_all()
        
        # Generate schemas
        schemas = []
        for tool in tools:
            if format.lower() == "openai":
                schema = tool.to_openai_schema(legacy=legacy)
            elif format.lower() == "gemini":
                schema = tool.to_gemini_schema()
            else:
                raise ValueError(f"Unknown schema format: {format}")
            schemas.append(schema)
        
        logger.debug(f"Generated {len(schemas)} schemas (format={format})")
        return schemas
    
    def get_openai_schemas(
        self,
        *,
        legacy: bool = False,
        category: Optional[ToolCategory] = None,
    ) -> List[Dict[str, Any]]:
        """
        Convenience method for OpenAI schemas.
        
        Args:
            legacy: Use legacy Chat Completions format
            category: Optional category filter
            
        Returns:
            List of OpenAI tool schemas
        """
        return self.get_schemas(format="openai", legacy=legacy, category=category)
    
    def get_gemini_schemas(
        self,
        *,
        category: Optional[ToolCategory] = None,
    ) -> List[Dict[str, Any]]:
        """
        Convenience method for Gemini schemas.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of Gemini function declarations
        """
        return self.get_schemas(format="gemini", category=category)
    
    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------
    
    def count(self) -> int:
        """
        Get number of registered tools.
        
        Returns:
            Count of registered tools
        """
        return len(self._tools)
    
    def clear(self) -> None:
        """Remove all tools from registry."""
        self._tools.clear()
        logger.info("Registry cleared")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the registry.
        
        Returns:
            Dictionary with registry statistics
        """
        by_category = {}
        for category in ToolCategory:
            tools = self.list_by_category(category)
            if tools:
                by_category[category.value] = [t.name for t in tools]
        
        return {
            "total_tools": self.count(),
            "tools": self.list_names(),
            "by_category": by_category,
            "safe_count": len(self.list_safe()),
            "dangerous_count": len(self.list_dangerous()),
        }
    
    # -------------------------------------------------------------------------
    # Magic Methods
    # -------------------------------------------------------------------------
    
    def __len__(self) -> int:
        """Support len() builtin."""
        return self.count()
    
    def __contains__(self, tool_name: str) -> bool:
        """Support 'in' operator."""
        return self.exists(tool_name)
    
    def __iter__(self):
        """Support iteration over tools."""
        return iter(self._tools.values())
    
    def __getitem__(self, tool_name: str) -> BaseTool:
        """Support dictionary-style access."""
        tool = self.get(tool_name)
        if tool is None:
            raise KeyError(tool_name)
        return tool
    
    def __str__(self) -> str:
        """String representation."""
        tools = ", ".join(self.list_names())
        return f"ToolRegistry({self.count()} tools: {tools})"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"ToolRegistry(tools={self.list_names()})"


# =============================================================================
# Module-level Singleton Instance
# =============================================================================

# Global registry instance (singleton pattern)
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.
    
    Creates the registry on first access (lazy initialization).
    
    Returns:
        The global ToolRegistry instance
        
    Example:
        >>> from Rocket.TOOLS.registry import get_registry
        >>> registry = get_registry()
        >>> registry.register(ReadFileTool())
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        logger.debug("Global tool registry created")
    return _registry


def reset_registry() -> None:
    """
    Reset the global registry (mainly for testing).
    
    Creates a new empty registry instance.
    """
    global _registry
    _registry = ToolRegistry()
    logger.debug("Global tool registry reset")


# =============================================================================
# Convenience Functions (operate on global registry)
# =============================================================================

def register_tool(tool: BaseTool) -> None:
    """
    Register a tool in the global registry.
    
    Args:
        tool: Tool instance to register
    """
    get_registry().register(tool)


def get_tool(tool_name: str) -> Optional[BaseTool]:
    """
    Get a tool from the global registry.
    
    Args:
        tool_name: Name of tool to retrieve
        
    Returns:
        Tool instance or None
    """
    return get_registry().get(tool_name)


def list_tools() -> List[BaseTool]:
    """
    List all tools in the global registry.
    
    Returns:
        List of all registered tools
    """
    return get_registry().list_all()


def get_tool_schemas(
    format: str = "openai",
    legacy: bool = False,
) -> List[Dict[str, Any]]:
    """
    Get LLM schemas from the global registry.
    
    Args:
        format: Schema format ("openai" or "gemini")
        legacy: Use legacy format for OpenAI
        
    Returns:
        List of tool schemas
    """
    return get_registry().get_schemas(format=format, legacy=legacy)


# =============================================================================
# Self-Test
# =============================================================================

if __name__ == "__main__":
    import json
    
    print("=" * 60)
    print("ToolRegistry Self-Test")
    print("=" * 60)
    
    # Import tools for testing
    from Rocket.TOOLS.read_file import ReadFileTool
    from Rocket.TOOLS.write_file import WriteFileTool
    
    # Test 1: Basic registration
    print("\n--- Test 1: Basic Registration ---")
    registry = ToolRegistry()
    
    read_tool = ReadFileTool(workspace_root=Path("."))
    write_tool = WriteFileTool(workspace_root=Path("."))
    
    registry.register(read_tool)
    registry.register(write_tool)
    
    print(f"Registered tools: {registry.list_names()}")
    assert registry.count() == 2
    print("✓ Basic registration works")
    
    # Test 2: Retrieval
    print("\n--- Test 2: Retrieval ---")
    tool = registry.get("read_file")
    assert tool is not None
    assert tool.name == "read_file"
    print(f"✓ Retrieved: {tool.name}")
    
    # Test 3: exists()
    print("\n--- Test 3: Existence Check ---")
    assert registry.exists("read_file")
    assert not registry.exists("nonexistent")
    assert "write_file" in registry  # __contains__
    print("✓ Existence check works")
    
    # Test 4: list_by_category
    print("\n--- Test 4: List by Category ---")
    read_tools = registry.list_by_category(ToolCategory.READ)
    write_tools = registry.list_by_category(ToolCategory.WRITE)
    print(f"  READ tools: {[t.name for t in read_tools]}")
    print(f"  WRITE tools: {[t.name for t in write_tools]}")
    assert len(read_tools) == 1
    assert len(write_tools) == 1
    print("✓ Category filtering works")
    
    # Test 5: Schema generation
    print("\n--- Test 5: Schema Generation ---")
    schemas = registry.get_schemas(format="openai")
    print(f"  Generated {len(schemas)} OpenAI schemas")
    assert len(schemas) == 2
    
    # Verify schema structure (Responses API format - flat structure)
    for schema in schemas:
        assert "type" in schema
        assert schema["type"] == "function"
        assert "name" in schema  # Name at top level in Responses API format
        print(f"  - {schema['name']}: valid schema")
    print("✓ Schema generation works")
    
    # Test 6: Legacy schema format
    print("\n--- Test 6: Legacy Schema Format ---")
    legacy_schemas = registry.get_schemas(format="openai", legacy=True)
    for schema in legacy_schemas:
        assert "function" in schema  # Legacy format has nested 'function' key
        assert "name" in schema["function"]
        print(f"  - {schema['function']['name']}: legacy format")
    print("✓ Legacy format works")
    
    # Test 7: Gemini schema
    print("\n--- Test 7: Gemini Schema ---")
    gemini_schemas = registry.get_gemini_schemas()
    for schema in gemini_schemas:
        assert "name" in schema
        assert "description" in schema
        print(f"  - {schema['name']}: Gemini format")
    print("✓ Gemini format works")
    
    # Test 8: Safe/Dangerous filtering
    print("\n--- Test 8: Safe/Dangerous Filtering ---")
    safe = registry.list_safe()
    dangerous = registry.list_dangerous()
    print(f"  Safe tools: {[t.name for t in safe]}")
    print(f"  Dangerous tools: {[t.name for t in dangerous]}")
    print("✓ Safety filtering works")
    
    # Test 9: Summary
    print("\n--- Test 9: Summary ---")
    summary = registry.get_summary()
    print(f"  Total: {summary['total_tools']}")
    print(f"  By category: {summary['by_category']}")
    print("✓ Summary generation works")
    
    # Test 10: Global registry
    print("\n--- Test 10: Global Registry ---")
    reset_registry()
    register_tool(ReadFileTool(workspace_root=Path(".")))
    tool = get_tool("read_file")
    assert tool is not None
    print(f"✓ Global registry works: {tool.name}")
    
    # Test 11: Duplicate registration error
    print("\n--- Test 11: Duplicate Registration Error ---")
    try:
        registry.register(ReadFileTool(workspace_root=Path(".")))
        print("✗ Should have raised error")
    except ToolRegistryError as e:
        print(f"✓ Correctly raised: {e}")
    
    # Test 12: Dictionary-style access
    print("\n--- Test 12: Dictionary-style Access ---")
    tool = registry["read_file"]
    print(f"✓ registry['read_file'] = {tool.name}")
    
    try:
        _ = registry["nonexistent"]
        print("✗ Should have raised KeyError")
    except KeyError:
        print("✓ Correctly raised KeyError for missing tool")
    
    # Test 13: Iteration
    print("\n--- Test 13: Iteration ---")
    for tool in registry:
        print(f"  - {tool.name}: {tool.category.value}")
    print("✓ Iteration works")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
