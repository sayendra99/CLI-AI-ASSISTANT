"""
Provider Manager - Smart router with automatic fallback logic.

This module provides a unified interface that automatically selects and
falls back between providers based on availability and rate limits.

Priority order:
1. BYOK (user's Gemini API key) - if configured
2. Community proxy (authenticated) - if logged in with GitHub
3. Community proxy (anonymous) - always available, limited
4. Ollama (local) - if running

Example:
    >>> from Rocket.LLM.providers import ProviderManager, GenerateOptions
    >>> 
    >>> manager = ProviderManager()
    >>> await manager.initialize()
    >>> 
    >>> response = await manager.generate(GenerateOptions(prompt="Hello!"))
    >>> print(f"Using {response.provider}: {response.text}")
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional, Type

from Rocket.Utils.Log import get_logger

from .base import (
    LLMProvider,
    GenerateOptions,
    GenerateResponse,
    RateLimitInfo,
    ProviderTier,
    ProviderError,
    RateLimitError,
    ConfigError,
    ProviderUnavailableError,
)
from .gemini import GeminiProvider
from .community_proxy import CommunityProxyProvider
from .ollama import OllamaProvider

logger = get_logger(__name__)


@dataclass
class ProviderStatus:
    """Status information for a provider."""
    provider: LLMProvider
    available: bool = False
    rate_limit: Optional[RateLimitInfo] = None
    last_error: Optional[str] = None
    last_checked: Optional[datetime] = None
    consecutive_failures: int = 0
    
    @property
    def is_rate_limited(self) -> bool:
        """Check if provider is currently rate limited."""
        return self.rate_limit is not None and self.rate_limit.is_limited
    
    @property
    def is_healthy(self) -> bool:
        """Check if provider is healthy (available and not rate limited)."""
        return self.available and not self.is_rate_limited and self.consecutive_failures < 3


@dataclass
class ManagerConfig:
    """Configuration for the provider manager."""
    # API Keys
    gemini_api_key: Optional[str] = None
    github_token: Optional[str] = None
    
    # Provider settings
    ollama_url: Optional[str] = None
    ollama_model: str = "llama3.2"
    community_proxy_url: Optional[str] = None
    default_model: str = "gemini-1.5-flash"  # Gemini model to use
    preferred_provider: Optional[str] = None  # Explicit provider preference: "gemini", "community-proxy", "ollama"
    
    # Behavior settings
    enable_fallback: bool = True
    max_retries: int = 2
    prefer_local: bool = False  # If True, try Ollama before community proxy


class ProviderManager:
    """Smart provider manager with automatic fallback.
    
    Manages multiple LLM providers and automatically routes requests
    to the best available provider, falling back on errors.
    
    Features:
    - Automatic provider selection based on priority
    - Graceful fallback on rate limits and errors
    - Clear error messages with upgrade paths
    - Provider health tracking
    
    Example:
        >>> manager = ProviderManager(config=ManagerConfig(
        ...     gemini_api_key="your-key"
        ... ))
        >>> await manager.initialize()
        >>> 
        >>> # Generate with automatic provider selection
        >>> response = await manager.generate(GenerateOptions(prompt="Hello!"))
        >>> 
        >>> # Check status
        >>> status = await manager.get_status()
        >>> for name, info in status.items():
        ...     print(f"{name}: {'✓' if info.available else '✗'}")
    """
    
    def __init__(self, config: Optional[ManagerConfig] = None):
        """Initialize the provider manager.
        
        Args:
            config: Manager configuration (optional, will use defaults/env)
        """
        self.config = config or ManagerConfig()
        
        # Provider instances (created during initialize)
        self._providers: Dict[str, ProviderStatus] = {}
        
        # Priority order for fallback
        self._priority_order: List[str] = []
        
        # Initialized flag
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all providers and check availability.
        
        Call this before using the manager to set up providers
        and determine which are available.
        """
        logger.debug("Initializing provider manager...")
        
        # Create providers based on config
        providers_to_check: List[LLMProvider] = []
        
        # 1. BYOK Gemini (highest priority if configured)
        if self.config.gemini_api_key:
            providers_to_check.append(
                GeminiProvider(
                    api_key=self.config.gemini_api_key,
                    model=self.config.default_model
                )
            )
        
        # 2. Community proxy (authenticated or anonymous)
        providers_to_check.append(
            CommunityProxyProvider(
                github_token=self.config.github_token,
                base_url=self.config.community_proxy_url,
            )
        )
        
        # 3. Local Ollama (lowest priority, but always available fallback)
        providers_to_check.append(
            OllamaProvider(
                model=self.config.ollama_model,
                base_url=self.config.ollama_url,
            )
        )
        
        # Check availability for all providers concurrently
        availability_checks = [
            self._check_provider(provider)
            for provider in providers_to_check
        ]
        
        results = await asyncio.gather(*availability_checks, return_exceptions=True)
        
        # Store results and build priority order
        for provider, result in zip(providers_to_check, results):
            if isinstance(result, Exception):
                logger.debug(f"Provider {provider.name} check failed: {result}")
                self._providers[provider.name] = ProviderStatus(
                    provider=provider,
                    available=False,
                    last_error=str(result),
                    last_checked=datetime.utcnow(),
                )
            else:
                self._providers[provider.name] = result
        
        # Build priority order based on tier and availability
        self._build_priority_order()
        
        self._initialized = True
        
        # Log status
        available_providers = [
            name for name, status in self._providers.items() 
            if status.available
        ]
        logger.info(f"Provider manager initialized. Available: {available_providers}")
    
    async def _check_provider(self, provider: LLMProvider) -> ProviderStatus:
        """Check a provider's availability and rate limits."""
        try:
            available = await provider.is_available()
            rate_limit = await provider.get_rate_limits() if available else None
            
            return ProviderStatus(
                provider=provider,
                available=available,
                rate_limit=rate_limit,
                last_checked=datetime.utcnow(),
            )
        except Exception as e:
            return ProviderStatus(
                provider=provider,
                available=False,
                last_error=str(e),
                last_checked=datetime.utcnow(),
            )
    
    def _build_priority_order(self) -> None:
        """Build the priority order for provider selection."""
        # If user explicitly set preferred_provider, put it first
        if self.config.preferred_provider:
            preferred = self.config.preferred_provider.lower()
            # Normalize provider names
            provider_map = {
                "gemini": "gemini",
                "community-proxy": "community-proxy",
                "ollama": "ollama",
            }
            
            if preferred in provider_map and provider_map[preferred] in self._providers:
                # Put preferred provider first, others in default order
                preferred_name = provider_map[preferred]
                other_providers = [name for name in self._providers.keys() if name != preferred_name]
                self._priority_order = [preferred_name] + other_providers
                logger.debug(f"Provider priority order (preferred={preferred}): {self._priority_order}")
                return
        
        # Sort by tier priority
        tier_priority = {
            ProviderTier.BYOK: 0,
            ProviderTier.AUTHENTICATED: 1,
            ProviderTier.ANONYMOUS: 2,
            ProviderTier.LOCAL: 3,
        }
        
        # If prefer_local is set, move local higher
        if self.config.prefer_local:
            tier_priority[ProviderTier.LOCAL] = 1
            tier_priority[ProviderTier.AUTHENTICATED] = 2
            tier_priority[ProviderTier.ANONYMOUS] = 3
        
        # Sort providers by tier priority
        sorted_providers = sorted(
            self._providers.items(),
            key=lambda x: tier_priority.get(x[1].provider.tier, 99)
        )
        
        self._priority_order = [name for name, _ in sorted_providers]
        logger.debug(f"Provider priority order: {self._priority_order}")
    
    def _get_next_provider(self, exclude: Optional[List[str]] = None) -> Optional[ProviderStatus]:
        """Get the next available provider based on priority.
        
        Args:
            exclude: List of provider names to skip
            
        Returns:
            Next healthy provider status, or None if all exhausted
        """
        exclude = exclude or []
        
        for name in self._priority_order:
            if name in exclude:
                continue
            
            status = self._providers.get(name)
            if status and status.is_healthy:
                return status
        
        return None
    
    async def generate(self, options: GenerateOptions) -> GenerateResponse:
        """Generate text using the best available provider.
        
        Automatically selects provider and falls back on errors.
        
        Args:
            options: Generation parameters
            
        Returns:
            GenerateResponse from successful provider
            
        Raises:
            ProviderError: If all providers fail
            RateLimitError: If all providers are rate limited
        """
        if not self._initialized:
            await self.initialize()
        
        tried_providers: List[str] = []
        last_error: Optional[Exception] = None
        rate_limit_errors: List[RateLimitError] = []
        
        while True:
            # Get next provider to try
            status = self._get_next_provider(exclude=tried_providers)
            
            if status is None:
                # All providers exhausted
                break
            
            provider = status.provider
            tried_providers.append(provider.name)
            
            logger.debug(f"Trying provider: {provider.name}")
            
            try:
                response = await provider.generate(options)
                
                # Success! Reset failure count
                status.consecutive_failures = 0
                
                # Update rate limit info if provided
                if response.rate_limit:
                    status.rate_limit = response.rate_limit
                
                logger.info(f"Generation successful using {provider.name}")
                return response
                
            except RateLimitError as e:
                logger.warning(f"Provider {provider.name} rate limited: {e}")
                status.consecutive_failures += 1
                status.rate_limit = RateLimitInfo(
                    limit=e.limit or 0,
                    remaining=0,
                    reset_at=e.reset_at,
                    tier=provider.tier,
                )
                rate_limit_errors.append(e)
                last_error = e
                
                if not self.config.enable_fallback:
                    raise
                
            except (ConfigError, ProviderUnavailableError) as e:
                logger.warning(f"Provider {provider.name} unavailable: {e}")
                status.available = False
                status.last_error = str(e)
                status.consecutive_failures += 1
                last_error = e
                
                if not self.config.enable_fallback:
                    raise
                
            except ProviderError as e:
                logger.error(f"Provider {provider.name} error: {e}")
                status.consecutive_failures += 1
                status.last_error = str(e)
                last_error = e
                
                if not self.config.enable_fallback:
                    raise
        
        # All providers failed
        if rate_limit_errors:
            # If we got rate limited, provide helpful error
            error = rate_limit_errors[0]
            raise RateLimitError(
                message=self._build_rate_limit_message(rate_limit_errors),
                provider="all",
                retry_after=error.retry_after,
                upgrade_url=error.upgrade_url,
            )
        
        if last_error:
            raise ProviderError(
                f"All providers failed. Last error: {last_error}",
                provider="all"
            )
        
        raise ProviderError(
            "No providers available. Configure an API key or start Ollama.",
            provider="none"
        )
    
    def _build_rate_limit_message(self, errors: List[RateLimitError]) -> str:
        """Build a helpful rate limit message with upgrade options."""
        messages = [
            "🚦 Rate limit reached on all providers.",
            "",
        ]
        
        # Check what's available
        has_byok = any(
            s.provider.tier == ProviderTier.BYOK 
            for s in self._providers.values() 
            if s.available
        )
        has_github_auth = self.config.github_token is not None
        
        if not has_byok:
            messages.append(
                "💡 Tip: Use your own Gemini API key for unlimited requests:\n"
                "   rocket config set gemini-key YOUR_API_KEY\n"
                "   Get a free key: https://aistudio.google.com/app/apikey"
            )
            messages.append("")
        
        if not has_github_auth:
            messages.append(
                "🔐 Or login with GitHub for 5x more requests (25/day):\n"
                "   rocket login"
            )
            messages.append("")
        
        # Show reset times
        for error in errors:
            if error.reset_at:
                reset_str = error.reset_at.strftime("%H:%M UTC")
                messages.append(f"⏰ Limits reset at: {reset_str}")
                break
        
        return "\n".join(messages)
    
    async def generate_stream(self, options: GenerateOptions) -> AsyncIterator[str]:
        """Generate text with streaming using the best available provider.
        
        Args:
            options: Generation parameters
            
        Yields:
            Chunks of generated text
        """
        if not self._initialized:
            await self.initialize()
        
        # Get best provider
        status = self._get_next_provider()
        
        if status is None:
            raise ProviderError(
                "No providers available for streaming.",
                provider="none"
            )
        
        provider = status.provider
        logger.debug(f"Streaming with provider: {provider.name}")
        
        try:
            async for chunk in provider.generate_stream(options):
                yield chunk
        except RateLimitError as e:
            # Can't easily fallback during streaming
            raise
        except ProviderError as e:
            # Try to fallback to non-streaming
            logger.warning(f"Streaming failed, falling back to non-streaming: {e}")
            options_copy = GenerateOptions(**options.to_dict())
            options_copy.stream = False
            response = await self.generate(options_copy)
            yield response.text
    
    async def get_status(self) -> Dict[str, ProviderStatus]:
        """Get current status of all providers.
        
        Returns:
            Dict mapping provider names to their status
        """
        if not self._initialized:
            await self.initialize()
        
        return self._providers.copy()
    
    async def get_active_provider(self) -> Optional[LLMProvider]:
        """Get the currently active (highest priority available) provider.
        
        Returns:
            The provider that would be used for the next request
        """
        if not self._initialized:
            await self.initialize()
        
        status = self._get_next_provider()
        return status.provider if status else None
    
    async def get_rate_limits(self) -> Dict[str, RateLimitInfo]:
        """Get rate limit info for all providers.
        
        Returns:
            Dict mapping provider names to their rate limit info
        """
        if not self._initialized:
            await self.initialize()
        
        result = {}
        for name, status in self._providers.items():
            if status.rate_limit:
                result[name] = status.rate_limit
            elif status.available:
                try:
                    result[name] = await status.provider.get_rate_limits()
                except:
                    pass
        
        return result
    
    async def refresh(self) -> None:
        """Refresh provider availability and rate limits."""
        logger.debug("Refreshing provider status...")
        
        # Re-check all providers
        checks = []
        for name, status in self._providers.items():
            checks.append(self._check_provider(status.provider))
        
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        for (name, old_status), result in zip(self._providers.items(), results):
            if isinstance(result, Exception):
                old_status.available = False
                old_status.last_error = str(result)
            else:
                self._providers[name] = result
        
        # Rebuild priority order
        self._build_priority_order()
    
    def set_api_key(self, key: str, provider: str = "gemini") -> None:
        """Set an API key for a provider.
        
        Args:
            key: The API key
            provider: Provider name ("gemini")
        """
        if provider == "gemini":
            self.config.gemini_api_key = key
            # Re-create the provider
            self._providers["gemini"] = ProviderStatus(
                provider=GeminiProvider(api_key=key),
                available=True,  # Assume available, will validate on use
            )
            self._build_priority_order()
    
    def set_github_token(self, token: str) -> None:
        """Set GitHub token for authenticated community proxy access.
        
        Args:
            token: GitHub OAuth token
        """
        self.config.github_token = token
        # Re-create the community proxy provider
        self._providers["community-proxy"] = ProviderStatus(
            provider=CommunityProxyProvider(github_token=token),
            available=True,
        )
        self._build_priority_order()
    
    async def close(self) -> None:
        """Close all provider connections."""
        for status in self._providers.values():
            if hasattr(status.provider, '_close_session'):
                try:
                    await status.provider._close_session()
                except:
                    pass


# Singleton instance for easy access
_manager: Optional[ProviderManager] = None


async def get_manager(config: Optional[ManagerConfig] = None) -> ProviderManager:
    """Get or create the global provider manager instance.
    
    Args:
        config: Configuration (only used on first call)
        
    Returns:
        The global ProviderManager instance
    """
    global _manager
    
    if _manager is None:
        _manager = ProviderManager(config)
        await _manager.initialize()
    
    return _manager


def reset_manager() -> None:
    """Reset the global provider manager (useful for testing)."""
    global _manager
    _manager = None
