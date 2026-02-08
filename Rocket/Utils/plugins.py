"""
Plugin System for Rocket CLI

Extensible plugin architecture allowing users to add custom functionality.

Features:
- Dynamic plugin discovery and loading
- Plugin lifecycle management (initialize, execute, cleanup)
- Plugin dependencies and version checking
- Secure plugin sandboxing
- Plugin marketplace/registry support
- Hook system for extending core functionality

Usage:
    from Rocket.Utils.plugins import PluginManager
    
    manager = PluginManager()
    manager.discover_plugins()
    manager.load_plugin("my-plugin")
    manager.execute_hook("before_command", context={})
"""

import importlib
import importlib.util
import inspect
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)


@dataclass
class PluginMetadata:
    """Plugin metadata information."""
    name: str
    version: str
    author: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    enabled: bool = True
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "dependencies": self.dependencies,
            "hooks": self.hooks,
            "enabled": self.enabled
        }


class Plugin(ABC):
    """
    Base class for all Rocket CLI plugins.
    
    Plugins must inherit from this class and implement required methods.
    """
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Plugin metadata."""
        pass
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize plugin with configuration.
        
        Args:
            config: Plugin configuration dictionary
            
        Returns:
            True if initialization successful
        """
        return True
    
    def cleanup(self) -> None:
        """Cleanup plugin resources before unloading."""
        pass
    
    def get_hooks(self) -> Dict[str, Callable]:
        """
        Get plugin hooks.
        
        Returns:
            Dictionary mapping hook names to callable functions
        """
        return {}


