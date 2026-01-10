"""Gemini Client Wrapper Model free tier"""
import asyncio
from typing import AsyncIterator, List, Optional
from contextlib import asynccontextmanager
import time
import google.generativeai as generativeai
from google.generativeai import types, HarmBlockThreshold
from google.api_core import exceptions as google_exceptions

from Rocket.LLM.Model import LLMResponse, LLMERROR, UsageMetadata
from Rocket.Utils.Config import settings
from Rocket.Utils.Logger import logger

logger = logger(__name__)

class GeminiClient:
    """Production-ready Gemini API Client.
    Features:
    - Async support for non-blocking calls.
    - Error handling with detailed error models.
    - Streaming response support.
    - Usage tracking and metadata.
    - Safety setup with harm categories.
    - Configurable parameters via environment variables.
    """
    #Model usage,tokens,max entries-->  Default initialization
    def __init__(self, model_name: str ="gemini-1.5-flash",
                    temperature: float = 0.7,
                    max_retries: int = 3,
                    retry_delay: float = 1.0
                ):
        self.model_name = model_name
        self.temperature = temperature
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        generativeai.configure(api_key=settings.GEMINI_API_KEY)
        self.client = generativeai.GenerativeModel(model_name=self.model_name)
        
        #Safety Settings  will be permissive for coding use cases
        self.safety_setting={
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        
        }
        
        #Intialize the model
        self.model= generativeai.GenerativeModel(model_name=self.model_name,safety_settings=self.safety_setting)
        
        #Track Usage across sessions
        self.total_requests = 0
        self.total_tokens =0
        logger.info(f"GeminiClient initialized with model: {self.model_name}")
    async def generate_text(self, prompt: str, max_tokens: int = 1024) -> LLMResponse:
        """Generate text using the Gemini API asynchronously."""
        logger.debug(f"Generating text for prompt: {prompt[:99]}...")
        
        #Build generation config
        generation_config = types.TextGenerationConfig(
            temperature=self.temperature,
            max_output_tokens=max_tokens,
        )
        
        for attempt in range(self.max_retries):
            try:
                full_prompt = f"{prompt}"
                if system_instruction:
                    response = await asyncio.to_thread(
                        self.model.generate_text,
                        prompt=full_prompt,
                        generation_config=generation_config
                    )
                    #Process response
                    try:
                        text = response.text
                    except ValueError as e:
                        logger.error(f"Response parsing error: {e}")
                        text = "Resposes Blockes oops..."
                    
                    usage_metadata = UsageMetadata(
                        prompt_tokens=response.metadata.input_token_count,
                        completion_tokens=response.metadata.output_token_count,
                        total_tokens=response.metadata.total_token_count
                    )
                    
                    # track usage
                    self.total_requests += 1
                    self.total_tokens += usage_metadata.total_tokens
                    
                    # extract finish reason
                    finish_reason = None
                    if response.candidates:
                        finish_reason = response.candidates[0].finish_reason.name
                    
                    logger.info(f"Response generated: {usage_metadata}")
                    return LLMResponse(
                        text=text,
                        model=self.model_name,
                        usage=usage_metadata,
                        finish_reason=finish_reason
                    )
            except google_exceptions.ResourceExhausted as e:
                # Rate limit hit!
                logger.warning(f"Rate limit hit (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s, etc.
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise RateLimitError("Rate limit exceeded after retries")
            except google_exceptions.GoogleAPIError as e:
                logger.error(f"Google API error: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise
    
    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming response from Gemini.
        
        This yields chunks of text as they're generated, enabling real-time UX!
        
        Args:
            prompt: The user's question/prompt
            system_instruction: Optional system prompt
        
        Yields:
            Chunks of text as they arrive
        
        Example:
            async for chunk in client.generate_stream("Tell me a story"):
                print(chunk, end="", flush=True)
        """
        logger.debug(f"Generating streaming response for: {prompt[:100]}...")
        
        # Prepare prompt
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"{system_instruction}\n\n{prompt}"
        
        # Build generation config
        generation_config = types.TextGenerationConfig(
            temperature=self.temperature,
        )
        
        # Call Gemini streaming API
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                full_prompt,
                generation_config=generation_config,
                stream=True,
            )
            
            # Yield chunks as they arrive
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    logger.debug(f"Streamed chunk: {chunk.text[:50]}...")
            
            logger.info("Streaming response completed successfully")
        
        except google_exceptions.ResourceExhausted as e:
            logger.warning(f"Rate limit hit during streaming: {e}")
            raise RateLimitError("Rate limit exceeded during streaming")
        
        except google_exceptions.GoogleAPIError as e:
            logger.error(f"Google API error during streaming: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error during streaming: {e}")
            raise
    
    def get_usage_stats(self) -> dict:
        """Get usage statistics as a dictionary.
        
        Returns a comprehensive dict with all usage metrics tracked during the session.
        
        Returns:
            dict: Contains:
                - model: Name of the model being used
                - total_requests: Total number of API calls made
                - total_tokens: Total tokens consumed across all requests
                - temperature: Current temperature setting
                - max_retries: Maximum retry attempts configured
                - retry_delay: Delay between retries (seconds)
        
        Example:
            stats = client.get_usage_stats()
            print(f"Requests: {stats['total_requests']}, Tokens: {stats['total_tokens']}")
        """
        usage_stats = {
            "model": self.model_name,
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "temperature": self.temperature,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "avg_tokens_per_request": (
                self.total_tokens / self.total_requests 
                if self.total_requests > 0 
                else 0
            )
        }
        
        logger.debug(f"Usage stats retrieved: {usage_stats}")
        return usage_stats
    
    def reset_usage_stats(self) -> None:
        """Reset all usage statistics to zero.
        
        Useful for starting a fresh tracking session.
        
        Example:
            client.reset_usage_stats()
        """
        self.total_requests = 0
        self.total_tokens = 0
        logger.info("Usage statistics reset to zero")

            