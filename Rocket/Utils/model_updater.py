"""
Automatic Model Updater - Keeps Rocket CLI models up-to-date

Features:
- Auto-discovers new models from Ollama library
- Checks for updates to installed models
- One-command upgrade for all models
- Non-intrusive notifications
"""

import asyncio
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from Rocket.Utils.Log import get_logger
from Rocket.Utils.model_registry import get_registry, ModelEntry

logger = get_logger(__name__)


@dataclass
class UpdateInfo:
    """Information about available model updates"""
    model_name: str
    current_version: Optional[str]
    latest_version: str
    size_gb: float
    changelog: str
    priority: str  # "critical", "recommended", "optional"


class ModelUpdater:
    """Handles automatic model updates and discovery"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the model updater.
        
        Args:
            cache_dir: Directory to store update metadata
        """
        self.cache_dir = cache_dir or Path.home() / ".rocket-cli" / "model-cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.update_check_file = self.cache_dir / "last_update_check.json"
        self.registry = get_registry()
    
    def _save_last_check(self):
        """Save timestamp of last update check"""
        data = {
            "last_check": datetime.now().isoformat(),
            "registry_version": self.registry.REGISTRY_VERSION,
        }
        
        with open(self.update_check_file, 'w') as f:
            json.dump(data, f)
    
    def _should_check_for_updates(self, interval_days: int = 7) -> bool:
        """
        Check if enough time has passed since last update check.
        
        Args:
            interval_days: Days between update checks
        
        Returns:
            True if should check for updates
        """
        if not self.update_check_file.exists():
            return True
        
        try:
            with open(self.update_check_file, 'r') as f:
                data = json.load(f)
            
            last_check = datetime.fromisoformat(data['last_check'])
            elapsed = datetime.now() - last_check
            
            return elapsed.days >= interval_days
        except Exception as e:
            logger.debug(f"Error reading update check file: {e}")
            return True
    
    def get_installed_models(self) -> List[str]:
        """Get list of currently installed Ollama models"""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    models = []
                    for line in lines[1:]:  # Skip header
                        if line.strip():
                            parts = line.split()
                            if parts:
                                models.append(parts[0])
                    return models
        except Exception as e:
            logger.debug(f"Failed to list installed models: {e}")
        
        return []
    
    def discover_new_models(self) -> List[ModelEntry]:
        """
        Discover new models in Ollama library that aren't in our registry.
        
        Returns:
            List of newly discovered models
        """
        # This would query Ollama's library API
        # For now, return registry models that aren't installed
        installed = set(self.get_installed_models())
        registry_models = self.registry.get_recommended_models()
        
        new_models = [
            m for m in registry_models
            if m.name not in installed
        ]
        
        return new_models
    
    def check_for_model_updates(self) -> List[UpdateInfo]:
        """
        Check if any installed models have newer versions.
        
        Returns:
            List of available updates
        """
        installed = self.get_installed_models()
        updates = []
        
        for model_name in installed:
            # Check if there's a newer version in registry
            registry_entry = self.registry.get_model(model_name)
            
            if not registry_entry:
                # Check for newer models in same family
                family = model_name.split(':')[0]
                newer_in_family = [
                    m for m in self.registry.get_all_models()
                    if m.name.startswith(family) and m.name != model_name
                ]
                
                if newer_in_family:
                    latest = max(newer_in_family, key=lambda m: m.release_date)
                    updates.append(UpdateInfo(
                        model_name=model_name,
                        current_version=None,
                        latest_version=latest.name,
                        size_gb=latest.size_gb,
                        changelog=f"Upgrade to {latest.specialty}",
                        priority="recommended"
                    ))
        
        return updates
    
    def get_upgrade_recommendations(self) -> List[Dict]:
        """
        Get intelligent upgrade recommendations based on installed models.
        
        Returns:
            List of upgrade suggestions with reasoning
        """
        installed = self.get_installed_models()
        return self.registry.get_upgrade_recommendations(installed)
    
    async def install_model(self, model_name: str, show_progress: bool = True) -> bool:
        """
        Install a new model.
        
        Args:
            model_name: Name of model to install
            show_progress: Whether to show download progress
        
        Returns:
            True if successful
        """
        logger.info(f"Installing model: {model_name}")
        
        try:
            cmd = ["ollama", "pull", model_name]
            
            if show_progress:
                # Show progress to user
                process = subprocess.run(cmd, check=True)
                return process.returncode == 0
            else:
                # Silent installation
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout
                )
                return result.returncode == 0
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install {model_name}: {e}")
            return False
        except subprocess.TimeoutExpired:
            logger.error(f"Installation of {model_name} timed out")
            return False
    
    def auto_upgrade_all(self, dry_run: bool = False) -> Dict[str, bool]:
        """
        Automatically upgrade all installed models to latest versions.
        
        Args:
            dry_run: If True, only show what would be upgraded
        
        Returns:
            Dict mapping model name to upgrade success status
        """
        recommendations = self.get_upgrade_recommendations()
        results = {}
        
        print(f"\n🔄 Found {len(recommendations)} upgrade(s) available\n")
        
        for rec in recommendations:
            current = rec['current']
            upgrade = rec['upgrade_to']
            reason = rec['reason']
            
            print(f"📦 {current} → {upgrade}")
            print(f"   {reason}")
            
            if dry_run:
                print("   [DRY RUN - Would upgrade]")
                results[current] = True
            else:
                print("   Installing...")
                success = asyncio.run(self.install_model(upgrade, show_progress=True))
                results[current] = success
                
                if success:
                    print("   ✅ Upgraded successfully")
                else:
                    print("   ❌ Upgrade failed")
            
            print()
        
        return results
    
    def check_and_notify(self, auto_check: bool = True) -> Optional[str]:
        """
        Check for updates and return notification message if any.
        
        Args:
            auto_check: Only check if enough time has passed
        
        Returns:
            Notification message or None
        """
        if auto_check and not self._should_check_for_updates():
            return None
        
        new_models = self.discover_new_models()
        updates = self.check_for_model_updates()
        
        self._save_last_check()
        
        if not new_models and not updates:
            return None
        
        # Build notification message
        lines = []
        
        if new_models:
            lines.append(f"🆕 {len(new_models)} new model(s) available:")
            for model in new_models[:3]:  # Show top 3
                lines.append(f"   • {model.name} - {model.specialty}")
            if len(new_models) > 3:
                lines.append(f"   ... and {len(new_models) - 3} more")
        
        if updates:
            lines.append(f"\n⬆️  {len(updates)} upgrade(s) available:")
            for update in updates[:3]:
                lines.append(f"   • {update.model_name} → {update.latest_version}")
            if len(updates) > 3:
                lines.append(f"   ... and {len(updates) - 3} more")
        
        lines.append("\n💡 Run 'rocket models upgrade' to update")
        
        return "\n".join(lines)
    
    def list_available_models(self, filter_quality: str = None) -> List[ModelEntry]:
        """
        List all available models from registry.
        
        Args:
            filter_quality: Filter by quality tier (sota, excellent, good, fast)
        
        Returns:
            List of available models
        """
        models = self.registry.get_all_models()
        
        if filter_quality:
            from Rocket.Utils.model_registry import ModelQuality
            quality_map = {
                'sota': ModelQuality.SOTA,
                'excellent': ModelQuality.EXCELLENT,
                'good': ModelQuality.GOOD,
                'fast': ModelQuality.FAST,
                'legacy': ModelQuality.LEGACY,
            }
            
            quality = quality_map.get(filter_quality.lower())
            if quality:
                models = [m for m in models if m.quality == quality]
        
        return models
    
    def install_recommended_for_system(self, ram_gb: float, has_gpu: bool = False) -> bool:
        """
        Install the best model for user's system.
        
        Args:
            ram_gb: Available RAM
            has_gpu: Whether system has GPU
        
        Returns:
            True if successful
        """
        recommended = self.registry.recommend_for_system(ram_gb, has_gpu)
        
        print(f"\n📊 System Analysis:")
        print(f"   RAM: {ram_gb:.1f} GB")
        print(f"   GPU: {'Yes' if has_gpu else 'No'}")
        print()
        print(f"🎯 Recommended Model: {recommended.name}")
        print(f"   {recommended.specialty}")
        print(f"   Quality: {recommended.quality.value}")
        print(f"   Speed: {recommended.speed_rating}")
        print(f"   Size: {recommended.size_gb:.1f} GB")
        print()
        
        # Check if already installed
        installed = self.get_installed_models()
        if recommended.name in installed:
            print(f"✅ {recommended.name} is already installed!")
            return True
        
        # Install
        print(f"📥 Installing {recommended.name}...")
        success = asyncio.run(self.install_model(recommended.name, show_progress=True))
        
        if success:
            print(f"\n✅ Successfully installed {recommended.name}")
            print(f"\n🚀 Ready to use:")
            print(f"   rocket chat --model ollama_chat/{recommended.name} -m 'Your question'")
        else:
            print(f"\n❌ Failed to install {recommended.name}")
        
        return success


def check_for_updates_background():
    """
    Background task to check for updates (non-blocking).
    Called when CLI starts, shows notification if updates available.
    """
    updater = ModelUpdater()
    notification = updater.check_and_notify(auto_check=True)
    
    if notification:
        print("\n" + "=" * 70)
        print(notification)
        print("=" * 70 + "\n")


if __name__ == "__main__":
    # Test the updater
    updater = ModelUpdater()
    
    print("Installed models:")
    for model in updater.get_installed_models():
        print(f"  • {model}")
    
    print("\nChecking for updates...")
    notification = updater.check_and_notify(auto_check=False)
    
    if notification:
        print(notification)
    else:
        print("✅ All models are up to date!")
