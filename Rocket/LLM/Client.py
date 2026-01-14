"""Gemini Client Wrapper Model free tier with Tool Calling Support"""
import asyncio
from dataclasses import dataclass, field
from typing import AsyncIterator, List, Optional, Dict, Any, Union
from contextlib import asynccontextmanager
import time
import google.generativeai as generativeai
from google.generativeai import types
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core import exceptions as google_exceptions

from Rocket.LLM.Model import LLMResponse, LLMERROR, UsageMetadata
from Rocket.Utils.Config import settings
from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)


# =============================================================================
# Tool Calling Response Models
# =============================================================================

@dataclass
class ToolCall:
    """Represents a single tool/function call from the LLM."""
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "arguments": self.arguments,
            "id": self.id,
        }


@dataclass
class ToolCallResponse:
    """Response from LLM that may contain tool calls or content."""
    content: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw_response: Optional[Any] = None
    usage: Dict[str, Any] = field(default_factory=dict)
    finish_reason: Optional[str] = None
    
    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return len(self.tool_calls) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "finish_reason": self.finish_reason,
            "usage": self.usage,
        }


class RateLimitError(Exception):
    """Raised when rate limit is exceeded after retries."""
    pass


class GeminiClient:
    """Production-ready Gemini API Client with Tool Calling Support.
    
    Features:
    - Async support for non-blocking calls.
    - Tool/function calling with Gemini's native support.
    - Error handling with detailed error models.
    - Streaming response support.
    - Usage tracking and metadata.
    - Safety setup with harm categories.
    - Configurable parameters via environment variables.
    
    Example:
        >>> client = GeminiClient()
        >>> # Basic generation
        >>> response = await client.generate_text("Hello!")
        >>> 
        >>> # With tools
        >>> tools = [{"name": "read_file", "description": "...", "parameters": {...}}]
        >>> response = await client.generate_with_tools(messages, tools)
        >>> if response.tool_calls:
        ...     for call in response.tool_calls:
        ...         print(f"Call: {call.name}({call.arguments})")
    """
    
    def __init__(
        self,
        model_name: str = "gemini-1.5-flash",
        temperature: float = 0.7,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        config: Optional[Any] = None,
    ):
        """
        Initialize the Gemini client.
        
        Args:
            model_name: Gemini model to use
            temperature: Creativity level (0.0-1.0)
            max_retries: Number of retries for rate limits
            retry_delay: Base delay between retries
            config: Optional config object
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Configure API
        api_key = settings.gemini_api_key if not config else getattr(config, 'gemini_api_key', settings.gemini_api_key)
        generativeai.configure(api_key=api_key)

        # Safety Settings - permissive for coding use cases
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        # Initialize the model (without tools - will create per-request with tools)
        self.model = generativeai.GenerativeModel(
            model_name=self.model_name,
            safety_settings=self.safety_settings
        )
        
        # Track usage across sessions
        self.total_requests = 0
        self.total_tokens = 0
        logger.info(f"GeminiClient initialized with model: {self.model_name}")
    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None, max_tokens: int = 1024) -> LLMResponse:
        """Generate text using the Gemini API asynchronously.
        
        Args:
            prompt: The user's prompt
            system_instruction: Optional system instruction to guide the model
            max_tokens: Maximum tokens to generate
            
        Returns:
            LLMResponse with generated text
        """
        logger.debug(f"Generating text for prompt: {prompt[:99]}...")
        
        #Build generation config - use dict for compatibility
        generation_config = {
            "temperature": self.temperature,
            "max_output_tokens": max_tokens,
        }
        
        for attempt in range(self.max_retries):
            try:
                # Combine system instruction with prompt if provided
                if system_instruction:
                    full_prompt = f"{system_instruction}\n\n{prompt}"
                else:
                    full_prompt = prompt
                    
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    full_prompt,
                    generation_config=generation_config
                )
                #Process response
                try:
                    text = response.text
                except ValueError as e:
                    logger.error(f"Response parsing error: {e}")
                    text = "Response was blocked or could not be parsed."
                
                # Extract usage metadata
                usage_metadata = UsageMetadata(
                    prompt_tokens=getattr(response.usage_metadata, 'prompt_token_count', 0),
                    completion_tokens=getattr(response.usage_metadata, 'candidates_token_count', 0),
                    total_tokens=getattr(response.usage_metadata, 'total_token_count', 0)
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
    
    # =========================================================================
    # Tool Calling Support
    # =========================================================================
    
    def _convert_tools_to_gemini_format(
        self,
        tools: List[Dict[str, Any]]
    ) -> List[Any]:
        """
        Convert tool schemas to Gemini's function declaration format.
        
        Args:
            tools: List of tool schemas in standard format
            
        Returns:
            List of Gemini FunctionDeclaration objects
        """
        from google.generativeai.types import FunctionDeclaration
        
        function_declarations = []
        
        for tool in tools:
            # Create FunctionDeclaration from schema
            func_decl = FunctionDeclaration(
                name=tool.get("name", ""),
                description=tool.get("description", ""),
                parameters=tool.get("parameters", {}),
            )
            function_declarations.append(func_decl)
        
        return function_declarations
    
    def _parse_function_calls(self, response: Any) -> List[ToolCall]:
        """
        Parse function calls from Gemini response.
        
        Args:
            response: Raw Gemini response
            
        Returns:
            List of ToolCall objects
        """
        tool_calls = []
        
        try:
            # Check if response has candidates with function calls
            if not response.candidates:
                return tool_calls
            
            candidate = response.candidates[0]
            
            # Check for function_call in the content parts
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    # Check if this part is a function call
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        
                        # Extract arguments - they come as a protobuf struct
                        args = {}
                        if hasattr(fc, 'args') and fc.args:
                            # Convert protobuf struct to dict
                            args = dict(fc.args)
                        
                        tool_calls.append(ToolCall(
                            name=fc.name,
                            arguments=args,
                            id=f"call_{len(tool_calls)}",
                        ))
        
        except Exception as e:
            logger.warning(f"Error parsing function calls: {e}")
        
        return tool_calls
    
    def _extract_text_content(self, response: Any) -> Optional[str]:
        """
        Extract text content from Gemini response.
        
        Args:
            response: Raw Gemini response
            
        Returns:
            Text content or None
        """
        try:
            # Try the simple .text accessor first
            if hasattr(response, 'text'):
                return response.text
            
            # Otherwise parse from candidates
            if response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    text_parts = []
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    if text_parts:
                        return "\n".join(text_parts)
        
        except Exception as e:
            logger.warning(f"Error extracting text: {e}")
        
        return None
    
    async def generate_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        temperature: Optional[float] = None,
    ) -> ToolCallResponse:
        """
        Generate a response with tool/function calling support.
        
        This method enables the LLM to decide whether to call tools
        or provide a direct text response.
        
        Args:
            messages: Conversation history in format:
                [{"role": "user"|"model", "parts": ["text"]}]
            tools: List of tool schemas in format:
                [{"name": str, "description": str, "parameters": dict}]
            temperature: Override temperature (uses instance default if None)
            
        Returns:
            ToolCallResponse with either:
                - content: Final text response (if no tools needed)
                - tool_calls: List of tools the LLM wants to call
                
        Example:
            >>> messages = [{"role": "user", "parts": ["Read main.py"]}]
            >>> tools = [{"name": "read_file", "description": "...", "parameters": {...}}]
            >>> response = await client.generate_with_tools(messages, tools)
            >>> if response.tool_calls:
            ...     print(f"LLM wants to call: {response.tool_calls[0].name}")
            ... else:
            ...     print(f"Response: {response.content}")
        """
        logger.debug(f"Generating with {len(tools)} tools, {len(messages)} messages")
        
        temp = temperature if temperature is not None else self.temperature
        
        # Build generation config
        generation_config = types.GenerationConfig(
            temperature=temp,
        )
        
        for attempt in range(self.max_retries):
            try:
                # Convert tools to Gemini format
                function_declarations = self._convert_tools_to_gemini_format(tools)
                
                # Create a model instance with tools
                model_with_tools = generativeai.GenerativeModel(
                    model_name=self.model_name,
                    safety_settings=self.safety_settings,
                    tools=function_declarations if function_declarations else None,
                )
                
                # Convert messages to Gemini format
                # Gemini expects: [{"role": "user"|"model", "parts": [str]}]
                gemini_messages = []
                for msg in messages:
                    role = msg.get("role", "user")
                    parts = msg.get("parts", [])
                    
                    # Ensure parts is a list
                    if isinstance(parts, str):
                        parts = [parts]
                    
                    gemini_messages.append({
                        "role": role,
                        "parts": parts,
                    })
                
                # Make the API call
                response = await asyncio.to_thread(
                    model_with_tools.generate_content,
                    gemini_messages,
                    generation_config=generation_config,
                )
                
                # Track usage
                self.total_requests += 1
                usage = {}
                
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    usage = {
                        "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0),
                        "completion_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0),
                        "total_tokens": getattr(response.usage_metadata, 'total_token_count', 0),
                    }
                    self.total_tokens += usage.get("total_tokens", 0)
                
                # Parse function calls
                tool_calls = self._parse_function_calls(response)
                
                # Extract text content
                content = None
                if not tool_calls:
                    content = self._extract_text_content(response)
                
                # Get finish reason
                finish_reason = None
                if response.candidates:
                    finish_reason = str(response.candidates[0].finish_reason)
                
                logger.info(
                    f"Generated response: "
                    f"tool_calls={len(tool_calls)}, "
                    f"has_content={content is not None}"
                )
                
                return ToolCallResponse(
                    content=content,
                    tool_calls=tool_calls,
                    raw_response=response,
                    usage=usage,
                    finish_reason=finish_reason,
                )
                
            except google_exceptions.ResourceExhausted as e:
                logger.warning(f"Rate limit hit (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise RateLimitError("Rate limit exceeded after retries")
                    
            except google_exceptions.GoogleAPIError as e:
                logger.error(f"Google API error: {e}")
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error in generate_with_tools: {e}", exc_info=True)
                raise
        
        # Should not reach here, but just in case
        return ToolCallResponse(
            content="Error: Failed to generate response after retries",
            tool_calls=[],
        )
