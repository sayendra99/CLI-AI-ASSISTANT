#!/usr/bin/env python3
"""
Quick test for Rocket CLI's free Ollama models integration
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from Rocket.LLM.providers.ollama import OllamaProvider


async def test_ollama_provider():
    """Test the enhanced Ollama provider"""
    
    print("=" * 70)
    print("🧪 Testing Rocket CLI - Free Models Integration")
    print("=" * 70)
    print()
    
    # Test 1: Provider initialization
    print("Test 1: Initialize OllamaProvider...")
    provider = OllamaProvider()
    print(f"✅ Default model: {provider.model}")
    print(f"✅ Display name: {provider.display_name}")
    print()
    
    # Test 2: Model recommendations
    print("Test 2: Model Recommendations...")
    print(f"✅ Recommended models: {len(provider.RECOMMENDED_MODELS)} available")
    for i, model in enumerate(provider.RECOMMENDED_MODELS[:5], 1):
        info = provider.get_model_info(model)
        print(f"   {i}. {model}")
        print(f"      • {info['params']} params, {info['specialty']}")
        print(f"      • RAM: {info['ram_min']}-{info['ram_optimal']} GB, Speed: {info['speed']}")
    print()
    
    # Test 3: System-based recommendation
    print("Test 3: Smart Model Selection...")
    test_systems = [
        (4, False, "Low-end laptop"),
        (8, False, "Standard PC"),
        (16, False, "Developer workstation"),
        (32, True, "High-end with GPU"),
    ]
    
    for ram, gpu, desc in test_systems:
        recommended = provider.recommend_model_for_system(ram, gpu)
        info = provider.get_model_info(recommended)
        print(f"   {desc} ({ram}GB RAM, GPU: {gpu})")
        print(f"   → {recommended} ({info['params']})")
    print()
    
    # Test 4: Check if Ollama is available
    print("Test 4: Checking Ollama availability...")
    is_available = await provider.is_available()
    
    if is_available:
        print("✅ Ollama is running and accessible!")
        
        # List available models
        models = await provider.get_models()
        if models:
            print(f"✅ Found {len(models)} installed models:")
            for model in models[:5]:
                print(f"   • {model}")
        else:
            print("⚠️  No models installed yet")
            print("   Run: python setup_free_models.py")
    else:
        print("⚠️  Ollama is not running or not installed")
        print()
        print("📥 To install Ollama:")
        print("   Windows: https://ollama.ai/download/windows")
        print("   macOS:   brew install ollama")
        print("   Linux:   curl -fsSL https://ollama.ai/install.sh | sh")
    
    print()
    
    # Test 5: Model info validation
    print("Test 5: Model Metadata Validation...")
    all_valid = True
    for model_name in provider.RECOMMENDED_MODELS:
        info = provider.get_model_info(model_name)
        if not all(key in info for key in ['params', 'ram_min', 'specialty', 'speed']):
            print(f"❌ Missing metadata for {model_name}")
            all_valid = False
    
    if all_valid:
        print("✅ All models have complete metadata")
    print()
    
    # Cleanup
    await provider.close()
    
    print("=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)
    print()
    
    if not is_available:
        print("⚠️  Next steps:")
        print("   1. Install Ollama (see instructions above)")
        print("   2. Run: python setup_free_models.py")
        print("   3. Start using: rocket chat -m 'Your question'")
    else:
        print("🚀 Ready to use!")
        print("   Run: python setup_free_models.py")
        print("   Or:  rocket chat -m 'Write a Python function'")
    
    print()


if __name__ == "__main__":
    try:
        asyncio.run(test_ollama_provider())
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
