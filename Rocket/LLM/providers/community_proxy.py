"""
Community Proxy Provider - Free tier access via rocket-cli proxy service.

This provider connects to api.rocket-cli.dev for users without their own API keys.
Supports both anonymous (5 req/day) and GitHub authenticated (25 req/day) tiers.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional

from Rocket.Utils.Log import get_logger

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
from .auth import get_auth_manager

logger = get_logger(__name__)

# Community proxy base URL
PROXY_BASE_URL = "https://api.rocket-cli.dev"
# Fallback for local development
PROXY_DEV_URL = "http://localhost:3000"


class CommunityProxyProvider(LLMProvider):
    """Community proxy provider for free tier access.
    
    Rate limits:
    - Anonymous (by IP): 5 requests/day
    - GitHub authenticated: 25 requests/day
    
    Features:
    - No API key required for basic usage
    - GitHub OAuth for higher limits
    - Clear rate limit information in responses
    - Automatic upgrade path suggestions
    
    Example:
        >>> # Anonymous usage
        >>> provider = CommunityProxyProvider()
        >>> 
        >>> # Authenticated usage (higher limits)
        >>> provider = CommunityProxyProvider(github_token="gho_xxx")
    """
    
    name = "community-proxy"
    display_name = "Rocket Community (Free)"
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        auto_auth: bool = True,
    ):
        """Initialize the community proxy provider.
        
        Args:
            github_token: GitHub OAuth token for authenticated tier
            base_url: Override proxy URL (for dev/testing)
            timeout: Request timeout in seconds
            auto_auth: Automatically load auth from storage if not provided
        """
        # Try to load auth from storage if not explicitly provided
        if github_token is None and auto_auth:
            github_token = self._load_stored_auth()
        
        self.github_token = github_token
        self.base_url = base_url or PROXY_BASE_URL
        self.timeout = timeout
        
        # Set tier based on authentication
        self.tier = ProviderTier.AUTHENTICATED if github_token else ProviderTier.ANONYMOUS
        
        # Cache rate limit info
        self._cached_rate_limit: Optional[RateLimitInfo] = None
        self._rate_limit_fetched_at: Optional[datetime] = None
        
        # HTTP session will be created lazily
        self._session = None
        
        if self.github_token:
            logger.debug("Community proxy initialized with authentication (25 req/day)")
        else:
            logger.debug("Community proxy initialized in anonymous mode (5 req/day)")
    
    def _load_stored_auth(self) -> Optional[str]:
        """Load session token from auth storage if available."""
        try:
            auth_manager = get_auth_manager()
            session_data = auth_manager.get_stored_session()
            if session_data:
                token = session_data.get('session_token')
                if token:
                    logger.debug(f"Loaded auth for user: {session_data.get('username', 'unknown')}")
                    return token
        except Exception as e:
            logger.debug(f"Could not load stored auth: {e}")
        return None
    
    async def _get_session(self):
        """Get or create aiohttp session."""
        if self._session is None:
            try:
                import aiohttp
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                )
            except ImportError:
                raise ConfigError(
                    "aiohttp package not installed. Install with: pip install aiohttp",
                    provider=self.name
                )
        return self._session
    
    async def close(self):
        """Close the HTTP session properly."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            self._session = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers including auth if available."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "rocket-cli/1.0",
        }
        
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        
        return headers
    
    async def is_available(self) -> bool:
        """Check if community proxy is reachable.
        
        Performs a quick health check to the proxy service.
        """
        try:
            session = await self._get_session()
            
            async with session.get(
                f"{self.base_url}/health",
                headers=self._get_headers(),
            ) as response:
                if response.status == 200:
                    logger.debug("Community proxy is available")
                    return True
                else:
                    logger.debug(f"Community proxy health check failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.debug(f"Community proxy not available: {e}")
            # Don't fail completely - proxy might work even if health check fails
            return True  # Optimistic - will fail gracefully on actual request
    
    async def generate(self, options: GenerateOptions) -> GenerateResponse:
        """Generate text via community proxy.
        
        Args:
            options: Generation parameters
            
        Returns:
            GenerateResponse with generated text and rate limit info
            
        Raises:
            RateLimitError: If daily limit exceeded
            ProviderError: If generation fails
        """
        session = await self._get_session()
        
        # Build request payload
        payload = {
            "prompt": options.prompt,
            "temperature": options.temperature,
            "maxTokens": options.max_tokens,
        }
        
        if options.system_instruction:
            payload["systemInstruction"] = options.system_instruction
        
        if options.messages:
            payload["messages"] = options.messages
        
        try:
            async with session.post(
                f"{self.base_url}/v1/generate",
                json=payload,
                headers=self._get_headers(),
            ) as response:
                # Parse response
                data = await response.json()
                
                # Handle rate limit errors
                if response.status == 429:
                    rate_limit = self._parse_rate_limit(response.headers, data)
                    self._cached_rate_limit = rate_limit
                    
                    raise RateLimitError(
                        message=data.get("error", "Rate limit exceeded"),
                        provider=self.name,
                        retry_after=rate_limit.reset_at.timestamp() - datetime.utcnow().timestamp() if rate_limit.reset_at else 86400,
                        limit=rate_limit.limit,
                        remaining=0,
                        reset_at=rate_limit.reset_at,
                        upgrade_url="https://rocket-cli.dev/upgrade" if not self.github_token else None,
                    )
                
                # Handle other errors
                if response.status != 200:
                    error_msg = data.get("error", f"HTTP {response.status}")
                    
                    if response.status == 401:
                        raise ConfigError(
                            "Invalid or expired GitHub token. Run: rocket login",
                            provider=self.name
                        )
                    elif response.status == 503:
                        raise ProviderUnavailableError(
                            "Community proxy is temporarily unavailable. Try again later.",
                            provider=self.name
                        )
                    else:
                        raise ProviderError(error_msg, provider=self.name)
                
                # Parse successful response
                text = data.get("text", "")
                model = data.get("model", "gemini-1.5-flash")
                
                # Parse usage info
                usage_data = data.get("usage", {})
                usage = UsageInfo(
                    prompt_tokens=usage_data.get("promptTokens", 0),
                    completion_tokens=usage_data.get("completionTokens", 0),
                    total_tokens=usage_data.get("totalTokens", 0),
                )
                
                # Parse rate limit info from response
                rate_limit = self._parse_rate_limit(response.headers, data)
                self._cached_rate_limit = rate_limit
                self._rate_limit_fetched_at = datetime.utcnow()
                
                logger.debug(
                    f"Community proxy generation successful. "
                    f"Remaining: {rate_limit.remaining}/{rate_limit.limit}"
                )
                
                return GenerateResponse(
                    text=text,
                    model=model,
                    provider=self.name,
                    usage=usage,
                    finish_reason=data.get("finishReason"),
                    rate_limit=rate_limit,
                    raw_response=data,
                )
                
        except RateLimitError:
            raise
        except ConfigError:
            raise
        except ProviderUnavailableError:
            raise
        except ProviderError:
            raise
        except asyncio.TimeoutError:
            raise ProviderUnavailableError(
                f"Request timed out after {self.timeout}s. The proxy may be overloaded.",
                provider=self.name
            )
        except Exception as e:
            logger.error(f"Community proxy error: {e}")
            raise ProviderError(f"Request failed: {e}", provider=self.name)
    
    async def generate_stream(self, options: GenerateOptions) -> AsyncIterator[str]:
        """Generate text with streaming (simulated).
        
        Note: Community proxy may not support true streaming.
        Falls back to returning full response.
        """
        # Try streaming endpoint first
        session = await self._get_session()
        
        payload = {
            "prompt": options.prompt,
            "temperature": options.temperature,
            "maxTokens": options.max_tokens,
            "stream": True,
        }
        
        if options.system_instruction:
            payload["systemInstruction"] = options.system_instruction
        
        try:
            async with session.post(
                f"{self.base_url}/v1/generate",
                json=payload,
                headers=self._get_headers(),
            ) as response:
                if response.status == 429:
                    data = await response.json()
                    rate_limit = self._parse_rate_limit(response.headers, data)
                    raise RateLimitError(
                        message=data.get("error", "Rate limit exceeded"),
                        provider=self.name,
                        limit=rate_limit.limit,
                        remaining=0,
                    )
                
                if response.status != 200:
                    # Fall back to non-streaming
                    response_data = await self.generate(options)
                    yield response_data.text
                    return
                
                # Check if response is SSE
                content_type = response.headers.get("content-type", "")
                
                if "text/event-stream" in content_type:
                    # True SSE streaming
                    async for line in response.content:
                        line = line.decode("utf-8").strip()
                        if line.startswith("data: "):
                            data = line[6:]
                            if data != "[DONE]":
                                try:
                                    import json
                                    chunk = json.loads(data)
                                    if "text" in chunk:
                                        yield chunk["text"]
                                except:
                                    yield data
                else:
                    # Non-streaming response
                    data = await response.json()
                    yield data.get("text", "")
                    
        except RateLimitError:
            raise
        except Exception as e:
            # Fall back to non-streaming
            logger.debug(f"Streaming failed, falling back to non-streaming: {e}")
            response = await self.generate(options)
            yield response.text
    
    def _parse_rate_limit(self, headers: Dict, data: Dict) -> RateLimitInfo:
        """Parse rate limit info from response headers and body."""
        # Try to get from response body first (more reliable)
        usage_data = data.get("usage", {})
        
        limit = usage_data.get("limit", 5 if not self.github_token else 25)
        remaining = usage_data.get("remaining", limit)
        reset_timestamp = usage_data.get("reset")
        
        # Fall back to headers
        if "X-RateLimit-Limit" in headers:
            limit = int(headers["X-RateLimit-Limit"])
        if "X-RateLimit-Remaining" in headers:
            remaining = int(headers["X-RateLimit-Remaining"])
        if "X-RateLimit-Reset" in headers:
            reset_timestamp = int(headers["X-RateLimit-Reset"])
        
        # Calculate reset time
        reset_at = None
        if reset_timestamp:
            reset_at = datetime.fromtimestamp(reset_timestamp)
        else:
            # Default: reset at midnight UTC
            now = datetime.utcnow()
            reset_at = datetime(now.year, now.month, now.day) + timedelta(days=1)
        
        return RateLimitInfo(
            limit=limit,
            remaining=remaining,
            reset_at=reset_at,
            period="day",
            tier=self.tier,
        )
    
    async def get_rate_limits(self) -> RateLimitInfo:
        """Get current rate limit status.
        
        Returns cached info if recent, otherwise fetches from /v1/limits endpoint.
        """
        # Return cached if fresh (< 1 minute old)
        if (
            self._cached_rate_limit 
            and self._rate_limit_fetched_at 
            and (datetime.utcnow() - self._rate_limit_fetched_at).seconds < 60
        ):
            return self._cached_rate_limit
        
        # Fetch fresh rate limit info
        try:
            session = await self._get_session()
            
            async with session.get(
                f"{self.base_url}/v1/limits",
                headers=self._get_headers(),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    rate_limit = self._parse_rate_limit(response.headers, data)
                    self._cached_rate_limit = rate_limit
                    self._rate_limit_fetched_at = datetime.utcnow()
                    return rate_limit
                    
        except Exception as e:
            logger.debug(f"Failed to fetch rate limits: {e}")
        
        # Return default limits
        limit = 25 if self.github_token else 5
        return RateLimitInfo(
            limit=limit,
            remaining=limit,
            period="day",
            tier=self.tier,
        )
    
    async def get_models(self) -> List[str]:
        """List available models through the proxy."""
        # Community proxy uses Gemini on backend
        return ["gemini-1.5-flash"]
    
    def __del__(self):
        """Cleanup on deletion."""
        if self._session and not self._session.closed:
            # Can't await in __del__, so schedule cleanup
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._close_session())
            except:
                pass
