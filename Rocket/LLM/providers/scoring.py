from dataclasses import dataclass, field
from typing import Dict, List, Optional

from Rocket.LLM.providers.base import GenerateOptions, LLMProvider
from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)


# ── Cost table: USD per 1M tokens ────────────────────────────────────────────
COST_PER_1M_TOKENS: Dict[str, float] = {
    "gemini":          0.075,   # Gemini 1.5 Flash
    "community-proxy": 0.0,     # Free (community funded)
    "ollama":          0.0,     # Free (local)
    "openai_compat":   0.0,     # Free (local)
}

# ── Baseline latency in ms (used before real data exists) ────────────────────
LATENCY_BASELINE_MS: Dict[str, float] = {
    "gemini":          800.0,
    "community-proxy": 1200.0,
    "ollama":          2000.0,
    "openai_compat":   1500.0,
}


@dataclass
class ProviderMetrics:
    """
    Runtime metrics tracked per provider.
    Updated after every single request.
    """
    total_requests:   int   = 0
    failed_requests:  int   = 0
    total_latency_ms: float = 0.0
    total_tokens:     int   = 0
    total_cost_usd:   float = 0.0
    last_latency_ms:  float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    @property
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    @property
    def success_rate(self) -> float:
        return 1.0 - self.failure_rate


@dataclass
class ProviderScore:
    """Full score breakdown for a single provider."""
    provider_name:     str
    total_score:       float
    reliability_score: float
    preference_score:  float
    latency_score:     float
    cost_score:        float
    reason:            str = ""


class ProviderScorer:
    """
    Scores LLM providers for intelligent request routing.

    Scoring weights:
        Reliability  40%  (historical failure rate)
        Preference   30%  (user config + provider tier)
        Latency      20%  (average response speed)
        Cost         10%  (token price)

    Create ONCE in ProviderManager.__init__(), not per request,
    so metrics accumulate across requests.
    """

    def __init__(self, preferred_provider: Optional[str] = None):
        # preferred_provider is the name string e.g. "gemini", "ollama"
        self.preferred_provider = preferred_provider
        self._metrics: Dict[str, ProviderMetrics] = {}

    # ── Record outcome after every request ───────────────────────────────────

    def record_request(
        self,
        provider_name: str,
        latency_ms: float,
        tokens_used: int,
        success: bool,
    ) -> None:
        """
        Record the outcome of a completed request.
        Must be called after every generate() call.
        """
        m = self._get_or_create(provider_name)
        m.total_requests   += 1
        m.total_latency_ms += latency_ms
        m.last_latency_ms   = latency_ms
        m.total_tokens     += tokens_used
        cost_per_token = COST_PER_1M_TOKENS.get(provider_name, 0.0) / 1_000_000
        m.total_cost_usd   += tokens_used * cost_per_token
        if not success:
            m.failed_requests += 1
        logger.debug(
            f"[Scorer] recorded {provider_name}: "
            f"latency={latency_ms:.0f}ms tokens={tokens_used} success={success}"
        )

    # ── Provider selection ────────────────────────────────────────────────────

    def get_best_provider(
        self,
        providers: List[LLMProvider],
        options: GenerateOptions,
    ) -> Optional[LLMProvider]:
        """
        Select the highest-scoring provider from eligible providers.
        Returns None if the list is empty.
        Caller passes only HEALTHY providers (already filtered by ProviderManager).
        """
        if not providers:
            logger.warning("[Scorer] No providers to score")
            return None

        if len(providers) == 1:
            return providers[0]  # skip scoring overhead

        scored = [
            self.score_provider(p, options)
            for p in providers
        ]
        scored.sort(key=lambda s: s.total_score, reverse=True)

        for s in scored:
            logger.debug(
                f"[Scorer] {s.provider_name}: "
                f"{s.total_score:.3f} | {s.reason}"
            )

        best_name = scored[0].provider_name
        return next(
            (p for p in providers if p.name == best_name),
            providers[0],
        )

    def score_provider(
        self,
        provider: LLMProvider,
        options: GenerateOptions,
    ) -> ProviderScore:
        """
        Score a single provider. Higher total_score = better choice.
        Only called for HEALTHY providers (no need to check health here).
        """
        name    = provider.name
        metrics = self._get_or_create(name)

        # ── Reliability (0-1): based on historical success rate ───────────
        # New providers start at 1.0 (benefit of the doubt)
        reliability = max(0.0, metrics.success_rate)

        # ── Preference (0-1): user config + provider tier ─────────────────
        if self.preferred_provider and self.preferred_provider == name:
            preference = 1.0
        elif name == "gemini":
            preference = 0.8   # BYOK: high quality, user pays
        elif name == "community-proxy":
            preference = 0.6   # Free tier: good default
        elif name in ("ollama", "openai_compat"):
            preference = 0.5   # Local: free but potentially slower
        else:
            preference = 0.4

        # ── Latency (0-1): lower latency = higher score ───────────────────
        avg_latency = (
            metrics.avg_latency_ms
            if metrics.total_requests > 0
            else LATENCY_BASELINE_MS.get(name, 1500.0)
        )
        # Normalize: 0ms -> 1.0, 5000ms -> 0.0
        latency = max(0.0, 1.0 - (avg_latency / 5000.0))

        # ── Cost (0-1): free providers score highest ───────────────────────
        cost_per_1m = COST_PER_1M_TOKENS.get(name, 0.0)
        cost = (
            1.0
            if cost_per_1m == 0.0
            else max(0.0, 1.0 - (cost_per_1m / 10.0))
        )

        # ── Weighted total ─────────────────────────────────────────────────
        total = (
            reliability * 0.40 +
            preference  * 0.30 +
            latency     * 0.20 +
            cost        * 0.10
        )

        return ProviderScore(
            provider_name=name,
            total_score=round(total, 4),
            reliability_score=round(reliability, 4),
            preference_score=round(preference, 4),
            latency_score=round(latency, 4),
            cost_score=round(cost, 4),
            reason=(
                f"reliability={reliability:.2f} "
                f"pref={preference:.2f} "
                f"latency={latency:.2f} "
                f"cost={cost:.2f}"
            ),
        )

    # ── Analytics ─────────────────────────────────────────────────────────────

    def get_summary(self) -> Dict[str, Dict]:
        """Return cost and performance summary. Used by: rocket stats"""
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

    def reset_metrics(self, provider_name: str) -> None:
        """Reset metrics for a specific provider (useful for testing)."""
        self._metrics[provider_name] = ProviderMetrics()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_or_create(self, name: str) -> ProviderMetrics:
        if name not in self._metrics:
            self._metrics[name] = ProviderMetrics()
        return self._metrics[name]