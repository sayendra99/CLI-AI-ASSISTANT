"""
Rocket - AI-Powered Coding Assistant
Professional CLI tool for developers with LLM integration
"""

__version__ = "0.1.0"
__author__ = "Rocket Team"
__description__ = "AI-Powered Coding Assistant CLI"

# Import main modules
from Rocket.LLM import GeminiClient, LLMResponse, LLMERROR, UsageMetadata
from Rocket.CLI import app, main

__all__ = [
    "GeminiClient",
    "LLMResponse",
    "LLMERROR",
    "UsageMetadata",
    "app",
    "main",
]

