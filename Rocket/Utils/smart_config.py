#!/usr/bin/env python3
"""
Rocket CLI - Intelligent Model Provider Configuration

Automatically configures the best AI model provider based on:
1. System capabilities (CPU, RAM, GPU)
2. Available installations (Ollama, Gemini API key)
3. Network connectivity
4. User preferences

Priority Order:
1. Local Ollama (if installed and capable)
2. Gemini API (if key configured)
3. Community Proxy (fallback)

Author: Rocket AI Team
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Rocket.Utils.ollama_auto_setup import (
    SystemDetector,
    ModelRecommender,
    OllamaInstaller,
    SystemCapabilities,
    OllamaModelRecommendation
)
from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)


class ProviderSelector:
    """Intelligently selects the best AI provider for the system"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize provider selector.
        
        Args:
            config_path: Path to Rocket CLI config file
        """
        self.config_path = config_path or Path.home() / ".rocket" / "config.json"
        self.detector = SystemDetector()
        self.recommender = ModelRecommender()
        self.installer = OllamaInstaller()
    
    def detect_best_provider(self) -> Tuple[str, Dict[str, Any]]:
        """
        Detect the best available provider for this system.
        
        Returns:
            Tuple of (provider_type, config_dict)
            - provider_type: "ollama", "gemini", or "proxy"
            - config_dict: Configuration for the provider
        """
        logger.info("Detecting best AI provider for your system...")
        
        # 1. Check if Ollama is available and suitable
        ollama_config = self._check_ollama()
        if ollama_config:
            logger.info("✅ Ollama detected as best option")
            return "ollama", ollama_config
        
        # 2. Check if Gemini API key is configured
        gemini_config = self._check_gemini()
        if gemini_config:
            logger.info("✅ Gemini API key found")
            return "gemini", gemini_config
        
        # 3. Fallback to community proxy
        logger.info("⚠️  Using community proxy (limited features)")
        return "proxy", {"provider": "community_proxy"}
    
    def _check_ollama(self) -> Optional[Dict[str, Any]]:
        """Check if Ollama is available and recommend a model"""
        
        # Check if Ollama is installed
        if not self.installer.is_ollama_installed():
            logger.debug("Ollama not installed")
            return None
        
        # Detect system capabilities
        caps = self.detector.detect_all()
        
        # Check if system can run Ollama models
        if caps.ram_available_gb < 4:
            logger.warning("Insufficient RAM for Ollama (need at least 4GB)")
            return None
        
        # Get model recommendation
        recommendation = self.recommender.recommend(caps)
        
        # Check if recommended model is installed
        installed_models = self.installer.list_installed_models()
        
        if recommendation.model_name in installed_models:
            return {
                "provider": "ollama",
                "model": recommendation.model_name,
                "config_key": f"ollama_chat/{recommendation.model_name}",
                "reason": recommendation.reason
            }
        
        # Check if any coding model is installed
        coding_models = [m for m in installed_models if "coder" in m or "codellama" in m]
        if coding_models:
            model = coding_models[0]
            return {
                "provider": "ollama",
                "model": model,
                "config_key": f"ollama_chat/{model}",
                "reason": "Using installed model"
            }
        
        # Ollama installed but no models - offer to install
        logger.info(f"Ollama installed but no models found. Recommended: {recommendation.model_name}")
        return None
    
    def _check_gemini(self) -> Optional[Dict[str, Any]]:
        """Check if Gemini API key is configured"""
        
        # Check environment variable
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key and len(api_key) > 10:
            return {
                "provider": "gemini",
                "api_key": api_key,
                "model": "gemini-2.0-flash-exp",
                "source": "environment"
            }
        
        # Check config file
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    config = json.load(f)
                    api_key = config.get("gemini_api_key")
                    if api_key and len(api_key) > 10:
                        return {
                            "provider": "gemini",
                            "api_key": api_key,
                            "model": config.get("gemini_model", "gemini-2.0-flash-exp"),
                            "source": "config"
                        }
            except Exception as e:
                logger.warning(f"Could not read config file: {e}")
        
        return None
    
    def configure_rocket_cli(self, provider_type: str, config: Dict[str, Any]) -> bool:
        """
        Configure Rocket CLI to use the detected provider.
        
        Args:
            provider_type: Type of provider ("ollama", "gemini", "proxy")
            config: Provider configuration
        
        Returns:
            True if configuration was successful
        """
        try:
            # Ensure config directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing config or create new
            existing_config = {}
            if self.config_path.exists():
                with open(self.config_path) as f:
                    existing_config = json.load(f)
            
            # Update config
            if provider_type == "ollama":
                existing_config["default_provider"] = "ollama"
                existing_config["default_model"] = config["config_key"]
                existing_config["ollama_model"] = config["model"]
            elif provider_type == "gemini":
                existing_config["default_provider"] = "gemini"
                existing_config["gemini_api_key"] = config["api_key"]
                existing_config["default_model"] = config["model"]
            else:  # proxy
                existing_config["default_provider"] = "proxy"
            
            # Save config
            with open(self.config_path, 'w') as f:
                json.dump(existing_config, f, indent=2)
            
            logger.info(f"✅ Rocket CLI configured to use {provider_type}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to configure Rocket CLI: {e}")
            return False
    
    def interactive_setup(self) -> bool:
        """
        Interactive setup wizard for Rocket CLI provider configuration.
        
        Returns:
            True if setup completed successfully
        """
        print("=" * 60)
        print("Rocket CLI - Intelligent Provider Setup")
        print("=" * 60)
        print()
        
        # Detect best provider
        provider_type, config = self.detect_best_provider()
        
        print(f"\n🎯 Recommended Provider: {provider_type.upper()}")
        
        if provider_type == "ollama":
            print(f"  Model: {config['model']}")
            print(f"  Reason: {config['reason']}")
            print("\n✅ Ollama provides:")
            print("  • Fast local responses")
            print("  • No API costs")
            print("  • Privacy (data stays local)")
        elif provider_type == "gemini":
            print(f"  Model: {config['model']}")
            print(f"  API Key Source: {config['source']}")
            print("\n✅ Gemini provides:")
            print("  • Cloud-based AI")
            print("  • Latest models")
            print("  • Generous free tier")
        else:
            print("\n⚠️  Community Proxy (fallback):")
            print("  • Limited features")
            print("  • Rate-limited")
            print("  • Recommended: Install Ollama or configure Gemini API")
        
        print("\n" + "=" * 60)
        response = input("Configure Rocket CLI with this provider? (Y/n): ").strip().lower()
        
        if response in ['', 'y', 'yes']:
            if self.configure_rocket_cli(provider_type, config):
                print("\n✅ Setup complete!")
                print("\nYou can now use Rocket CLI:")
                print("  rocket chat -m 'Explain Python decorators'")
                print("  rocket read src/main.py")
                return True
            else:
                print("\n❌ Setup failed")
                return False
        else:
            print("\nSetup cancelled")
            return False
    
    def suggest_improvements(self) -> None:
        """Suggest ways to improve the current setup"""
        provider_type, config = self.detect_best_provider()
        
        print("\n💡 Suggestions to improve your setup:")
        
        if provider_type == "proxy":
            print("\n1. Install Ollama for local, fast AI:")
            print("   Windows: https://ollama.ai/download")
            print("   macOS:   brew install ollama")
            print("   Linux:   curl https://ollama.ai/install.sh | sh")
            print("\n2. Or configure Gemini API:")
            print("   Get free API key: https://makersuite.google.com/app/apikey")
            print("   Set key: export GEMINI_API_KEY='your-key'")
        
        elif provider_type == "ollama":
            # Check if model can be upgraded
            caps = self.detector.detect_all()
            current_model = config["model"]
            recommendation = self.recommender.recommend(caps)
            
            if recommendation.model_name != current_model:
                print(f"\n1. Upgrade to better model:")
                print(f"   Current: {current_model}")
                print(f"   Recommended: {recommendation.model_name}")
                print(f"   Run: ollama pull {recommendation.model_name}")
        
        elif provider_type == "gemini":
            print("\n1. For faster, offline responses, consider installing Ollama:")
            print("   Windows: https://ollama.ai/download")
            print("   macOS:   brew install ollama")
            print("   Linux:   curl https://ollama.ai/install.sh | sh")


def main():
    """Main entry point for intelligent provider setup"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Rocket CLI - Intelligent Provider Setup"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatically configure without prompts"
    )
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Show suggestions for improving setup"
    )
    
    args = parser.parse_args()
    
    selector = ProviderSelector()
    
    if args.suggest:
        selector.suggest_improvements()
    elif args.auto:
        provider_type, config = selector.detect_best_provider()
        selector.configure_rocket_cli(provider_type, config)
        print(f"✅ Configured Rocket CLI to use {provider_type}")
    else:
        selector.interactive_setup()


if __name__ == "__main__":
    main()
