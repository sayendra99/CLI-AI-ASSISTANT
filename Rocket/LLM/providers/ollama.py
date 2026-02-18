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
    
    # Best free coding models for 2026 - Optimized for Rocket CLI
    # Listed in recommended order (best quality to fastest)
    RECOMMENDED_MODELS = [
        "qwen2.5-coder:7b",          # BEST: State-of-the-art coding model (Jan 2025)
        "qwen2.5-coder:14b",         # Highest quality for powerful systems
        "deepseek-coder-v2:16b",     # Excellent code generation and understanding
        "codegemma:7b",              # Google's specialized code model
        "codellama:13b",             # Meta's proven coding specialist
        "qwen2.5-coder:3b",          # Fast, good for moderate systems
        "phi3.5:latest",             # Microsoft's efficient small model
        "deepseek-coder:6.7b",       # Balanced performance
        "codellama:7b",              # Reliable fallback
        "qwen2.5-coder:1.5b",        # Ultra-fast for low-end systems
    ]
    
    # Model metadata for intelligent selection
    MODEL_INFO = {
        "qwen2.5-coder:7b": {
            "params": "7B",
            "ram_min": 10,
            "ram_optimal": 16,
            "specialty": "Best all-around coding model",
            "size_gb": 4.7,
            "speed": "fast",
        },
        "qwen2.5-coder:14b": {
            "params": "14B",
            "ram_min": 20,
            "ram_optimal": 32,
            "specialty": "Highest quality, complex code tasks",
            "size_gb": 8.9,
            "speed": "medium",
        },
        "qwen2.5-coder:3b": {
            "params": "3B",
            "ram_min": 6,
            "ram_optimal": 8,
            "specialty": "Fast responses, good quality",
            "size_gb": 2.0,
            "speed": "very_fast",
        },
        "qwen2.5-coder:1.5b": {
            "params": "1.5B",
            "ram_min": 4,
            "ram_optimal": 6,
            "specialty": "Ultra-fast for resource-limited systems",
            "size_gb": 1.0,
            "speed": "ultra_fast",
        },
        "deepseek-coder-v2:16b": {
            "params": "16B",
            "ram_min": 24,
            "ram_optimal": 32,
            "specialty": "Excellent code generation and debugging",
            "size_gb": 9.8,
            "speed": "medium",
        },
        "codegemma:7b": {
            "params": "7B",
            "ram_min": 10,
            "ram_optimal": 16,
            "specialty": "Google's specialized code understanding",
            "size_gb": 5.0,
            "speed": "fast",
        },
        "codellama:13b": {
            "params": "13B",
            "ram_min": 18,
            "ram_optimal": 24,
            "specialty": "Meta's proven code generation",
            "size_gb": 7.4,
            "speed": "medium",
        },
        "codellama:7b": {
            "params": "7B",
            "ram_min": 10,
            "ram_optimal": 16,
            "specialty": "Reliable, well-tested",
            "size_gb": 3.8,
            "speed": "fast",
        },
        "phi3.5:latest": {
            "params": "3.8B",
            "ram_min": 6,
            "ram_optimal": 8,
            "specialty": "Microsoft's efficient reasoning model",
            "size_gb": 2.3,
            "speed": "very_fast",
        },
        "deepseek-coder:6.7b": {
            "params": "6.7B",
            "ram_min": 9,
            "ram_optimal": 12,
            "specialty": "Balanced quality and speed",
            "size_gb": 3.8,
            "speed": "fast",
        },
    }
    
    def __init__(
        self,
        model: str = "qwen2.5-coder:7b",  # Default to best free model
        base_url: Optional[str] = None,
        timeout: float = 120.0,  # Local inference can be slow
    ):
        """Initialize the Ollama provider.
        
        Args:
            model: Model name to use (must be pulled in Ollama)
                   Default: qwen2.5-coder:7b - Best free coding model (2026)
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
    
    async def close(self):
        """Close the HTTP session properly."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
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
                    # Include full model names with tags
                    self._available_models = [
                        m.get("name", "") 
                        for m in data.get("models", [])
                    ]
                    return self._available_models
                    
        except Exception as e:
            logger.debug(f"Failed to list Ollama models: {e}")
        
        return self.RECOMMENDED_MODELS
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get metadata for a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Dictionary with model metadata (params, RAM requirements, etc.)
        """
        return self.MODEL_INFO.get(model_name, {
            "params": "Unknown",
            "ram_min": 8,
            "ram_optimal": 16,
            "specialty": "General purpose",
            "size_gb": 5.0,
            "speed": "medium",
        })
    
    def recommend_model_for_system(self, ram_gb: float, has_gpu: bool = False) -> str:
        """Recommend best model based on system resources.
        
        Args:
            ram_gb: Available RAM in GB
            has_gpu: Whether system has a capable GPU
            
        Returns:
            Recommended model name
        """
        # Adjust RAM requirements if GPU available (can offload to VRAM)
        ram_multiplier = 0.7 if has_gpu else 1.0
        
        for model_name in self.RECOMMENDED_MODELS:
            info = self.get_model_info(model_name)
            required_ram = info["ram_min"] * ram_multiplier
            
            if ram_gb >= required_ram:
                logger.info(
                    f"Recommended model: {model_name} "
                    f"({info['params']} params, {info['specialty']})"
                )
                return model_name
        
        # Fallback to smallest model
        return "qwen2.5-coder:1.5b"
    
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
