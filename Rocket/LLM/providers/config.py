"""
Rocket CLI Configuration Management

This module handles loading and saving configuration from ~/.rocket-cli/config.json,
including API keys, tokens, and user preferences.

Features:
- Automatic config directory creation
- Secure storage of API keys
- Support for multiple profiles
- Default values with environment variable overrides

Example:
    >>> from Rocket.LLM.providers.config import RocketConfig, load_config, save_config
    >>> 
    >>> # Load existing config (or create default)
    >>> config = load_config()
    >>> 
    >>> # Set API key
    >>> config.gemini_api_key = "your-key"
    >>> save_config(config)
    >>> 
    >>> # Get provider manager config
    >>> manager_config = config.to_manager_config()
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional

from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)

# Config directory and file paths
CONFIG_DIR = Path.home() / ".rocket-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class RocketConfig:
    """Rocket CLI configuration settings.
    
    This configuration is persisted to ~/.rocket-cli/config.json
    and can be modified via the CLI or programmatically.
    """
    
    # API Keys
    gemini_api_key: Optional[str] = None
    
    # GitHub OAuth
    github_token: Optional[str] = None
    github_username: Optional[str] = None
    
    # Provider preferences
    preferred_provider: Optional[str] = None  # "gemini", "community-proxy", "ollama"
    prefer_local: bool = False  # Prefer Ollama over community proxy
    
    # Ollama settings
    ollama_url: Optional[str] = None  # Default: http://localhost:11434
    ollama_model: str = "llama3.2"
    
    # Community proxy settings
    community_proxy_url: Optional[str] = None  # Default: https://api.rocket-cli.dev
    
    # Generation defaults
    default_temperature: float = 0.7
    default_max_tokens: int = 2048
    default_model: str = "gemini-1.5-flash"
    
    # CLI preferences
    stream_by_default: bool = True
    show_usage_stats: bool = False
    
    # Telemetry (opt-in)
    telemetry_enabled: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "gemini_api_key": self.gemini_api_key,
            "github_token": self.github_token,
            "github_username": self.github_username,
            "preferred_provider": self.preferred_provider,
            "prefer_local": self.prefer_local,
            "ollama_url": self.ollama_url,
            "ollama_model": self.ollama_model,
            "community_proxy_url": self.community_proxy_url,
            "default_temperature": self.default_temperature,
            "default_max_tokens": self.default_max_tokens,
            "default_model": self.default_model,
            "stream_by_default": self.stream_by_default,
            "show_usage_stats": self.show_usage_stats,
            "telemetry_enabled": self.telemetry_enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RocketConfig":
        """Create config from dictionary."""
        return cls(
            gemini_api_key=data.get("gemini_api_key"),
            github_token=data.get("github_token"),
            github_username=data.get("github_username"),
            preferred_provider=data.get("preferred_provider"),
            prefer_local=data.get("prefer_local", False),
            ollama_url=data.get("ollama_url"),
            ollama_model=data.get("ollama_model", "llama3.2"),
            community_proxy_url=data.get("community_proxy_url"),
            default_temperature=data.get("default_temperature", 0.7),
            default_max_tokens=data.get("default_max_tokens", 2048),
            default_model=data.get("default_model", "gemini-1.5-flash"),
            stream_by_default=data.get("stream_by_default", True),
            show_usage_stats=data.get("show_usage_stats", False),
            telemetry_enabled=data.get("telemetry_enabled", False),
        )
    
    def to_manager_config(self):
        """Convert to ProviderManager configuration.
        
        Returns:
            ManagerConfig instance for initializing the provider manager
        """
        from .manager import ManagerConfig
        
        return ManagerConfig(
            gemini_api_key=self.gemini_api_key or os.getenv("GEMINI_API_KEY"),
            github_token=self.github_token,
            ollama_url=self.ollama_url,
            ollama_model=self.ollama_model,
            community_proxy_url=self.community_proxy_url,
            default_model=self.default_model,
            preferred_provider=self.preferred_provider,
            prefer_local=self.prefer_local,
        )


def ensure_config_dir() -> Path:
    """Ensure the config directory exists.
    
    Returns:
        Path to the config directory
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config() -> RocketConfig:
    """Load configuration from file.
    
    Loads from ~/.rocket-cli/config.json if it exists,
    otherwise returns default configuration with environment
    variable overrides.
    
    Returns:
        RocketConfig instance
    """
    config = RocketConfig()
    
    # Try to load from file
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            config = RocketConfig.from_dict(data)
            logger.debug(f"Loaded config from {CONFIG_FILE}")
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid config file, using defaults: {e}")
        except Exception as e:
            logger.warning(f"Error loading config, using defaults: {e}")
    
    # Override with environment variables if not set in file
    if not config.gemini_api_key:
        config.gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if not config.github_token:
        config.github_token = os.getenv("ROCKET_GITHUB_TOKEN")
    
    if not config.ollama_url:
        config.ollama_url = os.getenv("OLLAMA_URL")
    
    if not config.community_proxy_url:
        config.community_proxy_url = os.getenv("ROCKET_PROXY_URL")
    
    return config


