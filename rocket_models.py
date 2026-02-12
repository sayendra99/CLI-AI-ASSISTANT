"""
Model Management CLI Commands

Provides user-friendly commands for:
- Listing available models
- Checking for updates
- Auto-upgrading models
- Installing recommended models
"""

import argparse
import sys
import os
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    try:
        import codecs
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
        if sys.stderr.encoding != 'utf-8':
            sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Rocket.Utils.model_updater import ModelUpdater
from Rocket.Utils.model_registry import get_registry, ModelQuality


def cmd_list_models(args):
    """List all available models"""
    updater = ModelUpdater()
    models = updater.list_available_models(filter_quality=args.quality)
    
    if not models:
        print("No models found.")
        return
    
    print("\n" + "=" * 80)
    print(f"📦 Available Free Models ({len(models)} total)")
    print("=" * 80 + "\n")
    
    # Group by quality
    quality_groups = {}
    for model in models:
        quality = model.quality.value
        if quality not in quality_groups:
            quality_groups[quality] = []
        quality_groups[quality].append(model)
    
    # Display grouped
    quality_order = ['state-of-the-art', 'excellent', 'good', 'fast', 'legacy']
    
    for quality in quality_order:
        if quality not in quality_groups:
            continue
        
        print(f"\n🏆 {quality.upper()}")
        print("-" * 80)
        
        for model in quality_groups[quality]:
            installed = "✅" if model.name in updater.get_installed_models() else "  "
            print(f"{installed} {model.name:<25} | {model.params:>5} | RAM: {model.ram_min_gb:>2}-{model.ram_optimal_gb:<2} GB | {model.speed_rating:<12}")
            print(f"   └─ {model.specialty}")
            if args.verbose:
                print(f"      Released: {model.release_date} | Size: {model.size_gb:.1f} GB")
    
    print("\n" + "=" * 80)
    print("💡 Install a model: rocket models install <model-name>")
    print("💡 Auto-install best: rocket models recommend")
    print("=" * 80 + "\n")


def cmd_list_installed(args):
    """List installed models"""
    updater = ModelUpdater()
    installed = updater.get_installed_models()
    
    if not installed:
        print("No models installed.")
        print("\n💡 Install recommended model: rocket models recommend")
        return
    
    registry = get_registry()
    
    print("\n" + "=" * 80)
    print(f"📦 Installed Models ({len(installed)} total)")
    print("=" * 80 + "\n")
    
    for model_name in installed:
        entry = registry.get_model(model_name)
        
        if entry:
            print(f"✅ {model_name}")
            print(f"   └─ {entry.specialty}")
            print(f"      Quality: {entry.quality.value} | RAM: {entry.ram_min_gb}-{entry.ram_optimal_gb} GB | Speed: {entry.speed_rating}")
        else:
            print(f"✅ {model_name}")
            print(f"   └─ (Not in registry)")
        print()
    
    print("=" * 80 + "\n")


def cmd_check_updates(args):
    """Check for model updates"""
    updater = ModelUpdater()
    
    print("\n🔍 Checking for updates...\n")
    
    # Check for new models
    new_models = updater.discover_new_models()
    
    if new_models:
        print(f"🆕 {len(new_models)} new model(s) available:\n")
        for model in new_models[:10]:  # Show top 10
            print(f"   • {model.name:<25} - {model.specialty}")
            print(f"     Quality: {model.quality.value} | RAM: {model.ram_min_gb}-{model.ram_optimal_gb} GB")
            print()
    
    # Check for upgrades
    upgrades = updater.get_upgrade_recommendations()
    
    if upgrades:
        print(f"\n⬆️  {len(upgrades)} upgrade(s) recommended:\n")
        for rec in upgrades:
            print(f"   • {rec['current']} → {rec['upgrade_to']}")
            print(f"     Reason: {rec['reason']}")
            print()
    
    if not new_models and not upgrades:
        print("✅ All models are up to date!")
        print("✅ No new models available")
    
    print("\n💡 To upgrade: rocket models upgrade")
    print("💡 To install new: rocket models install <model-name>")
    print()


def cmd_upgrade(args):
    """Upgrade installed models"""
    updater = ModelUpdater()
    
    if args.dry_run:
        print("\n🔍 DRY RUN - Showing what would be upgraded:\n")
    
    results = updater.auto_upgrade_all(dry_run=args.dry_run)
    
    if not results:
        print("\n✅ No upgrades needed - all models are up to date!\n")
        return
    
    if not args.dry_run:
        # Summary
        success_count = sum(1 for v in results.values() if v)
        total = len(results)
        
        print("\n" + "=" * 80)
        print(f"✅ Upgraded {success_count}/{total} model(s) successfully")
        print("=" * 80 + "\n")


