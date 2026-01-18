"""
Base classes and interfaces for LLM providers.

This module defines the core abstractions for the multi-provider LLM layer:
- LLMProvider: Abstract base class for all providers
- Custom exceptions for error handling
- Type definitions for requests and responses
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional


# =============================================================================
# Custom Exceptions
# =============================================================================

class ProviderError(Exception):
    """Base exception for all provider-related errors."""
    
    def __init__(self, message: str, provider: str = "unknown", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.provider = provider
        self.details = details or {}
        super().__init__(f"[{provider}] {message}")


class RateLimitError(ProviderError):
    """Raised when rate limit is exceeded.
    
    Includes information about when the limit resets and upgrade options.
    """
    
    def __init__(
        self,
        message: str,
        provider: str = "unknown",
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        remaining: Optional[int] = None,
        reset_at: Optional[datetime] = None,
        upgrade_url: Optional[str] = None,
    ):
        super().__init__(message, provider)
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining
        self.reset_at = reset_at
        self.upgrade_url = upgrade_url
    
    def get_upgrade_message(self) -> str:
        """Return a user-friendly message about upgrading."""
        if self.upgrade_url:
            return f"🚀 Upgrade for higher limits: {self.upgrade_url}"
        return "💡 Tip: Use your own API key (rocket config set gemini-key YOUR_KEY) for unlimited requests"


class ConfigError(ProviderError):
    """Raised when there's a configuration issue (missing keys, invalid config)."""
    pass


class ProviderUnavailableError(ProviderError):
    """Raised when a provider is not available (network, service down)."""
    pass


# =============================================================================
# Type Definitions
# =============================================================================

class ProviderTier(str, Enum):
    """Provider authentication tier levels."""
    BYOK = "byok"           # Bring Your Own Key - highest priority
    AUTHENTICATED = "auth"   # GitHub authenticated
    ANONYMOUS = "anon"       # Anonymous/free tier
    LOCAL = "local"          # Local Ollama


@dataclass
class RateLimitInfo:
    """Information about current rate limit status."""
    limit: int = 0              # Total requests allowed in period
    remaining: int = 0          # Requests remaining
    reset_at: Optional[datetime] = None  # When limit resets
    period: str = "day"         # Period type (day, hour, minute)
    tier: ProviderTier = ProviderTier.ANONYMOUS
    
    @property
    def is_limited(self) -> bool:
        """Check if rate limit has been reached."""
        return self.remaining <= 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "limit": self.limit,
            "remaining": self.remaining,
            "reset_at": self.reset_at.isoformat() if self.reset_at else None,
            "period": self.period,
            "tier": self.tier.value,
        }


@dataclass
class GenerateOptions:
    """Options for text generation requests."""
    prompt: str
    system_instruction: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    stop_sequences: List[str] = field(default_factory=list)
    stream: bool = False
    
    # Tool calling support
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None  # "auto", "none", or specific tool name
    
    # Context/history for multi-turn
    messages: Optional[List[Dict[str, str]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests."""
        return {
            "prompt": self.prompt,
            "system_instruction": self.system_instruction,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stop_sequences": self.stop_sequences,
            "stream": self.stream,
            "tools": self.tools,
            "tool_choice": self.tool_choice,
            "messages": self.messages,
        }


@dataclass
class UsageInfo:
    """Token usage information from a generation request."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class GenerateResponse:
    """Response from a text generation request."""
    text: str
    model: str
    provider: str
    usage: UsageInfo = field(default_factory=UsageInfo)
    finish_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Rate limit info (from community proxy)
    rate_limit: Optional[RateLimitInfo] = None
    
    # Tool calls (if using function calling)
    tool_calls: Optional[List[Dict[str, Any]]] = None
    
    # Raw response for debugging
    raw_response: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "text": self.text,
            "model": self.model,
            "provider": self.provider,
            "usage": self.usage.to_dict(),
            "finish_reason": self.finish_reason,
            "timestamp": self.timestamp.isoformat(),
            "rate_limit": self.rate_limit.to_dict() if self.rate_limit else None,
            "tool_calls": self.tool_calls,
        }


# =============================================================================
# Abstract Base Provider
# =============================================================================

class LLMProvider(ABC):
    """Abstract base class for all LLM providers.
    
    All providers must implement:
    - generate(): Async text generation
    - is_available(): Check if provider can be used
    - get_rate_limits(): Get current rate limit status
    
    Providers may optionally implement:
    - generate_stream(): Streaming text generation
    - get_models(): List available models
    """
    
    # Provider identification
    name: str = "base"
    display_name: str = "Base Provider"
    tier: ProviderTier = ProviderTier.ANONYMOUS
    
    @abstractmethod
    async def generate(self, options: GenerateOptions) -> GenerateResponse:
        """Generate text from the LLM.
        
        Args:
            options: Generation parameters including prompt, temperature, etc.
            
        Returns:
            GenerateResponse with the generated text and metadata
            
        Raises:
            RateLimitError: If rate limit exceeded
            ProviderError: If generation fails
            ConfigError: If provider not configured
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this provider is currently available.
        
        Should verify:
        - Required API keys/tokens are configured
        - Network connectivity (optional quick check)
        - Service is not in maintenance
        
        Returns:
            True if provider can handle requests
        """
        pass
    
    @abstractmethod
    async def get_rate_limits(self) -> RateLimitInfo:
        """Get current rate limit status for this provider.
        
        Returns:
            RateLimitInfo with current usage and limits
        """
        pass
    
    async def generate_stream(self, options: GenerateOptions) -> AsyncIterator[str]:
        """Generate text with streaming response.
        
        Default implementation calls generate() and yields the full response.
        Override for true streaming support.
        
        Args:
            options: Generation parameters
            
        Yields:
            Chunks of generated text
        """
        response = await self.generate(options)
        yield response.text
    
    async def get_models(self) -> List[str]:
        """List available models for this provider.
        
        Returns:
            List of model identifiers
        """
        return []
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} tier={self.tier.value}>"
