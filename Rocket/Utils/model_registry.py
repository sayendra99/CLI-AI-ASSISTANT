"""
Model Registry - Centralized catalog of recommended free AI models

This registry can be updated remotely to add new models as they're released.
Users can check for updates and auto-install new recommended models.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class ModelQuality(Enum):
    """Model quality tiers"""
    SOTA = "state-of-the-art"  # Best available
    EXCELLENT = "excellent"     # Very good
    GOOD = "good"              # Solid choice
    FAST = "fast"              # Speed-optimized
    LEGACY = "legacy"          # Older, being phased out


@dataclass
class ModelEntry:
    """Represents a model in the registry"""
    name: str                    # e.g., "qwen2.5-coder:7b"
    version: str                 # e.g., "1.5.0" or "2025.01"
    quality: ModelQuality
    params: str                  # e.g., "7B"
    ram_min_gb: int
    ram_optimal_gb: int
    size_gb: float
    speed_rating: str            # "ultra_fast", "fast", "medium", "slow"
    specialty: str               # Description
    release_date: str            # ISO format
    provider: str = "ollama"
    
    # Optional fields
    recommended_for: List[str] = None  # ["coding", "debugging", "explanation"]
    supersedes: Optional[str] = None   # Model it replaces
    notes: Optional[str] = None
    
    def __post_init__(self):
        if self.recommended_for is None:
            self.recommended_for = ["coding"]
        if isinstance(self.quality, str):
            self.quality = ModelQuality(self.quality)
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['quality'] = self.quality.value
        return data


class ModelRegistry:
    """
    Central registry of all recommended free models.
    
    This can be updated via:
    1. Local JSON file
    2. Remote API call (for auto-updates)
    3. Hardcoded defaults (fallback)
    """
    
    # Current registry version
    REGISTRY_VERSION = "2026.02"
    
    # Hardcoded models (fallback if remote fetch fails)
    DEFAULT_MODELS = [
        # Qwen2.5-Coder series (SOTA as of Jan 2025)
        ModelEntry(
            name="qwen2.5-coder:1.5b",
            version="2025.01",
            quality=ModelQuality.FAST,
            params="1.5B",
            ram_min_gb=4,
            ram_optimal_gb=6,
            size_gb=1.0,
            speed_rating="ultra_fast",
            specialty="Ultra-fast for resource-limited systems. Best tiny coding model.",
            release_date="2025-01-15",
            recommended_for=["coding", "quick-queries"],
        ),
        ModelEntry(
            name="qwen2.5-coder:3b",
            version="2025.01",
            quality=ModelQuality.EXCELLENT,
            params="3B",
            ram_min_gb=6,
            ram_optimal_gb=8,
            size_gb=2.0,
            speed_rating="very_fast",
            specialty="Perfect balance of speed and quality. Great for daily use.",
            release_date="2025-01-15",
            recommended_for=["coding", "debugging", "refactoring"],
        ),
        ModelEntry(
            name="qwen2.5-coder:7b",
            version="2025.01",
            quality=ModelQuality.SOTA,
            params="7B",
            ram_min_gb=10,
            ram_optimal_gb=16,
            size_gb=4.7,
            speed_rating="fast",
            specialty="State-of-the-art free coding model. Best quality-to-performance ratio.",
            release_date="2025-01-15",
            recommended_for=["coding", "debugging", "explanation", "refactoring"],
        ),
        ModelEntry(
            name="qwen2.5-coder:14b",
            version="2025.01",
            quality=ModelQuality.SOTA,
            params="14B",
            ram_min_gb=20,
            ram_optimal_gb=32,
            size_gb=8.9,
            speed_rating="medium",
            specialty="Highest quality for complex tasks. Rivals paid models.",
            release_date="2025-01-15",
            recommended_for=["coding", "debugging", "architecture", "complex-tasks"],
        ),
        
        # DeepSeek-Coder series
        ModelEntry(
            name="deepseek-coder-v2:16b",
            version="2024.11",
            quality=ModelQuality.EXCELLENT,
            params="16B",
            ram_min_gb=24,
            ram_optimal_gb=32,
            size_gb=9.8,
            speed_rating="medium",
            specialty="Excellent code generation and debugging. Strong at complex logic.",
            release_date="2024-11-20",
            recommended_for=["coding", "debugging", "complex-logic"],
        ),
        ModelEntry(
            name="deepseek-coder:6.7b",
            version="2024.06",
            quality=ModelQuality.GOOD,
            params="6.7B",
            ram_min_gb=9,
            ram_optimal_gb=12,
            size_gb=3.8,
            speed_rating="fast",
            specialty="Balanced quality and speed. Reliable choice.",
            release_date="2024-06-15",
            recommended_for=["coding", "debugging"],
        ),
        
        # CodeGemma (Google)
        ModelEntry(
            name="codegemma:7b",
            version="2024.08",
            quality=ModelQuality.EXCELLENT,
            params="7B",
            ram_min_gb=10,
            ram_optimal_gb=16,
            size_gb=5.0,
            speed_rating="fast",
            specialty="Google's specialized code understanding model.",
            release_date="2024-08-10",
            recommended_for=["code-understanding", "explanation"],
        ),
        
        # CodeLlama (Meta)
        ModelEntry(
            name="codellama:13b",
            version="2023.09",
            quality=ModelQuality.GOOD,
            params="13B",
            ram_min_gb=18,
            ram_optimal_gb=24,
            size_gb=7.4,
            speed_rating="medium",
            specialty="Meta's proven code generation model. Well-tested.",
            release_date="2023-09-25",
            recommended_for=["coding", "code-completion"],
        ),
        ModelEntry(
            name="codellama:7b",
            version="2023.09",
            quality=ModelQuality.GOOD,
            params="7B",
            ram_min_gb=10,
            ram_optimal_gb=16,
            size_gb=3.8,
            speed_rating="fast",
            specialty="Reliable, well-tested code model.",
            release_date="2023-09-25",
            recommended_for=["coding"],
        ),
        
        # Phi-3.5 (Microsoft)
        ModelEntry(
            name="phi3.5:latest",
            version="2024.10",
            quality=ModelQuality.FAST,
            params="3.8B",
            ram_min_gb=6,
            ram_optimal_gb=8,
            size_gb=2.3,
            speed_rating="very_fast",
            specialty="Microsoft's efficient reasoning model. Great for explanations.",
            release_date="2024-10-15",
            recommended_for=["explanation", "reasoning"],
        ),
    ]
    
    def __init__(self):
        self.models: List[ModelEntry] = self.DEFAULT_MODELS.copy()
        self.last_update: Optional[datetime] = None
    
    def get_all_models(self) -> List[ModelEntry]:
        """Get all models in registry"""
        return self.models
    
    def get_recommended_models(self, quality_threshold: ModelQuality = ModelQuality.GOOD) -> List[ModelEntry]:
        """Get models above quality threshold"""
        threshold_order = [ModelQuality.LEGACY, ModelQuality.FAST, ModelQuality.GOOD, ModelQuality.EXCELLENT, ModelQuality.SOTA]
        min_index = threshold_order.index(quality_threshold)
        
        return [
            m for m in self.models 
            if threshold_order.index(m.quality) >= min_index
        ]
    
    def get_model(self, name: str) -> Optional[ModelEntry]:
        """Get specific model by name"""
        for model in self.models:
            if model.name == name:
                return model
        return None
    
    def get_latest_models(self, limit: int = 5) -> List[ModelEntry]:
        """Get most recently released models"""
        sorted_models = sorted(
            self.models,
            key=lambda m: m.release_date,
            reverse=True
        )
        return sorted_models[:limit]
    
    def get_models_by_quality(self, quality: ModelQuality) -> List[ModelEntry]:
        """Get models of specific quality tier"""
        return [m for m in self.models if m.quality == quality]
    
    def get_sota_models(self) -> List[ModelEntry]:
        """Get state-of-the-art models only"""
        return self.get_models_by_quality(ModelQuality.SOTA)
    
    def recommend_for_system(self, ram_gb: float, has_gpu: bool = False) -> ModelEntry:
        """Recommend best model for system specs"""
        ram_multiplier = 0.7 if has_gpu else 1.0
        
        # Filter to models that fit in RAM
        suitable = [
            m for m in self.models
            if m.ram_min_gb * ram_multiplier <= ram_gb
        ]
        
        if not suitable:
            # Return smallest model as fallback
            return min(self.models, key=lambda m: m.ram_min_gb)
        
        # Prioritize by quality, then by how well it fits the system
        def score(model: ModelEntry) -> tuple:
            quality_scores = {
                ModelQuality.SOTA: 5,
                ModelQuality.EXCELLENT: 4,
                ModelQuality.GOOD: 3,
                ModelQuality.FAST: 2,
                ModelQuality.LEGACY: 1,
            }
            
            # Check if model is in optimal RAM range
            optimal_fit = 1 if ram_gb >= model.ram_optimal_gb else 0
            
            return (quality_scores[model.quality], optimal_fit, -model.ram_min_gb)
        
        return max(suitable, key=score)
    
    def get_new_models_since(self, date: str) -> List[ModelEntry]:
        """Get models released after a specific date"""
        return [m for m in self.models if m.release_date > date]
    
    def get_superseded_models(self) -> List[ModelEntry]:
        """Get models that have newer alternatives"""
        superseded_names = {m.supersedes for m in self.models if m.supersedes}
        return [m for m in self.models if m.name in superseded_names]
    
    def export_to_json(self, filepath: str):
        """Export registry to JSON file"""
        data = {
            "version": self.REGISTRY_VERSION,
            "last_update": datetime.now().isoformat(),
            "models": [m.to_dict() for m in self.models]
        }
        
        import json
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_json(self, filepath: str) -> bool:
        """Load registry from JSON file"""
        try:
            import json
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.models = [ModelEntry(**m) for m in data.get('models', [])]
            self.last_update = datetime.fromisoformat(data.get('last_update', datetime.now().isoformat()))
            return True
        except Exception as e:
            print(f"Failed to load registry: {e}")
            return False
    
    def check_for_updates(self, remote_url: Optional[str] = None) -> List[ModelEntry]:
        """
        Check for new models from remote registry.
        
        Args:
            remote_url: URL to fetch updated registry (future feature)
        
        Returns:
            List of new models not in current registry
        """
        # TODO: Implement remote fetch
        # For now, return empty list
        # In future: fetch from https://api.rocket-cli.dev/models/registry.json
        return []
    
    def get_upgrade_recommendations(self, installed_models: List[str]) -> List[Dict]:
        """
        Get upgrade recommendations for installed models.
        
        Args:
            installed_models: List of currently installed model names
        
        Returns:
            List of dicts with upgrade suggestions
        """
        recommendations = []
        
        for installed in installed_models:
            current = self.get_model(installed)
            
            if not current:
                continue
            
            # Find newer models that supersede this one
            newer = [
                m for m in self.models
                if m.supersedes == installed or
                (m.name.split(':')[0] == installed.split(':')[0] and  # Same family
                 m.release_date > current.release_date)
            ]
            
            if newer:
                best_upgrade = max(newer, key=lambda m: (m.quality.value, m.release_date))
                recommendations.append({
                    'current': installed,
                    'upgrade_to': best_upgrade.name,
                    'reason': f"Newer version: {best_upgrade.specialty}",
                    'quality_improvement': best_upgrade.quality.value != current.quality.value,
                })
        
        return recommendations


# Global registry instance
_registry = ModelRegistry()


def get_registry() -> ModelRegistry:
    """Get the global model registry"""
    return _registry
