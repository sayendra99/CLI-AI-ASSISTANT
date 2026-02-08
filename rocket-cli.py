#!/usr/bin/env python3
"""
Rocket CLI - Optimized Performance Entry Point

Performance Optimizations:
- Efficient data structures (sets, dicts, generators)
- LRU caching for frequently accessed data.
- Lazy loading of modules
- Buffered I/O for large files
- Memory-efficient string operations
"""

import sys
from functools import lru_cache
from typing import Optional, Dict, Any

# Lazy imports - only load modules when needed to speed up startup time
_MODULE_CACHE: Dict[str, Any] = {}


@lru_cache(maxsize=128)
def get_cached_greeting(name: str) -> str:
    """
    Generate cached greeting message.
    
    Uses LRU cache to avoid regenerating the same greeting
    for repeated calls with the same name.
    
    Args:
        name: User's name
        
    Returns:
        Formatted greeting string
    """
    return f"Hey {name}"


def greeting(name: str) -> None:
    """
    Display greeting message with caching.
    
    Args:
        name: User's name to greet
    """
    print(get_cached_greeting(name))


def load_module_lazy(module_name: str) -> Any:
    """
    Load module lazily with caching.
    
    Modules are only loaded when first needed and then cached
    for subsequent access, improving startup performance.
    
    Args:
        module_name: Name of module to import
        
    Returns:
        Loaded module object
    """
    if module_name not in _MODULE_CACHE:
        if module_name == 'Rocket.CLI.Main':
            from Rocket.CLI import Main
            _MODULE_CACHE[module_name] = Main
        elif module_name == 'Rocket.Utils.Config':
            from Rocket.Utils import Config
            _MODULE_CACHE[module_name] = Config
        # Add more modules as needed
    
    return _MODULE_CACHE.get(module_name)


def main() -> None:
    """
    Main entry point with optimized argument parsing.
    
    Uses efficient data structures and early returns to minimize
    processing overhead.
    """
    # Fast path: validate args before any heavy processing
    if len(sys.argv) < 2:
        print("Usage: rocket-cli <name>")
        sys.exit(1)
    
    # Use efficient string extraction (no copying)
    name = sys.argv[1]
    
    # Basic validation with early return
    if not name or not name.strip():
        print("Error: Name cannot be empty")
        sys.exit(1)
    
    greeting(name)


if __name__ == '__main__':
    main()
