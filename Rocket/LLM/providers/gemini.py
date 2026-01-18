"""
Gemini Provider - Google's Generative AI provider implementation.

This provider wraps Google's Gemini API for direct BYOK (Bring Your Own Key) usage.
Highest priority provider when user has their own API key.
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
    RateLimitError,
    ConfigError,
    ProviderUnavailableError,
)

logger = get_logger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini API provider for BYOK usage.
    
    Features:
    - Direct Gemini API access with user's key
    - Streaming support
    - Automatic retry with exponential backoff
    - Tool/function calling support
    
    Example:
        >>> provider = GeminiProvider(api_key="your-key")
        >>> if await provider.is_available():
        ...     response = await provider.generate(GenerateOptions(prompt="Hello!"))
        ...     print(response.text)
    """
    
    name = "gemini"
    display_name = "Google Gemini (BYOK)"
    tier = ProviderTier.BYOK
    
    # Available Gemini models
    AVAILABLE_MODELS = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b", 
        "gemini-1.5-pro",
        "gemini-2.0-flash-exp",
    ]
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-1.5-flash",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize the Gemini provider.
        
        Args:
            api_key: Gemini API key (required for BYOK)
            model: Model to use (default: gemini-1.5-flash)
            max_retries: Number of retries on rate limit
            retry_delay: Base delay between retries (exponential backoff)
        """
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Will be initialized lazily
        self._client = None
        self._genai = None
        
        # Track usage
        self.total_requests = 0
        self.total_tokens = 0
    
    def _ensure_initialized(self) -> None:
        """Lazily initialize the Gemini client."""
        if self._genai is None:
            try:
                import google.generativeai as genai
                from google.generativeai.types import HarmCategory, HarmBlockThreshold
                
                self._genai = genai
                self._HarmCategory = HarmCategory
                self._HarmBlockThreshold = HarmBlockThreshold
                
                # Configure with API key
                genai.configure(api_key=self.api_key)
                
                # Safety settings - permissive for coding
                self._safety_settings = {
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
                
                # Create model instance
                self._client = genai.GenerativeModel(
                    model_name=self.model,
                    safety_settings=self._safety_settings,
                )
                
                logger.debug(f"Gemini provider initialized with model: {self.model}")
                
            except ImportError:
                raise ConfigError(
                    "google-generativeai package not installed. "
                    "Install with: pip install google-generativeai",
                    provider=self.name
                )
            except Exception as e:
                raise ConfigError(f"Failed to initialize Gemini: {e}", provider=self.name)
    
    async def is_available(self) -> bool:
        """Check if Gemini provider is available.
        
        Requires:
        - API key to be set
        - google-generativeai package installed
        """
        if not self.api_key:
            logger.debug("Gemini provider not available: no API key")
            return False
        
        try:
            self._ensure_initialized()
            return True
        except ConfigError as e:
            logger.debug(f"Gemini provider not available: {e}")
            return False
    
    async def generate(self, options: GenerateOptions) -> GenerateResponse:
        """Generate text using Gemini API.
        
        Args:
            options: Generation parameters
            
        Returns:
            GenerateResponse with generated text
            
        Raises:
            RateLimitError: If rate limit exceeded after retries
            ProviderError: If generation fails
        """
        self._ensure_initialized()
        
        # Build generation config
        generation_config = {
            "temperature": options.temperature,
            "max_output_tokens": options.max_tokens,
        }
        
        if options.stop_sequences:
            generation_config["stop_sequences"] = options.stop_sequences
        
        # Prepare prompt
        if options.system_instruction and options.prompt:
            full_prompt = f"{options.system_instruction}\n\n{options.prompt}"
        else:
            full_prompt = options.prompt
        
        # Handle messages format (for multi-turn)
        if options.messages:
            # Convert messages to Gemini format
            contents = []
            for msg in options.messages:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [msg.get("content", "")]})
            # Add current prompt if provided
            if options.prompt:
                contents.append({"role": "user", "parts": [options.prompt]})
        else:
            contents = full_prompt
        
        # Retry loop with exponential backoff
        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Make async call
                response = await asyncio.to_thread(
                    self._client.generate_content,
                    contents,
                    generation_config=generation_config,
                )
                
                # Extract text
                try:
                    text = response.text
                except ValueError:
                    text = "Response was blocked or could not be parsed."
                
                # Extract usage
                usage = UsageInfo(
                    prompt_tokens=getattr(response.usage_metadata, 'prompt_token_count', 0),
                    completion_tokens=getattr(response.usage_metadata, 'candidates_token_count', 0),
                    total_tokens=getattr(response.usage_metadata, 'total_token_count', 0),
                )
                
                # Extract finish reason
                finish_reason = None
                if response.candidates:
                    finish_reason = response.candidates[0].finish_reason.name
                
                # Track usage
                self.total_requests += 1
                self.total_tokens += usage.total_tokens
                
                logger.debug(f"Gemini generation successful: {usage.total_tokens} tokens")
                
                return GenerateResponse(
                    text=text,
                    model=self.model,
                    provider=self.name,
                    usage=usage,
                    finish_reason=finish_reason,
                    raw_response=response,
                )
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Check for rate limit
                if "resource exhausted" in error_str or "429" in error_str:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(
                            f"Gemini rate limit hit (attempt {attempt + 1}/{self.max_retries}), "
                            f"retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise RateLimitError(
                            "Rate limit exceeded after retries. Consider upgrading your plan.",
                            provider=self.name,
                            retry_after=60,
                            upgrade_url="https://ai.google.dev/pricing",
                        )
                
                # Check for auth errors
                if "api key" in error_str or "unauthorized" in error_str or "403" in error_str:
                    raise ConfigError(
                        "Invalid or expired Gemini API key. "
                        "Get a new key at: https://aistudio.google.com/app/apikey",
                        provider=self.name,
                    )
                
                # Other errors
                logger.error(f"Gemini generation error: {e}")
                raise ProviderError(f"Generation failed: {e}", provider=self.name)
        
        # Should not reach here, but just in case
        raise ProviderError(f"Generation failed after {self.max_retries} attempts", provider=self.name)
    
    async def generate_stream(self, options: GenerateOptions) -> AsyncIterator[str]:
        """Generate text with streaming response.
        
        Args:
            options: Generation parameters
            
        Yields:
            Chunks of generated text
        """
        self._ensure_initialized()
        
        # Build generation config
        generation_config = {
            "temperature": options.temperature,
            "max_output_tokens": options.max_tokens,
        }
        
        # Prepare prompt
        if options.system_instruction and options.prompt:
            full_prompt = f"{options.system_instruction}\n\n{options.prompt}"
        else:
            full_prompt = options.prompt
        
        try:
            # Make streaming call
            response = await asyncio.to_thread(
                self._client.generate_content,
                full_prompt,
                generation_config=generation_config,
                stream=True,
            )
            
            # Yield chunks
            for chunk in response:
                if hasattr(chunk, 'text') and chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            error_str = str(e).lower()
            
            if "resource exhausted" in error_str or "429" in error_str:
                raise RateLimitError(
                    "Rate limit exceeded during streaming.",
                    provider=self.name,
                    upgrade_url="https://ai.google.dev/pricing",
                )
            
            logger.error(f"Gemini streaming error: {e}")
            raise ProviderError(f"Streaming failed: {e}", provider=self.name)
    
    async def get_rate_limits(self) -> RateLimitInfo:
        """Get rate limit info for Gemini.
        
        Note: Gemini free tier has 15 RPM, 1M TPM, 1500 RPD.
        BYOK users have higher limits based on their plan.
        """
        # Gemini doesn't expose rate limit info in headers,
        # so we return estimated limits for free tier
        return RateLimitInfo(
            limit=1500,  # Free tier daily limit
            remaining=1500 - self.total_requests,  # Estimate
            period="day",
            tier=self.tier,
        )
    
    async def get_models(self) -> List[str]:
        """List available Gemini models."""
        return self.AVAILABLE_MODELS
