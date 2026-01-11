"""
Rocket CLI Module
Command-line interface for Rocket AI Assistant
"""

from .Main import app, main, chat, generate, explain, debug, optimize, version, config

__all__ = [
    "app",
    "main",
    "chat",
    "generate",
    "explain",
    "debug",
    "optimize",
    "version",
    "config",
]

__version__ = "0.1.0"
__author__ = "Rocket Team"
__description__ = "AI-Powered CLI Assistant for Developers"
