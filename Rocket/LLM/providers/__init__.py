"""
Rocket LLM Providers - Multi-provider abstraction layer with smart fallback.

This module provides a unified interface for multiple LLM providers:
- Gemini (Google's API with BYOK)
- Community Proxy (api.rocket-cli.dev for free tier)
- Ollama (local LLM inference)

Priority order:
1. BYOK (user's API key) - highest priority
2. Community proxy (authenticated via GitHub)
3. Community proxy (anonymous)
4. Ollama (local fallback)

Example:
    >>> from Rocket.LLM.providers import ProviderManager, load_config
    >>> 
    >>> # Load config and create manager
    >>> config = load_config()
    >>> manager = ProviderManager(config.to_manager_config())
    >>> await manager.initialize()
    >>> 
    >>> # Generate text
    >>> from Rocket.LLM.providers import GenerateOptions
    >>> response = await manager.generate(GenerateOptions(prompt="Hello, world!"))
    >>> print(response.text)
"""

from .base import (
    LLMProvider,
    GenerateOptions,
    GenerateResponse,
    RateLimitInfo,
    UsageInfo,
    ProviderTier,
    ProviderError,
    RateLimitError,
    ConfigError,
    ProviderUnavailableError,
)
from .gemini import GeminiProvider
from .community_proxy import CommunityProxyProvider
from .ollama import OllamaProvider
from .manager import ProviderManager, ManagerConfig, get_manager, reset_manager
from .auth import AuthManager, AuthSession, AuthError, get_auth_manager
from .config import (
    RocketConfig,
    load_config,
    save_config,
    get_config_value,
    set_config_value,
    get_config_path,
    list_config_keys,
    resolve_config_key,
)

__all__ = [
    # Base classes and types
    "LLMProvider",
    "GenerateOptions",
    "GenerateResponse",
    "RateLimitInfo",
    "UsageInfo",
    "ProviderTier",
    # Errors
    "ProviderError",
    "RateLimitError",
    "ConfigError",
    "ProviderUnavailableError",
    # Providers
    "GeminiProvider",
    "CommunityProxyProvider",
    "OllamaProvider",
    # Manager
    "ProviderManager",
    "ManagerConfig",
    "get_manager",
    "reset_manager",
    # Auth
    "AuthManager",
    "AuthSession",
    "AuthError",
    "get_auth_manager",
    # Config
    "RocketConfig",
    "load_config",
    "save_config",
    "get_config_value",
    "set_config_value",
    "get_config_path",
    "list_config_keys",
    "resolve_config_key",
]
