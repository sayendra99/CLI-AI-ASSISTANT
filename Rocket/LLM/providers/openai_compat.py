import json
import time
from typing import AsyncIterator, Dict, Optional

import httpx

from Rocket.LLM.providers.base import (
    GenerateOptions,
    GenerateResponse,
    LLMProvider,
    ProviderError,
    ProviderTier,
    ProviderUnavailableError,
    RateLimitError,
    RateLimitInfo,
    UsageInfo,
)
from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)


class OpenAICompatProvider(LLMProvider):
    """
    Provider for ANY OpenAI-compatible API endpoint.

    Supports:
        LM Studio  -> http://localhost:1234/v1
        vLLM       -> http://localhost:8000/v1
        Jan.ai     -> http://localhost:1337/v1
        llama.cpp  -> http://localhost:8080/v1
        Any custom -> http://your-server/v1

    Usage:
        provider = OpenAICompatProvider({
            "openai_compat_url":   "http://localhost:1234/v1",
            "openai_compat_model": "llama3",
        })
    """

    name: str = "openai_compat"
    display_name: str = "OpenAI Compatible (Local)"
    tier: ProviderTier = ProviderTier.LOCAL

    def __init__(self, config: Dict):
        self.api_url = config.get("openai_compat_url", "").rstrip("/")
        self.model_name = config.get("openai_compat_model", "")
        self.api_key = config.get("openai_compat_api_key", "not-needed")
        self.timeout = float(config.get("openai_compat_timeout", 120.0))

        if not self.api_url:
            raise ValueError(
                "openai_compat_url is required. "
                "Run: rocket config set openai-compat-url http://localhost:1234/v1"
            )
        if not self.model_name:
            raise ValueError(
                "openai_compat_model is required. "
                "Run: rocket config set openai-compat-model llama3"
            )

    # ── Health check ──────────────────────────────────────────────────────────

    async def is_available(self) -> bool:
        """Check if the local server is running via /models endpoint."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.api_url}/models",
                    headers=self._headers(),
                )
                available = response.status_code == 200
                logger.debug(
                    f"[OpenAICompat] Health: "
                    f"{'available' if available else 'unavailable'}"
                )
                return available
        except Exception as e:
            logger.debug(f"[OpenAICompat] Not reachable: {e}")
            return False

    async def get_rate_limits(self) -> RateLimitInfo:
        """Local providers have no rate limits."""
        return RateLimitInfo(
            limit=999999,
            remaining=999999,
            period="unlimited",
            tier=self.tier,
        )

    # ── Generate (non-streaming) ──────────────────────────────────────────────

    async def generate(self, options: GenerateOptions) -> GenerateResponse:
        """
        POST /chat/completions  <- correct chat endpoint.
        Always RAISES on error so manager fallback triggers.
        """
        start_ms = time.monotonic() * 1000
        messages = self._build_messages(options)

        payload: Dict = {
            "model":       self.model_name,
            "messages":    messages,
            "max_tokens":  options.max_tokens,
            "temperature": options.temperature,
            "stream":      False,
        }
        if options.stop_sequences:
            payload["stop"] = options.stop_sequences

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_url}/chat/completions",  # correct endpoint
                    headers=self._headers(),
                    json=payload,
                )

            # ── HTTP error handling ───────────────────────────────────────
            if response.status_code == 429:
                raise RateLimitError(
                    "Local server rate limit hit", provider=self.name
                )
            if response.status_code >= 500:
                raise ProviderUnavailableError(
                    f"Server error HTTP {response.status_code}", provider=self.name
                )
            if response.status_code >= 400:
                raise ProviderError(
                    f"Bad request HTTP {response.status_code}: {response.text[:200]}",
                    provider=self.name,
                )

            data = response.json()
            choice = data["choices"][0]

            # correct: chat/completions response format
            text = choice["message"]["content"]
            finish_reason = choice.get("finish_reason", "stop")

            # ── Token usage for cost tracking ─────────────────────────────
            usage_data        = data.get("usage", {})
            prompt_tokens     = usage_data.get("prompt_tokens", 0)
            completion_tokens = usage_data.get("completion_tokens", 0)
            total_tokens      = usage_data.get(
                "total_tokens", prompt_tokens + completion_tokens
            )
            latency_ms = (time.monotonic() * 1000) - start_ms

            logger.debug(
                f"[OpenAICompat] OK: {total_tokens} tokens in {latency_ms:.0f}ms"
            )

            return GenerateResponse(
                text=text,
                model=data.get("model", self.model_name),
                provider=self.name,
                finish_reason=finish_reason,
                usage=UsageInfo(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                ),
            )

        # Always raise so ProviderManager can fallback to next provider
        except (RateLimitError, ProviderUnavailableError, ProviderError):
            raise
        except httpx.TimeoutException:
            raise ProviderUnavailableError(
                f"Timed out after {self.timeout}s. Is your local server running?",
                provider=self.name,
            )
        except httpx.ConnectError:
            raise ProviderUnavailableError(
                f"Cannot connect to {self.api_url}. Is your local server running?",
                provider=self.name,
            )
        except Exception as e:
            raise ProviderError(f"Unexpected error: {e}", provider=self.name)

    # ── Streaming ─────────────────────────────────────────────────────────────

    async def generate_stream(self, options: GenerateOptions) -> AsyncIterator[str]:
        """Stream tokens via SSE. Falls back to non-streaming if unsupported."""
        messages = self._build_messages(options)
        payload = {
            "model":       self.model_name,
            "messages":    messages,
            "max_tokens":  options.max_tokens,
            "temperature": options.temperature,
            "stream":      True,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.api_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        # Server does not support streaming — fallback
                        logger.debug(
                            "[OpenAICompat] Streaming unsupported, "
                            "falling back to generate()"
                        )
                        result = await self.generate(options)
                        yield result.text
                        return

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:]  # strip "data: " prefix
                        if data_str == "[DONE]":
                            break
                        try:
                            data  = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            chunk = delta.get("content", "")
                            if chunk:
                                yield chunk
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

        except (ProviderError, ProviderUnavailableError):
            raise
        except Exception as e:
            raise ProviderError(f"Stream error: {e}", provider=self.name)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_messages(self, options: GenerateOptions) -> list:
        """Build messages array in chat/completions format."""
        messages = []
        if options.system_instruction:
            messages.append({"role": "system", "content": options.system_instruction})
        if options.messages:
            messages.extend(options.messages)
        messages.append({"role": "user", "content": options.prompt})
        return messages

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }