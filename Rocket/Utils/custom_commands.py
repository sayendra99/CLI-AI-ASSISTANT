"""
Custom Commands Module for Rocket CLI

Allows users to define reusable custom commands with templates and aliases.

Features:
- Define custom commands via JSON configuration
- Template support with variables
- Command aliases for shortcuts
- Parameter validation
- Command groups/categories
- Import/export custom commands

Usage:
    from Rocket.Utils.custom_commands import CustomCommandManager
    
    manager = CustomCommandManager()
    
    # Define a custom command
    manager.add_command(
        name="deploy",
        description="Deploy application",
        template="rocket generate 'Deploy {env} environment' --language bash"
    )
    
    # Execute custom command
    manager.execute("deploy", env="production")
"""

import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)


@dataclass
class CustomCommand:
    """Represents a custom user-defined command."""
    name: str
    description: str
    template: str
    aliases: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    category: str = "general"
    enabled: bool = True
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CustomCommand':
        """Create from dictionary."""
        return cls(**data)
    
    def render(self, **kwargs) -> str:
        """
        Render command template with parameters.
        
        Args:
            **kwargs: Template variables
            
        Returns:
            Rendered command string
        """
        # Validate required parameters
        for param_name, param_config in self.parameters.items():
            if param_config.get('required', False) and param_name not in kwargs:
                raise ValueError(f"Required parameter '{param_name}' not provided")
            
            # Use default value if not provided
            if param_name not in kwargs and 'default' in param_config:
                kwargs[param_name] = param_config['default']
        
        # Render template
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")


