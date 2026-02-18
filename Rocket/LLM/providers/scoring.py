from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional

from Rocket.LLM.providers.base import GenerateOptions, LLMProvider, ProviderTier
from Rocket.Utils.Log import get_logger

# TYPE_CHECKING guard breaks the circular import:
# manager.py → scoring.py → manager.py
# At runtime this import is never executed; it only exists for type checkers.
if TYPE_CHECKING:
    from Rocket.LLM.providers.manager import ProviderStatus

logger = get_logger(__name__)

# --- Constants for Scoring ---
# Estimated cost per 1 million tokens (input + output) in USD
PROVIDER_COST_PER_1M_TOKENS: Dict[str, float] = {
    "gemini": 0.075, # Example for Gemini 1.5 Flash, adjust as needed
    "community-proxy": 0.00, # Community-funded
    "ollama": 0.00, # Local, no monetary cost
    "openai_compat": 0.00, # Local, no monetary cost (user might run paid models, but we don't bill)
}

# Baseline latency estimates in milliseconds for initial scoring
PROVIDER_LATENCY_BASELINE: Dict[str, int] = {
    "gemini": 800,
    "community-proxy": 1500, # Higher due to proxy overhead
    "ollama": 2000, # Varies heavily by hardware
    "openai_compat": 1000, # Varies by local setup/model
}

# Known max token limits for some providers (approximate)
# These are rough estimates and should be refined. Some models have context windows
# that include both input and output.
PROVIDER_MAX_TOKENS: Dict[str, int] = {
    "gemini": 32000, # Gemini 1.5 Flash has 1M context, but typical usage might be smaller
    "community-proxy": 8000, # Assumed limit for free tier
    "ollama": 8192, # Common default for models like Llama 3
    "openai_compat": 4096, # Common default for many OpenAI-like local models
}

# --- Scoring Weights ---
# These weights can be tuned based on product priorities
WEIGHT_PREFERRED_PROVIDER = 1000 # Very high to strongly influence choice
WEIGHT_COST = 500 # Higher weight means lower cost is more preferred
WEIGHT_LATENCY = 300 # Higher weight means lower latency is more preferred
WEIGHT_TOKEN_CAPABILITY = 200
WEIGHT_HEALTH = 2000 # Unhealthy providers heavily penalized (handled by early exit)
WEIGHT_DEFAULT_PENALTY = -10 # Small penalty for unknown factors

@dataclass
class ProviderMetrics:
    """Runtime metrics tracked per provider. Updated after every request."""
    total_requests:   int   = 0
    failed_requests:  int   = 0
    total_latency_ms: float = 0.0
    total_tokens:     int   = 0
    total_cost_usd:   float = 0.0
    last_latency_ms:  float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        return 0.0 if not self.total_requests else self.total_latency_ms / self.total_requests

    @property
    def failure_rate(self) -> float:
        return 0.0 if not self.total_requests else self.failed_requests / self.total_requests

    @property
    def success_rate(self) -> float:
        return 1.0 - self.failure_rate


