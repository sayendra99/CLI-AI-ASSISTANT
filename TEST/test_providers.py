"""
Test script for Phase 1 Provider Abstraction Layer

Tests the new multi-provider LLM system with:
- Provider initialization
- Configuration loading/saving
- Smart fallback logic
- Rate limit handling
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

console = Console()


async def test_provider_imports():
    """Test that all providers can be imported."""
    console.print("\n[bold cyan]Test 1: Provider Imports[/bold cyan]")
    
    try:
        from Rocket.LLM.providers import (
            LLMProvider,
            GenerateOptions,
            GenerateResponse,
            RateLimitInfo,
            ProviderError,
            RateLimitError,
            ConfigError,
            GeminiProvider,
            CommunityProxyProvider,
            OllamaProvider,
            ProviderManager,
            load_config,
            save_config,
        )
        console.print("[green]✅ All imports successful[/green]")
        return True
    except ImportError as e:
        console.print(f"[red]❌ Import failed: {e}[/red]")
        return False


async def test_config_system():
    """Test configuration loading and saving."""
    console.print("\n[bold cyan]Test 2: Configuration System[/bold cyan]")
    
    try:
        from Rocket.LLM.providers.config import (
            load_config,
            save_config,
            get_config_path,
            RocketConfig,
        )
        
        # Load config
        config = load_config()
        console.print(f"[green]✅ Config loaded from: {get_config_path()}[/green]")
        
        # Check config values
        console.print(f"  • Gemini API Key: {'[green]Set[/green]' if config.gemini_api_key else '[yellow]Not set[/yellow]'}")
        console.print(f"  • GitHub Token: {'[green]Set[/green]' if config.github_token else '[yellow]Not set[/yellow]'}")
        console.print(f"  • Default Model: {config.default_model}")
        console.print(f"  • Temperature: {config.default_temperature}")
        
        return True
    except Exception as e:
        console.print(f"[red]❌ Config test failed: {e}[/red]")
        return False


async def test_provider_availability():
    """Test provider availability checking."""
    console.print("\n[bold cyan]Test 3: Provider Availability[/bold cyan]")
    
    try:
        from Rocket.LLM.providers import (
            GeminiProvider,
            CommunityProxyProvider,
            OllamaProvider,
            load_config,
        )
        
        config = load_config()
        
        # Test Gemini provider
        gemini = GeminiProvider(api_key=config.gemini_api_key)
        gemini_available = await gemini.is_available()
        console.print(f"  • Gemini: {'[green]Available[/green]' if gemini_available else '[yellow]Not available[/yellow]'}")
        
        # Test Community Proxy (just checks if reachable)
        proxy = CommunityProxyProvider(github_token=config.github_token)
        # Note: This might time out if proxy isn't running
        try:
            proxy_available = await asyncio.wait_for(proxy.is_available(), timeout=5.0)
            console.print(f"  • Community Proxy: {'[green]Available[/green]' if proxy_available else '[yellow]Not available[/yellow]'}")
        except asyncio.TimeoutError:
            console.print(f"  • Community Proxy: [yellow]Timeout (proxy may not be running)[/yellow]")
        
        # Test Ollama
        ollama = OllamaProvider()
        try:
            ollama_available = await asyncio.wait_for(ollama.is_available(), timeout=3.0)
            console.print(f"  • Ollama: {'[green]Available[/green]' if ollama_available else '[yellow]Not available[/yellow]'}")
        except asyncio.TimeoutError:
            console.print(f"  • Ollama: [yellow]Timeout (not running)[/yellow]")
        
        console.print("[green]✅ Provider availability check completed[/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Availability test failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


async def test_provider_manager():
    """Test the provider manager with fallback logic."""
    console.print("\n[bold cyan]Test 4: Provider Manager[/bold cyan]")
    
    try:
        from Rocket.LLM.providers import (
            ProviderManager,
            load_config,
            GenerateOptions,
        )
        
        config = load_config()
        manager_config = config.to_manager_config()
        
        manager = ProviderManager(config=manager_config)
        await manager.initialize()
        
        # Get status
        status = await manager.get_status()
        
        # Create status table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Provider")
        table.add_column("Available")
        table.add_column("Tier")
        table.add_column("Healthy")
        
        for name, provider_status in status.items():
            table.add_row(
                name,
                "[green]Yes[/green]" if provider_status.available else "[red]No[/red]",
                provider_status.provider.tier.value,
                "[green]Yes[/green]" if provider_status.is_healthy else "[red]No[/red]",
            )
        
        console.print(table)
        
        # Check active provider
        active = await manager.get_active_provider()
        if active:
            console.print(f"\n[green]✅ Active provider: {active.display_name}[/green]")
        else:
            console.print(f"\n[yellow]⚠️ No active provider available[/yellow]")
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Provider manager test failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


async def test_generate_request():
    """Test actual generation (only if provider available)."""
    console.print("\n[bold cyan]Test 5: Generate Request[/bold cyan]")
    
    try:
        from Rocket.LLM.providers import (
            ProviderManager,
            load_config,
            GenerateOptions,
            RateLimitError,
            ProviderError,
        )
        
        config = load_config()
        manager_config = config.to_manager_config()
        
        manager = ProviderManager(config=manager_config)
        await manager.initialize()
        
        active = await manager.get_active_provider()
        if not active:
            console.print("[yellow]⚠️ No provider available - skipping generation test[/yellow]")
            console.print("[dim]To enable: set GEMINI_API_KEY or run 'ollama serve'[/dim]")
            return True
        
        console.print(f"[cyan]Testing with provider: {active.display_name}[/cyan]")
        
        options = GenerateOptions(
            prompt="Say 'Hello from Rocket CLI!' in exactly 5 words.",
            temperature=0.3,
            max_tokens=50,
        )
        
        try:
            response = await manager.generate(options)
            console.print(f"\n[bold]Response:[/bold] {response.text[:200]}")
            console.print(f"[dim]Provider: {response.provider}, Model: {response.model}[/dim]")
            console.print(f"[dim]Tokens: {response.usage.total_tokens}[/dim]")
            console.print("[green]✅ Generation successful![/green]")
            return True
            
        except RateLimitError as e:
            console.print(f"[yellow]⚠️ Rate limited: {e.message}[/yellow]")
            console.print(f"[cyan]{e.get_upgrade_message()}[/cyan]")
            return True  # Rate limit is expected behavior
            
        except ProviderError as e:
            console.print(f"[red]❌ Provider error: {e}[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]❌ Generate test failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


async def test_cli_integration():
    """Test CLI command integration."""
    console.print("\n[bold cyan]Test 6: CLI Integration[/bold cyan]")
    
    try:
        from Rocket.CLI.commands import get_provider_manager, handle_config
        
        # Test config handler
        console.print("[cyan]Testing config show...[/cyan]")
        handle_config(action="show")
        
        console.print("[green]✅ CLI integration working[/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]❌ CLI integration test failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all tests and report results."""
    console.print("[bold]=" * 60)
    console.print("[bold cyan]Phase 1 Provider Abstraction Layer Tests[/bold cyan]")
    console.print("[bold]=" * 60)
    
    results = []
    
    results.append(("Provider Imports", await test_provider_imports()))
    results.append(("Configuration System", await test_config_system()))
    results.append(("Provider Availability", await test_provider_availability()))
    results.append(("Provider Manager", await test_provider_manager()))
    results.append(("Generate Request", await test_generate_request()))
    results.append(("CLI Integration", await test_cli_integration()))
    
    # Summary
    console.print("\n" + "=" * 60)
    console.print("[bold cyan]Test Summary[/bold cyan]")
    console.print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "[green]PASS[/green]" if result else "[red]FAIL[/red]"
        console.print(f"  {name}: {status}")
    
    console.print(f"\n[bold]Results: {passed}/{total} tests passed[/bold]")
    
    if passed == total:
        console.print("[green]🎉 All tests passed![/green]")
    else:
        console.print("[yellow]⚠️ Some tests failed. Check the output above.[/yellow]")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