def cmd_install(args):
    """Install a specific model"""
    updater = ModelUpdater()
    registry = get_registry()
    
    model_name = args.model
    
    # Check if model exists in registry
    entry = registry.get_model(model_name)
    
    if entry:
        print(f"\n📦 Installing: {model_name}")
        print(f"   {entry.specialty}")
        print(f"   Quality: {entry.quality.value}")
        print(f"   Size: {entry.size_gb:.1f} GB")
        print(f"   RAM needed: {entry.ram_min_gb}-{entry.ram_optimal_gb} GB")
        print()
    else:
        print(f"\n⚠️  Model '{model_name}' not found in registry.")
        print("   Installing anyway (assuming it exists in Ollama library)...")
        print()
    
    import asyncio
    success = asyncio.run(updater.install_model(model_name, show_progress=True))
    
    if success:
        print(f"\n✅ Successfully installed {model_name}")
        print(f"\n🚀 To use:")
        print(f"   rocket chat --model ollama_chat/{model_name} -m 'Your question'")
    else:
        print(f"\n❌ Failed to install {model_name}")
        print("\n💡 Make sure:")
        print("   1. Ollama is running")
        print("   2. Model name is correct")
        print("   3. You have internet connection")


def cmd_recommend(args):
    """Install recommended model for user's system"""
    updater = ModelUpdater()
    
    # Detect system (requires psutil)
    try:
        import psutil
        memory = psutil.virtual_memory()
        ram_gb = memory.available / (1024 ** 3)
    except ImportError:
        print("⚠️  Cannot detect system specs (psutil not installed)")
        ram_gb = float(input("Enter available RAM in GB: "))
    
    has_gpu = input("Do you have a GPU? [y/N]: ").lower() in ['y', 'yes']
    
    updater.install_recommended_for_system(ram_gb, has_gpu)


def cmd_search(args):
    """Search for models by keyword"""
    registry = get_registry()
    keyword = args.keyword.lower()
    
    matches = [
        m for m in registry.get_all_models()
        if keyword in m.name.lower() or 
           keyword in m.specialty.lower() or
           keyword in ' '.join(m.recommended_for).lower()
    ]
    
    if not matches:
        print(f"\nNo models found matching '{args.keyword}'")
        return
    
    print(f"\n🔍 Found {len(matches)} model(s) matching '{args.keyword}':\n")
    
    updater = ModelUpdater()
    installed = set(updater.get_installed_models())
    
    for model in matches:
        status = "✅ Installed" if model.name in installed else "  Available"
        print(f"{status} | {model.name}")
        print(f"   {model.specialty}")
        print(f"   Quality: {model.quality.value} | RAM: {model.ram_min_gb}-{model.ram_optimal_gb} GB | {model.speed_rating}")
        print()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Rocket CLI - Model Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  rocket models list                    # List all available models
  rocket models installed              # List installed models
  rocket models check                  # Check for updates
  rocket models upgrade                # Upgrade all models
  rocket models install qwen2.5-coder:7b  # Install specific model
  rocket models recommend              # Install best model for your system
  rocket models search coding          # Search for models
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available models')
    list_parser.add_argument('-q', '--quality', choices=['sota', 'excellent', 'good', 'fast', 'legacy'],
                            help='Filter by quality tier')
    list_parser.add_argument('-v', '--verbose', action='store_true',
                            help='Show detailed information')
    list_parser.set_defaults(func=cmd_list_models)
    
    # Installed command
    installed_parser = subparsers.add_parser('installed', help='List installed models')
    installed_parser.set_defaults(func=cmd_list_installed)
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check for updates')
    check_parser.set_defaults(func=cmd_check_updates)
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser('upgrade', help='Upgrade models')
    upgrade_parser.add_argument('--dry-run', action='store_true',
                               help='Show what would be upgraded without doing it')
    upgrade_parser.set_defaults(func=cmd_upgrade)
    
    # Install command
    install_parser = subparsers.add_parser('install', help='Install a model')
    install_parser.add_argument('model', help='Model name to install')
    install_parser.set_defaults(func=cmd_install)
    
    # Recommend command
    recommend_parser = subparsers.add_parser('recommend', help='Install recommended model')
    recommend_parser.set_defaults(func=cmd_recommend)
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for models')
    search_parser.add_argument('keyword', help='Search keyword')
    search_parser.set_defaults(func=cmd_search)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()
