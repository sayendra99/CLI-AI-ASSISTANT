#!/usr/bin/env python3
"""
Rocket CLI - Quick Setup for Free AI Models

This script helps users get started with 100% free AI models.
No API keys required, no cost, unlimited usage!

Includes automatic update checking and model recommendations.
"""

import subprocess
import sys
import platform
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from Rocket.Utils.model_updater import ModelUpdater
    from Rocket.Utils.model_registry import get_registry
    USE_SMART_SETUP = True
except ImportError:
    # Fallback to basic setup if imports fail
    USE_SMART_SETUP = False
    print("⚠️  Advanced features unavailable (missing dependencies)")


def print_header():
    """Print welcome header"""
    print("=" * 70)
    print("🚀 ROCKET CLI - FREE AI MODELS SETUP")
    print("=" * 70)
    print()
    print("Get enterprise-quality AI coding assistant for FREE!")
    print("No API keys • No cost • Unlimited usage • 100% private")
    print()
    if USE_SMART_SETUP:
        print("✨ Smart Setup: Auto-detects best model for your system")
        print("🔄 Auto-Update: Checks for new models periodically")
    print()


def check_ollama():
    """Check if Ollama is installed"""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_ollama_instructions():
    """Show installation instructions for Ollama"""
    os_type = platform.system()
    
    print("⚠️  Ollama is not installed!")
    print()
    print("📥 Installation Instructions:")
    print()
    
    if os_type == "Windows":
        print("Windows:")
        print("  Option 1: Download installer from https://ollama.ai/download/windows")
        print("  Option 2: Run: winget install Ollama.Ollama")
    elif os_type == "Darwin":  # macOS
        print("macOS:")
        print("  Run: brew install ollama")
    elif os_type == "Linux":
        print("Linux:")
        print("  Run: curl -fsSL https://ollama.ai/install.sh | sh")
    
    print()
    print("After installation, run this script again!")
    print()


def get_system_ram():
    """Get available RAM"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        return memory.available / (1024 ** 3)
    except ImportError:
        print("Installing psutil for system detection...")
        subprocess.run([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil
        memory = psutil.virtual_memory()
        return memory.available / (1024 ** 3)


def recommend_model(ram_gb):
    """Recommend best model based on RAM"""
    if ram_gb >= 16:
        return "qwen2.5-coder:7b", "BEST - State-of-the-art coding model"
    elif ram_gb >= 10:
        return "qwen2.5-coder:3b", "FAST - Great balance of speed and quality"
    else:
        return "qwen2.5-coder:1.5b", "ULTRA-FAST - Perfect for your system"


def pull_model(model_name):
    """Download/pull the model"""
    print(f"📥 Downloading {model_name}...")
    print("This may take a few minutes depending on your internet speed.")
    print()
    
    try:
        result = subprocess.run(
            ["ollama", "pull", model_name],
            check=True
        )
        return result.returncode == 0
    except subprocess.CalledProcessError:
        print(f"❌ Failed to download {model_name}")
        return False


def list_installed_models():
    """List currently installed models"""
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
                models = [line.split()[0] for line in lines[1:] if line.strip()]
                return models
    except Exception:
        pass
    
    return []


def main():
    """Main setup flow"""
    print_header()
    
    # Step 1: Check Ollama
    print("Step 1: Checking Ollama installation...")
    if not check_ollama():
        install_ollama_instructions()
        return 1
    
    print("✅ Ollama is installed")
    print()
    
    # Use smart setup if available
    if USE_SMART_SETUP:
        return smart_setup()
    else:
        return basic_setup()


def smart_setup():
    """Smart setup using model updater"""
    updater = ModelUpdater()
    
    # Check for updates
    print("🔍 Checking for new models...")
    notification = updater.check_and_notify(auto_check=False)
    
    if notification:
        print(notification)
        print()
    
    # Detect system and recommend
    print("Step 2: Analyzing your system...")
    ram_gb = get_system_ram()
    
    # Simple GPU detection
    has_gpu = False
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            timeout=3
        )
        has_gpu = result.returncode == 0
    except:
        pass
    
    print(f"📊 System specs:")
    print(f"   RAM: {ram_gb:.1f} GB available")
    print(f"   GPU: {'Detected' if has_gpu else 'Not detected'}")
    print()
    
    # Install recommended model
    print("Step 3: Installing optimal model...")
    success = updater.install_recommended_for_system(ram_gb, has_gpu)
    
    if success:
        print_success_message()
        return 0
    else:
        print("\n⚠️  Installation incomplete. See troubleshooting above.")
        return 1


def basic_setup():
    """Basic setup (legacy fallback)"""
    # Step 2: Detect system
    print("Step 2: Detecting your system...")
    ram_gb = get_system_ram()
    print(f"📊 Available RAM: {ram_gb:.1f} GB")
    print()
    
    # Step 3: Recommend model
    print("Step 3: Selecting best model for your system...")
    recommended_model, reason = recommend_model(ram_gb)
    print(f"🎯 Recommended: {recommended_model}")
    print(f"   Reason: {reason}")
    print()
    
    # Check if already installed
    installed = list_installed_models()
    if recommended_model in installed:
        print(f"✅ {recommended_model} is already installed!")
        print()
        print_success_message(recommended_model)
        return 0
    
    # Step 4: Install model
    print("Step 4: Installing the model...")
    user_input = input(f"Install {recommended_model}? [Y/n]: ").strip().lower()
    
    if user_input in ['', 'y', 'yes']:
        if pull_model(recommended_model):
            print()
            print("✅ Model installed successfully!")
            print()
            print_success_message(recommended_model)
            return 0
        else:
            print()
            print("❌ Installation failed. Please try manually:")
            print(f"   ollama pull {recommended_model}")
            return 1
    else:
        print("Skipped installation.")
        print(f"You can install later with: ollama pull {recommended_model}")
        return 0


def print_success_message(model_name=None):
    """Print success message"""
    print()
    print("=" * 70)
    print("🎉 SETUP COMPLETE!")
    print("=" * 70)
    print()
    
    if model_name:
        print("🚀 Quick Start:")
        print(f"   rocket chat --model ollama_chat/{model_name} -m 'Write a function'")
        print()
        print("📖 Set as default:")
        print(f"   rocket config set default_model ollama_chat/{model_name}")
    else:
        print("🚀 Quick Start:")
        print("   rocket chat -m 'Write a Python function'")
        print()
        print("📖 Model Management:")
        print("   python rocket_models.py list       # List all models")
        print("   python rocket_models.py check      # Check for updates")
        print("   python rocket_models.py upgrade    # Upgrade models")
    
    print()
    print("🔥 Available Commands:")
    print("   python rocket_models.py list       # See all available models")
    print("   python rocket_models.py check      # Check for new models")
    print("   python rocket_models.py upgrade    # Auto-upgrade to latest")
    print()
    print("📚 Full guide: FREE_MODELS_GUIDE.md")
    print()
    print("Happy coding! 🎉")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nFor help, see FREE_MODELS_GUIDE.md")
        sys.exit(1)