class CustomCommandManager:
    """
    Manages custom user-defined commands.
    
    Provides command registration, execution, and persistence.
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize custom command manager.
        
        Args:
            config_file: Path to custom commands config file
        """
        self.config_file = config_file or (Path.home() / ".rocket-cli" / "custom_commands.json")
        self._commands: Dict[str, CustomCommand] = {}
        self._aliases: Dict[str, str] = {}  # alias -> command name mapping
        
        # Create directory if needed
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing commands
        self.load()
    
    def add_command(
        self,
        name: str,
        description: str,
        template: str,
        aliases: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        category: str = "general",
        overwrite: bool = False
    ) -> bool:
        """
        Add a custom command.
        
        Args:
            name: Command name
            description: Command description
            template: Command template with {placeholders}
            aliases: List of command aliases
            parameters: Parameter definitions
            category: Command category
            overwrite: Allow overwriting existing command
            
        Returns:
            True if command was added successfully
        """
        # Validate command name
        if not re.match(r'^[a-z][a-z0-9-]*$', name):
            logger.error(f"Invalid command name: {name}. Must start with letter and contain only lowercase letters, numbers, and hyphens.")
            return False
        
        # Check if command exists
        if name in self._commands and not overwrite:
            logger.error(f"Command '{name}' already exists. Use overwrite=True to replace.")
            return False
        
        # Create command
        command = CustomCommand(
            name=name,
            description=description,
            template=template,
            aliases=aliases or [],
            parameters=parameters or {},
            category=category
        )
        
        # Register command
        self._commands[name] = command
        
        # Register aliases
        for alias in command.aliases:
            self._aliases[alias] = name
        
        # Save to disk
        self.save()
        
        logger.info(f"Added custom command: {name}")
        return True
    
    def remove_command(self, name: str) -> bool:
        """
        Remove a custom command.
        
        Args:
            name: Command name
            
        Returns:
            True if command was removed
        """
        if name not in self._commands:
            logger.error(f"Command '{name}' not found")
            return False
        
        command = self._commands[name]
        
        # Remove aliases
        for alias in command.aliases:
            self._aliases.pop(alias, None)
        
        # Remove command
        del self._commands[name]
        
        # Save to disk
        self.save()
        
        logger.info(f"Removed custom command: {name}")
        return True
    
    def get_command(self, name_or_alias: str) -> Optional[CustomCommand]:
        """
        Get a custom command by name or alias.
        
        Args:
            name_or_alias: Command name or alias
            
        Returns:
            CustomCommand or None if not found
        """
        # Try direct name lookup
        if name_or_alias in self._commands:
            return self._commands[name_or_alias]
        
        # Try alias lookup
        if name_or_alias in self._aliases:
            command_name = self._aliases[name_or_alias]
            return self._commands.get(command_name)
        
        return None
    
    def list_commands(self, category: Optional[str] = None) -> List[CustomCommand]:
        """
        List all custom commands.
        
        Args:
            category: Filter by category (optional)
            
        Returns:
            List of custom commands
        """
        commands = list(self._commands.values())
        
        if category:
            commands = [cmd for cmd in commands if cmd.category == category]
        
        return sorted(commands, key=lambda x: x.name)
    
    def get_categories(self) -> List[str]:
        """
        Get list of command categories.
        
        Returns:
            List of unique categories
        """
        categories = set(cmd.category for cmd in self._commands.values())
        return sorted(categories)
    
    def execute(self, name_or_alias: str, **kwargs) -> Optional[str]:
        """
        Execute a custom command.
        
        Args:
            name_or_alias: Command name or alias
            **kwargs: Template parameters
            
        Returns:
            Rendered command string or None if command not found
        """
        command = self.get_command(name_or_alias)
        
        if not command:
            logger.error(f"Command '{name_or_alias}' not found")
            return None
        
        if not command.enabled:
            logger.warning(f"Command '{name_or_alias}' is disabled")
            return None
        
        try:
            return command.render(**kwargs)
        except Exception as e:
            logger.error(f"Failed to execute command '{name_or_alias}': {e}")
            return None
    
    def save(self) -> bool:
        """
        Save custom commands to disk.
        
        Returns:
            True if saved successfully
        """
        try:
            data = {
                "version": "1.0",
                "commands": [cmd.to_dict() for cmd in self._commands.values()]
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save custom commands: {e}")
            return False
    
    def load(self) -> bool:
        """
        Load custom commands from disk.
        
        Returns:
            True if loaded successfully
        """
        if not self.config_file.exists():
            logger.debug("No custom commands file found")
            return True
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            commands = data.get("commands", [])
            self._commands.clear()
            self._aliases.clear()
            
            for cmd_data in commands:
                command = CustomCommand.from_dict(cmd_data)
                self._commands[command.name] = command
                
                # Register aliases
                for alias in command.aliases:
                    self._aliases[alias] = command.name
            
            logger.info(f"Loaded {len(self._commands)} custom commands")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load custom commands: {e}")
            return False
    
    def export_to_file(self, file_path: Path) -> bool:
        """
        Export custom commands to a file.
        
        Args:
            file_path: Path to export file
            
        Returns:
            True if exported successfully
        """
        try:
            data = {
                "version": "1.0",
                "exported_at": str(Path.home()),
                "commands": [cmd.to_dict() for cmd in self._commands.values()]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Exported {len(self._commands)} custom commands to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export custom commands: {e}")
            return False
    
    def import_from_file(self, file_path: Path, merge: bool = True) -> bool:
        """
        Import custom commands from a file.
        
        Args:
            file_path: Path to import file
            merge: If True, merge with existing commands; if False, replace
            
        Returns:
            True if imported successfully
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            commands = data.get("commands", [])
            
            if not merge:
                self._commands.clear()
                self._aliases.clear()
            
            for cmd_data in commands:
                command = CustomCommand.from_dict(cmd_data)
                self._commands[command.name] = command
                
                # Register aliases
                for alias in command.aliases:
                    self._aliases[alias] = command.name
            
            self.save()
            logger.info(f"Imported {len(commands)} custom commands from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import custom commands: {e}")
            return False


# Global custom command manager instance
_manager_instance: Optional[CustomCommandManager] = None


def get_custom_command_manager() -> CustomCommandManager:
    """
    Get the global custom command manager instance.
    
    Returns:
        CustomCommandManager instance
    """
    global _manager_instance
    
    if _manager_instance is None:
        _manager_instance = CustomCommandManager()
    
    return _manager_instance