class ProviderScorer:
    """
    Scores LLM providers based on various factors such as user preference, cost,
    latency, token capability, and health. This scorer works with ProviderStatus
    objects which contain the actual LLMProvider and its current health/rate limit info.
    """

    def __init__(self, preferred_provider: Optional[str] = None):
        # Takes only the string it needs — no ManagerConfig dependency
        self.preferred_provider = preferred_provider
        self._metrics: Dict[str, ProviderMetrics] = {}

    def get_best_provider(self, provider_statuses: List[ProviderStatus], options: GenerateOptions) -> Optional[LLMProvider]:
        """
        Selects the best provider from a list of eligible ProviderStatus objects
        based on their calculated score.
        """
        best_provider: Optional[LLMProvider] = None
        best_score = -float('inf') # Initialize with negative infinity

        for status in provider_statuses:
            # Ensure the provider in status is healthy before scoring,
            # though manager should ideally filter this already.
            if not status.is_healthy:
                continue

            score = self.score_provider(status, options)
            # if logger: logger.debug(f"Provider {status.provider.name} scored: {score}")

            if score > best_score:
                best_score = score
                best_provider = status.provider
            
        return best_provider

    def score_provider(self, status: ProviderStatus, options: GenerateOptions) -> float:
        """
        Scores a single provider based on various factors.
        Takes a ProviderStatus object.
        """
        provider = status.provider
        score = 0.0

        # --- 1. Provider Health (Critical Weight - should be handled by manager, but a safeguard) ---
        if not status.is_healthy:
            return -float('inf') # Heavily penalize unhealthy providers

        # --- 2. User Preference (High Weight) ---
        if self.preferred_provider and self.preferred_provider.lower() == provider.name.lower():
            score += WEIGHT_PREFERRED_PROVIDER

        # --- 3. Cost (Weighted) ---
        # Lower cost should yield higher score
        cost_per_1m = PROVIDER_COST_PER_1M_TOKENS.get(provider.name.lower(), 1.0) # Default to 1.0 if unknown
        if cost_per_1m == 0:
            score += WEIGHT_COST # Free providers get a significant bonus
        else:
            # Invert cost (1/cost) so lower cost gives higher score.
            # Example: cost 0.075 -> 1/0.075 = 13.33; cost 0.1 -> 1/0.1 = 10
            # Adjust factor to scale appropriately with other weights
            score += (1 / cost_per_1m) * (WEIGHT_COST / 10) # Reduced impact for paid options relative to free

        # --- 4. Latency (Weighted) ---
        # Lower latency should yield higher score
        # For now, using baseline. Dynamic metrics from ProviderMetrics (in ManagerConfig) would be better.
        latency_ms = PROVIDER_LATENCY_BASELINE.get(provider.name.lower(), 2000) # Default to 2s
        # Invert latency (1/latency) so lower latency gives higher score
        # Normalize by dividing by 1000 for seconds, and scale
        score += (1 / latency_ms) * (WEIGHT_LATENCY * 1000) 

        # --- 5. Token Capability (Weighted) ---
        # Ensure provider can handle the requested max_tokens for output (or context window)
        required_tokens = options.max_tokens
        provider_max = PROVIDER_MAX_TOKENS.get(provider.name.lower())

        if provider_max is None:
            # If we don't know the limit, assume average or apply a small penalty
            score += WEIGHT_DEFAULT_PENALTY 
        elif required_tokens <= provider_max:
            # Bonus for being able to meet the request
            score += WEIGHT_TOKEN_CAPABILITY
            # Further bonus for larger capacity beyond required, if applicable
            if provider_max > required_tokens * 2: # Has ample buffer
                score += WEIGHT_TOKEN_CAPABILITY / 2
        else:
            # Cannot meet the token requirements, heavily penalize
            score -= WEIGHT_TOKEN_CAPABILITY * 5 # Significant penalty

        # --- Additional considerations could include: ---
        # - Provider-specific features (e.g., code generation quality)
        # - Current provider load (if measurable)
        # - Success rate of previous requests

        return score

    def record_request(
        self,
        provider_name: str,
        latency_ms: float,
        tokens_used: int,
        success: bool,
    ) -> None:
        """Record outcome of a completed request for adaptive scoring."""
        if provider_name not in self._metrics:
            self._metrics[provider_name] = ProviderMetrics()
        m = self._metrics[provider_name]
        m.total_requests   += 1
        m.total_latency_ms += latency_ms
        m.last_latency_ms   = latency_ms
        m.total_tokens     += tokens_used
        cost_per_token = PROVIDER_COST_PER_1M_TOKENS.get(provider_name, 0.0) / 1_000_000
        m.total_cost_usd   += tokens_used * cost_per_token
        if not success:
            m.failed_requests += 1
        logger.debug(
            f"[Scorer] {provider_name}: latency={latency_ms:.0f}ms "
            f"tokens={tokens_used} success={success}"
        )

    def get_summary(self) -> Dict[str, Dict]:
        """Return per-provider metrics summary. Used by: rocket stats."""
        return {
            name: {
                "total_requests": m.total_requests,
                "success_rate":   f"{m.success_rate:.1%}",
                "avg_latency_ms": round(m.avg_latency_ms),
                "total_tokens":   m.total_tokens,
                "total_cost_usd": round(m.total_cost_usd, 6),
            }
            for name, m in self._metrics.items()
        }
