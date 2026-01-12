"""
Mode registry for managing available modes.

Centralized registry pattern for mode management.
"""

from typing import Dict, List, Optional

from Rocket.MODES.Base import BaseMode
from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)


class ModeRegistryError(Exception):
    """Mode registry operation failed."""
    pass


class ModeRegistry:
    """
    Registry for managing operating modes.
    
    Provides centralized storage and retrieval of modes.
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._modes: Dict[str, BaseMode] = {}
        logger.debug("ModeRegistry initialized")
    
    def register(self, mode: BaseMode) -> None:
        """
        Register a mode.
        
        Args:
            mode: Mode instance to register
            
        Raises:
            ModeRegistryError: If mode already registered
        """
        mode_name = mode.config.name
        
        if mode_name in self._modes:
            raise ModeRegistryError(f"Mode '{mode_name}' is already registered")
        
        self._modes[mode_name] = mode
        logger.info(f"Registered mode: {mode_name}")
    
    def get(self, mode_name: str) -> Optional[BaseMode]:
        """
        Get a mode by name.
        
        Args:
            mode_name: Name of mode to retrieve
            
        Returns:
            Mode instance or None if not found
        """
        mode = self._modes.get(mode_name.upper())
        
        if mode:
            logger.debug(f"Retrieved mode: {mode_name}")
        else:
            logger.warning(f"Mode not found: {mode_name}")
        
        return mode
    
    def get_or_default(self, mode_name: str, default: str = "READ") -> BaseMode:
        """
        Get mode by name, or return default if not found.
        
        Args:
            mode_name: Name of mode to retrieve
            default: Default mode name
            
        Returns:
            Mode instance
            
        Raises:
            ModeRegistryError: If both mode and default not found
        """
        if mode := self.get(mode_name):
            return mode
        
        # Try default
        default_mode = self.get(default)
        if not default_mode:
            raise ModeRegistryError(f"Neither '{mode_name}' nor default '{default}' found")
        
        logger.warning(f"Mode '{mode_name}' not found, using default: {default}")
        return default_mode
    
    def list_all(self) -> List[BaseMode]:
        """
        Get list of all registered modes.
        
        Returns:
            List of mode instances
        """
        return list(self._modes.values())
    
    def list_names(self) -> List[str]:
        """
        Get list of all registered mode names.
        
        Returns:
            List of mode names
        """
        return list(self._modes.keys())
    
    def exists(self, mode_name: str) -> bool:
        """
        Check if a mode is registered.
        
        Args:
            mode_name: Name to check
            
        Returns:
            True if mode exists
        """
        return mode_name.upper() in self._modes
    
    def count(self) -> int:
        """
        Get number of registered modes.
        
        Returns:
            Count of registered modes
        """
        return len(self._modes)
    
    def __len__(self) -> int:
        """Support len() builtin."""
        return self.count()
    
    def __contains__(self, mode_name: str) -> bool:
        """Support 'in' operator."""
        return self.exists(mode_name)
    
    def __str__(self) -> str:
        """String representation."""
        modes = ", ".join(self.list_names())
        return f"ModeRegistry({self.count()} modes: {modes})"
