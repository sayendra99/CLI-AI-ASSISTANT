"""
Ollama Provider - Local LLM inference via Ollama.

This provider connects to a locally running Ollama instance for completely
offline LLM usage. Lowest priority but always available fallback.
"""

import asyncio
from datetime import datetime
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
    ProviderUnavailableError,
)

logger = get_logger(__name__)

# Default Ollama API endpoint
OLLAMA_DEFAULT_URL = "http://localhost:11434"


class OllamaProvider(LLMProvider):
    """Local Ollama provider for offline LLM inference.
    
    Features:
    - Completely offline/local operation
    - No API keys required
    - No rate limits
    - Supports various open-source models (llama3, codellama, mistral, etc.)
    
    Requirements:
    - Ollama installed and running locally
    - At least one model pulled (e.g., `ollama pull llama3`)
    
    Example:
        >>> provider = OllamaProvider(model="codellama")
        >>> if await provider.is_available():
        ...     response = await provider.generate(GenerateOptions(prompt="Hello!"))
        ...     print(response.text)
    """
    
    name = "ollama"
    display_name = "Ollama (Local)"
    tier = ProviderTier.LOCAL
    
    # Recommended models for coding tasks
    RECOMMENDED_MODELS = [
        "llama3.2",
        "codellama",
        "deepseek-coder",
        "mistral",
        "phi3",
        "qwen2.5-coder",
    ]
    
    def __init__(
        self,
        model: str = "llama3.2",
        base_url: Optional[str] = None,
        timeout: float = 120.0,  # Local inference can be slow
    ):
        """Initialize the Ollama provider.
        
        Args:
            model: Model name to use (must be pulled in Ollama)
            base_url: Ollama API URL (default: http://localhost:11434)
            timeout: Request timeout in seconds (longer for local inference)
        """
        self.model = model
        self.base_url = base_url or OLLAMA_DEFAULT_URL
        self.timeout = timeout
        
        # HTTP session created lazily
        self._session = None
        
        # Cache available models
        self._available_models: Optional[List[str]] = None
    
    async def _get_session(self):
        """Get or create aiohttp session."""
        if self._session is None:
            try:
                import aiohttp
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                )
            except ImportError:
                raise ProviderError(
                    "aiohttp package not installed. Install with: pip install aiohttp",
                    provider=self.name
                )
        return self._session
    
    async def _close_session(self):
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def is_available(self) -> bool:
        """Check if Ollama is running and has models available.
        
        Verifies:
        1. Ollama API is reachable
        2. At least one model is available
        3. The configured model is available (optional)
        """
        try:
            session = await self._get_session()
            
            # Check if Ollama is running
            async with session.get(f"{self.base_url}/api/tags") as response:
                if response.status != 200:
                    logger.debug(f"Ollama not available: HTTP {response.status}")
                    return False
                
                data = await response.json()
                models = data.get("models", [])
                
                if not models:
                    logger.debug("Ollama available but no models installed")
                    return False
                
                # Cache available models
                self._available_models = [m.get("name", "").split(":")[0] for m in models]
                
                # Check if configured model is available
                model_available = any(
                    self.model in m.get("name", "") 
                    for m in models
                )
                
                if not model_available:
                    logger.debug(
                        f"Ollama available but model '{self.model}' not found. "
                        f"Available: {self._available_models}"
                    )
                    # Still return True - we can suggest models
                    return True
                
                logger.debug(f"Ollama available with model: {self.model}")
                return True
                
        except asyncio.TimeoutError:
            logger.debug("Ollama connection timed out")
            return False
        except Exception as e:
            logger.debug(f"Ollama not available: {e}")
            return False
    
    async def generate(self, options: GenerateOptions) -> GenerateResponse:
        """Generate text using local Ollama.
        
        Args:
            options: Generation parameters
            
        Returns:
            GenerateResponse with generated text
            
        Raises:
            ProviderError: If generation fails
            ProviderUnavailableError: If Ollama is not running
        """
        session = await self._get_session()
        
        # Build prompt with system instruction
        if options.system_instruction:
            full_prompt = f"System: {options.system_instruction}\n\nUser: {options.prompt}"
        else:
            full_prompt = options.prompt
        
        # Build request payload for Ollama API
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": options.temperature,
                "num_predict": options.max_tokens,
            }
        }
        
        if options.stop_sequences:
            payload["options"]["stop"] = options.stop_sequences
        
        try:
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload,
            ) as response:
                if response.status == 404:
                    raise ProviderUnavailableError(
                        f"Model '{self.model}' not found. "
                        f"Pull it with: ollama pull {self.model}",
                        provider=self.name
                    )
                
                if response.status != 200:
                    error_text = await response.text()
                    raise ProviderError(
                        f"Ollama returned HTTP {response.status}: {error_text}",
                        provider=self.name
                    )
                
                data = await response.json()
                
                # Extract response text
                text = data.get("response", "")
                
                # Extract usage info (Ollama provides this)
                usage = UsageInfo(
                    prompt_tokens=data.get("prompt_eval_count", 0),
                    completion_tokens=data.get("eval_count", 0),
                    total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                )
                
                # Determine finish reason
                finish_reason = "stop"
                if data.get("done_reason") == "length":
                    finish_reason = "length"
                
                logger.debug(
                    f"Ollama generation successful: {usage.total_tokens} tokens, "
                    f"eval time: {data.get('eval_duration', 0) / 1e9:.2f}s"
                )
                
                return GenerateResponse(
                    text=text,
                    model=self.model,
                    provider=self.name,
                    usage=usage,
                    finish_reason=finish_reason,
                    raw_response=data,
                )
                
        except ProviderUnavailableError:
            raise
        except ProviderError:
            raise
        except asyncio.TimeoutError:
            raise ProviderUnavailableError(
                f"Ollama request timed out after {self.timeout}s. "
                "Local inference may need more time for large prompts.",
                provider=self.name
            )
        except Exception as e:
            # Check if Ollama is simply not running
            if "Connection refused" in str(e) or "Cannot connect" in str(e):
                raise ProviderUnavailableError(
                    "Ollama is not running. Start it with: ollama serve",
                    provider=self.name
                )
            
            logger.error(f"Ollama generation error: {e}")
            raise ProviderError(f"Generation failed: {e}", provider=self.name)
    
    async def generate_stream(self, options: GenerateOptions) -> AsyncIterator[str]:
        """Generate text with streaming response.
        
        Args:
            options: Generation parameters
            
        Yields:
            Chunks of generated text
        """
        session = await self._get_session()
        
        # Build prompt with system instruction
        if options.system_instruction:
            full_prompt = f"System: {options.system_instruction}\n\nUser: {options.prompt}"
        else:
            full_prompt = options.prompt
        
        # Build request payload with streaming enabled
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": True,
            "options": {
                "temperature": options.temperature,
                "num_predict": options.max_tokens,
            }
        }
        
        try:
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload,
            ) as response:
                if response.status != 200:
                    # Fall back to non-streaming
                    result = await self.generate(options)
                    yield result.text
                    return
                
                # Stream NDJSON responses
                import json
                async for line in response.content:
                    line = line.decode("utf-8").strip()
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.debug(f"Ollama streaming failed, falling back: {e}")
            result = await self.generate(options)
            yield result.text
    
    async def get_rate_limits(self) -> RateLimitInfo:
        """Get rate limit info for Ollama.
        
        Ollama has no rate limits - it's local!
        """
        return RateLimitInfo(
            limit=999999,  # Essentially unlimited
            remaining=999999,
            period="unlimited",
            tier=self.tier,
        )
    
    async def get_models(self) -> List[str]:
        """List available models from Ollama."""
        if self._available_models:
            return self._available_models
        
        try:
            session = await self._get_session()
            
            async with session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    self._available_models = [
                        m.get("name", "").split(":")[0] 
                        for m in data.get("models", [])
                    ]
                    return self._available_models
                    
        except Exception as e:
            logger.debug(f"Failed to list Ollama models: {e}")
        
        return self.RECOMMENDED_MODELS
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama library.
        
        Args:
            model_name: Name of model to pull
            
        Returns:
            True if successful
        """
        session = await self._get_session()
        
        try:
            async with session.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully pulled model: {model_name}")
                    return True
                else:
                    logger.error(f"Failed to pull model {model_name}: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False
    
    def __del__(self):
        """Cleanup on deletion."""
        if self._session and not self._session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._close_session())
            except:
                pass