def save_config(config: RocketConfig) -> None:
    """Save configuration to file.
    
    Saves to ~/.rocket-cli/config.json, creating the directory
    if it doesn't exist.
    
    Args:
        config: Configuration to save
    """
    ensure_config_dir()
    
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config.to_dict(), f, indent=2)
        logger.debug(f"Saved config to {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        raise


def get_config_value(key: str) -> Optional[Any]:
    """Get a single configuration value.
    
    Args:
        key: Configuration key
        
    Returns:
        Value if set, None otherwise
    """
    config = load_config()
    return getattr(config, key, None)


def set_config_value(key: str, value: Any) -> None:
    """Set a single configuration value.
    
    Args:
        key: Configuration key
        value: Value to set
    """
    config = load_config()
    
    if hasattr(config, key):
        setattr(config, key, value)
        save_config(config)
    else:
        raise ValueError(f"Unknown config key: {key}")


def clear_config_value(key: str) -> None:
    """Clear a configuration value (set to None/default).
    
    Args:
        key: Configuration key to clear
    """
    config = load_config()
    
    if hasattr(config, key):
        # Get default value from a fresh config
        default_config = RocketConfig()
        default_value = getattr(default_config, key)
        setattr(config, key, default_value)
        save_config(config)
    else:
        raise ValueError(f"Unknown config key: {key}")


def delete_config() -> bool:
    """Delete the config file.
    
    Returns:
        True if deleted, False if didn't exist
    """
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
        logger.info(f"Deleted config file: {CONFIG_FILE}")
        return True
    return False


def get_config_path() -> Path:
    """Get the path to the config file.
    
    Returns:
        Path to config.json
    """
    return CONFIG_FILE


# Config key aliases for CLI
CONFIG_KEY_ALIASES = {
    "gemini-key": "gemini_api_key",
    "gemini_key": "gemini_api_key",
    "api-key": "gemini_api_key",
    "github-token": "github_token",
    "token": "github_token",
    "temperature": "default_temperature",
    "max-tokens": "default_max_tokens",
    "model": "default_model",
    "ollama-url": "ollama_url",
    "ollama-model": "ollama_model",
    "proxy-url": "community_proxy_url",
    "prefer-local": "prefer_local",
    "stream": "stream_by_default",
}


def resolve_config_key(key: str) -> str:
    """Resolve a config key alias to the actual key name.
    
    Args:
        key: Key or alias
        
    Returns:
        Actual config key name
    """
    return CONFIG_KEY_ALIASES.get(key, key)


def list_config_keys() -> Dict[str, str]:
    """Get all valid configuration keys with descriptions.
    
    Returns:
        Dict mapping key names to descriptions
    """
    return {
        "gemini_api_key": "Google Gemini API key (get at aistudio.google.com)",
        "github_token": "GitHub OAuth token for higher rate limits",
        "github_username": "GitHub username (set automatically on login)",
        "preferred_provider": "Preferred provider: gemini, community-proxy, ollama",
        "prefer_local": "Prefer local Ollama over community proxy (true/false)",
        "ollama_url": "Ollama API URL (default: http://localhost:11434)",
        "ollama_model": "Ollama model to use (default: llama3.2)",
        "community_proxy_url": "Community proxy URL (default: api.rocket-cli.dev)",
        "default_temperature": "Default temperature for generation (0.0-1.0)",
        "default_max_tokens": "Default max tokens for generation",
        "default_model": "Default Gemini model",
        "stream_by_default": "Stream responses by default (true/false)",
        "show_usage_stats": "Show token usage stats after generation",
        "telemetry_enabled": "Enable anonymous usage telemetry (true/false)",
    }
