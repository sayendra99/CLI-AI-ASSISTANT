"""
Operating modes module for Rocket CLI.

Provides different behavioral modes optimized for specific tasks.
"""

from Rocket.MODES.Base import BaseMode, ModeConfig
from Rocket.MODES.Register import ModeRegistry
from Rocket.MODES.Selectors import ModeSelector

# Import concrete modes
from Rocket.MODES.Read_mode import ReadMode
from Rocket.MODES.Debug_mode import DebugMode
from Rocket.MODES.Think_mode import ThinkMode
from Rocket.MODES.Agent_mode import AgentMode
from Rocket.MODES.Enhancement_mode import EnhanceMode
from Rocket.MODES.Analyze_mode import AnalyzeMode

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