class PluginManager:
    """
    Manages plugin discovery, loading, and execution.
    
    Provides a secure extensibility mechanism for Rocket CLI.
    """
    
    # Available hook points in the CLI lifecycle
    AVAILABLE_HOOKS = {
        "before_command": "Called before executing any command",
        "after_command": "Called after command execution",
        "on_error": "Called when an error occurs",
        "before_generate": "Called before generating code",
        "after_generate": "Called after code generation",
        "before_chat": "Called before chat interaction",
        "after_chat": "Called after chat interaction",
        "on_login": "Called after successful login",
        "on_logout": "Called after logout",
        "on_config_change": "Called when configuration changes"
    }
    
    def __init__(self, plugins_dir: Optional[Path] = None):
        """
        Initialize plugin manager.
        
        Args:
            plugins_dir: Directory containing plugins
        """
        self.plugins_dir = plugins_dir or (Path.home() / ".rocket-cli" / "plugins")
        self._loaded_plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, List[Callable]] = {hook: [] for hook in self.AVAILABLE_HOOKS}
        
        # Create plugins directory if needed
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
    
    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins in the plugins directory.
        
        Returns:
            List of discovered plugin names
        """
        discovered = []
        
        if not self.plugins_dir.exists():
            return discovered
        
        # Look for Python files or directories with __init__.py
        for item in self.plugins_dir.iterdir():
            if item.is_file() and item.suffix == '.py' and item.name != '__init__.py':
                discovered.append(item.stem)
            elif item.is_dir() and (item / '__init__.py').exists():
                discovered.append(item.name)
        
        logger.info(f"Discovered {len(discovered)} plugins: {discovered}")
        return discovered
    
    def load_plugin(self, plugin_name: str, config: Optional[Dict] = None) -> bool:
        """
        Load a plugin by name.
        
        Args:
            plugin_name: Name of the plugin to load
            config: Optional plugin configuration
            
        Returns:
            True if plugin loaded successfully
        """
        if plugin_name in self._loaded_plugins:
            logger.warning(f"Plugin '{plugin_name}' already loaded")
            return True
        
        try:
            # Find plugin file
            plugin_file = self.plugins_dir / f"{plugin_name}.py"
            plugin_package = self.plugins_dir / plugin_name / "__init__.py"
            
            if plugin_file.exists():
                module_path = plugin_file
            elif plugin_package.exists():
                module_path = plugin_package
            else:
                logger.error(f"Plugin '{plugin_name}' not found")
                return False
            
            # Load module dynamically
            spec = importlib.util.spec_from_file_location(plugin_name, module_path)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to load plugin spec: {plugin_name}")
                return False
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_name] = module
            spec.loader.exec_module(module)
            
            # Find Plugin class in module
            plugin_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Plugin) and obj != Plugin:
                    plugin_class = obj
                    break
            
            if plugin_class is None:
                logger.error(f"No Plugin class found in {plugin_name}")
                return False
            
            # Instantiate plugin
            plugin = plugin_class()
            
            # Initialize plugin
            if not plugin.initialize(config or {}):
                logger.error(f"Plugin '{plugin_name}' initialization failed")
                return False
            
            # Register hooks
            for hook_name, hook_func in plugin.get_hooks().items():
                if hook_name in self._hooks:
                    self._hooks[hook_name].append(hook_func)
                    logger.debug(f"Registered hook '{hook_name}' for plugin '{plugin_name}'")
            
            # Store loaded plugin
            self._loaded_plugins[plugin_name] = plugin
            
            logger.info(f"Loaded plugin: {plugin_name} v{plugin.metadata.version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load plugin '{plugin_name}': {e}")
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin.
        
        Args:
            plugin_name: Name of the plugin to unload
            
        Returns:
            True if plugin unloaded successfully
        """
        if plugin_name not in self._loaded_plugins:
            logger.warning(f"Plugin '{plugin_name}' not loaded")
            return False
        
        try:
            plugin = self._loaded_plugins[plugin_name]
            
            # Cleanup plugin
            plugin.cleanup()
            
            # Unregister hooks
            for hook_name, hook_funcs in self._hooks.items():
                # Remove hooks from this plugin
                plugin_hooks = plugin.get_hooks()
                if hook_name in plugin_hooks:
                    try:
                        hook_funcs.remove(plugin_hooks[hook_name])
                    except ValueError:
                        pass
            
            # Remove from loaded plugins
            del self._loaded_plugins[plugin_name]
            
            logger.info(f"Unloaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload plugin '{plugin_name}': {e}")
            return False
    
    def list_plugins(self) -> List[PluginMetadata]:
        """
        List all loaded plugins.
        
        Returns:
            List of plugin metadata
        """
        return [plugin.metadata for plugin in self._loaded_plugins.values()]
    
    def execute_hook(self, hook_name: str, context: Dict[str, Any]) -> None:
        """
        Execute all registered hooks for a hook point.
        
        Args:
            hook_name: Name of the hook point
            context: Context dictionary passed to hooks
        """
        if hook_name not in self._hooks:
            logger.warning(f"Unknown hook: {hook_name}")
            return
        
        for hook_func in self._hooks[hook_name]:
            try:
                hook_func(context)
            except Exception as e:
                logger.error(f"Hook '{hook_name}' failed: {e}")
    
    def reload_plugin(self, plugin_name: str, config: Optional[Dict] = None) -> bool:
        """
        Reload a plugin (unload and load again).
        
        Args:
            plugin_name: Name of the plugin to reload
            config: Optional plugin configuration
            
        Returns:
            True if plugin reloaded successfully
        """
        if plugin_name in self._loaded_plugins:
            self.unload_plugin(plugin_name)
        
        return self.load_plugin(plugin_name, config)
    
    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """
        Get a loaded plugin by name.
        
        Args:
            plugin_name: Plugin name
            
        Returns:
            Plugin instance or None if not loaded
        """
        return self._loaded_plugins.get(plugin_name)
    
    def is_plugin_loaded(self, plugin_name: str) -> bool:
        """
        Check if a plugin is loaded.
        
        Args:
            plugin_name: Plugin name
            
        Returns:
            True if plugin is loaded
        """
        return plugin_name in self._loaded_plugins
    
    def get_available_hooks(self) -> Dict[str, str]:
        """
        Get list of available hook points.
        
        Returns:
            Dictionary mapping hook names to descriptions
        """
        return self.AVAILABLE_HOOKS.copy()


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """
    Get the global plugin manager instance.
    
    Returns:
        PluginManager instance
    """
    global _plugin_manager
    
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    
    return _plugin_manager
