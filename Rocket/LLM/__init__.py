"""
Rocket LLM Module - Production-ready LLM Integration Layer

This module provides a clean, asynchronous interface for interacting with 
Google's Gemini AI. It handles:
- Async text and streaming generation
- Tool/function calling support
- Automatic retry logic with exponential backoff
- Usage tracking and statistics
- Type-safe request/response handling with Pydantic models
- Comprehensive error handling and logging

Example:
    >>> from Rocket.LLM import GeminiClient, LLMResponse, UsageMetadata
    >>> client = GeminiClient(model_name="gemini-1.5-flash")
    >>> response = await client.generate_text("What is Python?")
    >>> print(response.text)
    
    >>> # Streaming
    >>> async for chunk in client.generate_stream("Tell me a story"):
    ...     print(chunk, end="", flush=True)
    
    >>> # Tool calling
    >>> tools = [{"name": "read_file", "description": "...", "parameters": {...}}]
    >>> response = await client.generate_with_tools(messages, tools)
    >>> if response.tool_calls:
    ...     print(f"Tool: {response.tool_calls[0].name}")
    
    >>> # Usage stats
    >>> stats = client.get_usage_stats()
    >>> print(f"Total tokens: {stats['total_tokens']}")
"""

from .Model import (
    UsageMetadata,
    LLMResponse,
    LLMERROR,
)
from .Client import (
    GeminiClient,
    ToolCall,
    ToolCallResponse,
    RateLimitError,
)

__all__ = [
    # Models
    "UsageMetadata",
    "LLMResponse",
    "LLMERROR",
    # Client
    "GeminiClient",
    # Tool Calling
    "ToolCall",
    "ToolCallResponse",
    "RateLimitError",
]

__version__ = "1.0.0"
__author__ = "Sayendra Chowdary"
__description__ = "Production-ready Gemini LLM client with async support"
