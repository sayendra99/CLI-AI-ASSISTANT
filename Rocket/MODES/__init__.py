"""
Operating modes module for Rocket CLI.

Provides different behavioral modes optimized for specific tasks.
"""

from rocket.modes.base import BaseMode, ModeConfig
from rocket.modes.registry import ModeRegistry
from rocket.modes.selector import ModeSelector

# Import concrete modes
from rocket.modes.read_mode import ReadMode
from rocket.modes.debug_mode import DebugMode
from rocket.modes.think_mode import ThinkMode
from rocket.modes.agent_mode import AgentMode
from rocket.modes.enhance_mode import EnhanceMode
from rocket.modes.analyze_mode import AnalyzeMode

# Create global registry
mode_registry = ModeRegistry()

# Register all modes
mode_registry.register(ReadMode())
mode_registry.register(DebugMode())
mode_registry.register(ThinkMode())
mode_registry.register(AgentMode())
mode_registry.register(EnhanceMode())
mode_registry.register(AnalyzeMode())

__all__ = [
    "BaseMode",
    "ModeConfig",
    "ModeRegistry",
    "ModeSelector",
    "mode_registry",
    # Concrete modes
    "ReadMode",
    "DebugMode",
    "ThinkMode",
    "AgentMode",
    "EnhanceMode",
    "AnalyzeMode",
]
