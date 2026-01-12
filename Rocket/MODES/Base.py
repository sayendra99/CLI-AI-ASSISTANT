"""
Base mode interface and configuration.

All modes must inherit from BaseMode.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)


@dataclass
class ModeConfig:
    """
    Configuration for an operating mode.
    
    Attributes:
        name: Mode identifier (e.g., "READ", "DEBUG")
        description: Human-readable description
        temperature: LLM creativity (0.0-1.0)
        max_tokens: Maximum response length
        tools_allowed: List of tool names this mode can use
        requires_git_branch: Whether to auto-create git branch
        system_prompt: LLM instruction for this mode
        icon: Emoji/icon for display
    """
    name: str
    description: str
    temperature: float
    max_tokens: int
    tools_allowed: List[str] = field(default_factory=list)
    requires_git_branch: bool = False
    system_prompt: Optional[str] = None
    icon: str = "🚀"
    
    def __post_init__(self):
        """Validate configuration."""
        # Validate temperature
        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError(f"Temperature must be 0.0-1.0, got {self.temperature}")
        
        # Validate max_tokens
        if self.max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {self.max_tokens}")
        
        # Validate name
        if not self.name:
            raise ValueError("Mode name cannot be empty")
        
        logger.debug(f"Created ModeConfig: {self.name}")


class BaseMode(ABC):
    """
    Abstract base class for all operating modes.
    
    All modes must implement:
    - config property: Return ModeConfig
    - get_llm_settings(): Return LLM configuration
    - is_tool_allowed(): Check if tool is permitted
    """
    
    @property
    @abstractmethod
    def config(self) -> ModeConfig:
        """
        Get mode configuration.
        
        Returns:
            ModeConfig instance
        """
        pass
    
    def get_llm_settings(self) -> Dict[str, Any]:
        """
        Get LLM client settings for this mode.
        
        Returns:
            Dictionary with LLM settings
        """
        return {
            "temperature": self.config.temperature,
            "max_output_tokens": self.config.max_tokens,
            "system_instruction": self.config.system_prompt,
        }
    
    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        Check if a tool is allowed in this mode.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if tool is allowed
        """
        # Special case: "ALL" means all tools allowed
        if "ALL" in self.config.tools_allowed:
            return True
        
        return tool_name in self.config.tools_allowed
    
    def get_allowed_tools(self) -> List[str]:
        """
        Get list of allowed tools.
        
        Returns:
            List of tool names
        """
        return self.config.tools_allowed.copy()
    
    def needs_git_branch(self) -> bool:
        """
        Check if this mode requires git branch creation.
        
        Returns:
            True if git branch should be created
        """
        return self.config.requires_git_branch
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.config.icon} {self.config.name}: {self.config.description}"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"<{self.__class__.__name__} (name='{self.config.name}')>"
    
    def get_name(self) -> str:
        """Get mode name."""
        return self.config.name
    
    def get_description(self) -> str:
        """Get mode description."""
        return self.config.description
    
    def get_icon(self) -> str:
        """Get mode icon."""
        return self.config.icon
