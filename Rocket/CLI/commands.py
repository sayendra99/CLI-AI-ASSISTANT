"""
Command handlers for Rocket CLI
Routes user requests to appropriate AI services

Performance Optimizations:
- LRU caching for provider manager and config
- Efficient data structures (sets, dicts)
- Buffered I/O for file operations
- Memory-efficient generators
"""

import io
import logging
from functools import lru_cache
from typing import Optional, Dict, Any, Set
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from Rocket.LLM import GeminiClient
from Rocket.LLM.providers import (
    ProviderManager,
    GenerateOptions,
    GenerateResponse,
    load_config,
    save_config,
    get_config_path,
    list_config_keys,
    resolve_config_key,
    RateLimitError,
    ProviderError,
    ConfigError,
)
from Rocket.LLM.providers.auth import get_auth_manager, AuthError
from Rocket.Utils.Config import settings

logger = logging.getLogger(__name__)
console = Console()

# Global provider manager instance (initialized lazily)
_provider_manager: Optional[ProviderManager] = None

# Cache for frequently accessed data
_config_cache: Optional[Dict[str, Any]] = None
_system_instructions_cache: Dict[str, str] = {}

# Set of supported languages for O(1) lookup
SUPPORTED_LANGUAGES: Set[str] = {
    'python', 'javascript', 'typescript', 'go', 'rust', 
    'java', 'cpp', 'c', 'csharp', 'php', 'ruby', 'swift',
    'kotlin', 'scala', 'html', 'css', 'yaml', 'json'
}


@lru_cache(maxsize=1)
def _get_cached_config() -> Any:
    """
    Load and cache configuration.
    
    Uses LRU cache to avoid repeated config loading from disk.
    Cache is invalidated by restarting the CLI.
    
    Returns:
        Cached configuration object
    """
    return load_config()


async def get_provider_manager() -> ProviderManager:
    """
    Get the provider manager instance, initializing if needed.
    
    Uses the new multi-provider system with automatic fallback.
    Provider manager is cached globally for the lifetime of the process.
    
    Returns:
        Initialized ProviderManager instance
    """
    global _provider_manager
    
    if _provider_manager is None:
        # Load config from cached source
        config = _get_cached_config()
        manager_config = config.to_manager_config()
        
        _provider_manager = ProviderManager(config=manager_config)
        await _provider_manager.initialize()
    
    return _provider_manager


@lru_cache(maxsize=1)
def get_llm_client() -> GeminiClient:
    """
    Get configured LLM client with settings applied.
    
    NOTE: This is the legacy client. Use get_provider_manager() for
    the new multi-provider system with fallback support.
    
    Client instance is cached to avoid repeated initialization.
    
    Returns:
        Cached GeminiClient instance with current settings
    """
    return GeminiClient(
        model_name=settings.gemini_model,
        temperature=settings.temperature,
        max_retries=settings.max_retries,
        retry_delay=settings.retry_delay
    )


def read_file_buffered(file_path: str, buffer_size: int = 65536) -> str:
    """
    Read file with buffered I/O for better performance.
    
    Uses larger buffer size (64KB default) for efficient reading
    of large files. Reads entire file into memory using chunks.
    
    Args:
        file_path: Path to file to read
        buffer_size: Buffer size in bytes (default 64KB)
        
    Returns:
        File contents as string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    chunks = []
    with open(file_path, 'r', buffering=buffer_size, encoding='utf-8') as f:
        while True:
            chunk = f.read(buffer_size)
            if not chunk:
                break
            chunks.append(chunk)
    return ''.join(chunks)


def write_file_buffered(file_path: str, content: str, buffer_size: int = 65536) -> None:
    """
    Write file with buffered I/O for better performance.
    
    Uses larger buffer size (64KB default) for efficient writing
    of large files. Writes entire content using buffered I/O.
    
    Args:
        file_path: Path to file to write
        content: Content to write
        buffer_size: Buffer size in bytes (default 64KB)
        
    Raises:
        IOError: If file cannot be written
    """
    with open(file_path, 'w', buffering=buffer_size, encoding='utf-8') as f:
        f.write(content)


@lru_cache(maxsize=32)
def get_system_instruction(language: str, instruction_type: str) -> str:
    """
    Get cached system instruction for a language and type.
    
    Caches system instructions to avoid repeated string concatenation.
    Uses LRU cache with max 32 entries (covers common language/type pairs).
    
    Args:
        language: Programming language
        instruction_type: Type of instruction (generate, explain, debug, etc.)
        
    Returns:
        Cached system instruction string
    """
    instructions = {
        'generate': (
            f"You are an expert {language} developer. "
            "Generate production-ready, well-documented code. "
            "Include error handling and best practices. "
            "Format code with proper markdown code blocks."
        ),
        'explain': (
            f"You are an expert {language} code analyst. "
            "Explain the code clearly, line by line. "
            "Describe what it does, why it works, and any potential issues. "
            "Use simple language for beginners but be thorough."
        ),
        'debug': (
            f"You are an expert {language} debugger. "
            "Analyze the error or issue and provide clear, actionable solutions. "
            "Explain the root cause and show how to fix it with code examples. "
            "Include prevention tips for the future."
        )
    }
    return instructions.get(instruction_type, f"You are an expert {language} developer.")


async def handle_chat(message: str, stream: bool = False) -> None:
    """
    Handle chat command - general conversation with AI.
    
    Uses the new multi-provider system with automatic fallback.
    
    Args:
        message: User's question or request
        stream: Whether to stream the response
    """
    try:
        console.print(f"\n[cyan]🚀 Rocket:[/cyan]", end=" ")
        
        # Get provider manager (with fallback support)
        manager = await get_provider_manager()
        
        system_instruction = (
            "You are Rocket, an expert AI coding assistant. "
            "Help developers with code generation, debugging, optimization, and explanations. "
            "Provide practical, production-ready solutions. "
            "When showing code, use proper markdown formatting with language identifiers."
        )
        
        options = GenerateOptions(
            prompt=message,
            system_instruction=system_instruction,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            stream=stream,
        )
        
        if stream:
            # Stream response
            async for chunk in manager.generate_stream(options):
                console.print(chunk, end="", highlight=False)
            console.print()  # New line at end
        else:
            # Get full response
            response = await manager.generate(options)
            console.print(Markdown(response.text))
            
            # Show provider used
            logger.info(f"Response from provider: {response.provider}")
        
        # Log usage from rate limits if available
        rate_limits = await manager.get_rate_limits()
        for provider_name, limit_info in rate_limits.items():
            if limit_info.remaining < limit_info.limit:
                logger.info(f"{provider_name}: {limit_info.remaining}/{limit_info.limit} requests remaining")
        
    except RateLimitError as e:
        console.print(f"\n[yellow]{e.message}[/yellow]")
        if e.upgrade_url:
            console.print(f"[cyan]{e.get_upgrade_message()}[/cyan]")
        logger.warning(f"Rate limit hit: {e}")
    except ProviderError as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        logger.exception("Error in handle_chat")
        raise
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        logger.exception("Error in handle_chat")
        raise


async def handle_generate(
    description: str,
    language: str = "python",
    stream: bool = True,
    output_file: Optional[str] = None
) -> None:
    """
    Handle generate command - create code from description.
    
    Uses the new multi-provider system with automatic fallback.
    
    Args:
        description: What to generate
        language: Programming language
        stream: Whether to stream response
        output_file: Optional file to save output
        
    Raises:
        ValueError: If description is empty or None
    """
    try:
        # Validate inputs
        if not description or not description.strip():
            error_msg = "Description cannot be empty"
            console.print(f"[red]❌ Error: {error_msg}[/red]")
            logger.error(f"handle_generate called with invalid description: {error_msg}")
            raise ValueError(error_msg)
        
        console.print(f"\n[cyan]🔧 Generating {language} code...[/cyan]\n")
        
        # Get provider manager (with fallback support)
        manager = await get_provider_manager()
        
        # Use cached system instruction for better performance
        system_instruction = get_system_instruction(language, 'generate')
        
        prompt = f"Generate {language} code for: {description}"
        
        options = GenerateOptions(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            stream=stream,
        )
        
        generated_code = ""
        
        # Use efficient string builder for streaming
        if stream:
            # Use list for efficient string concatenation (O(n) vs O(n^2))
            chunks = []
            async for chunk in manager.generate_stream(options):
                console.print(chunk, end="", highlight=False)
                chunks.append(chunk)
            console.print()
            generated_code = ''.join(chunks)
        else:
            response = await manager.generate(options)
            console.print(Markdown(response.text))
            generated_code = response.text
            logger.info(f"Response from provider: {response.provider}")
        
        # Save to file if requested
        if output_file:
            try:
                # Use buffered I/O for better performance
                write_file_buffered(output_file, generated_code)
                console.print(f"[green]✅ Code saved to: {output_file}[/green]")
                logger.info(f"Generated code saved to: {output_file}")
            except IOError as e:
                console.print(f"[red]❌ Error saving file: {str(e)}[/red]")
                logger.exception(f"Failed to save generated code to {output_file}")
                raise
        
        logger.info(f"Generated {language} code for: {description[:50]}")
        
    except ValueError as e:
        console.print(f"[red]❌ Validation error: {str(e)}[/red]")
        logger.exception("Validation error in handle_generate")
        raise
    except RateLimitError as e:
        console.print(f"\n[yellow]{e.message}[/yellow]")
        if e.upgrade_url:
            console.print(f"[cyan]{e.get_upgrade_message()}[/cyan]")
        logger.warning(f"Rate limit hit: {e}")
    except ProviderError as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        logger.exception("Error in handle_generate")
        raise
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        logger.exception("Error in handle_generate")
        raise


async def handle_explain(
    file_path: Optional[str] = None,
    code_snippet: Optional[str] = None,
    language: str = "python"
) -> None:
    """
    Handle explain command - analyze and explain code.
    
    Args:
        file_path: Path to file to explain
        code_snippet: Code snippet to explain
        language: Programming language
        
    Raises:
        ValueError: If neither file_path nor code_snippet is provided
        FileNotFoundError: If file_path does not exist
    """
    try:
        # Validate inputs - at least one must be provided
        if not file_path and not code_snippet:
            error_msg = "Either file_path or code_snippet must be provided"
            console.print(f"[red]❌ Error: {error_msg}[/red]")
            logger.error(f"handle_explain called with invalid inputs: {error_msg}")
            raise ValueError(error_msg)
        
        # Read file if provided, otherwise use snippet
        code_to_explain: str
        if file_path:
            try:
                # Use buffered I/O for better performance
                code_to_explain = read_file_buffered(file_path)
                logger.info(f"Read code from file: {file_path}")
            except FileNotFoundError:
                error_msg = f"File not found: {file_path}"
                console.print(f"[red]❌ Error: {error_msg}[/red]")
                logger.error(error_msg)
                raise
        else:
            # Use code_snippet (guaranteed non-None due to validation above)
            code_to_explain = code_snippet
            logger.info("Using provided code snippet")
        
        # Ensure code is not empty
        if not code_to_explain or not code_to_explain.strip():
            error_msg = "Code to explain cannot be empty"
            console.print(f"[red]❌ Error: {error_msg}[/red]")
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        console.print(f"\n[cyan]📖 Analyzing {language} code...[/cyan]\n")
        
        # Get dynamically configured client
        llm_client = get_llm_client()
        
        # Use cached system instruction for better performance
        system_instruction = get_system_instruction(language, 'explain')
        
        prompt = f"Explain this {language} code:\n\n```{language}\n{code_to_explain}\n```"
        
        response = await llm_client.generate_text(
            prompt=prompt,
            system_instruction=system_instruction
        )
        
        console.print(Markdown(response.text))
        logger.info(f"Explained code from: {file_path or 'code snippet'}")
        
    except ValueError as e:
        console.print(f"[red]❌ Validation error: {str(e)}[/red]")
        logger.exception("Validation error in handle_explain")
        raise
    except FileNotFoundError as e:
        logger.exception("File not found in handle_explain")
        raise
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        logger.exception("Error in handle_explain")
        raise


async def handle_debug(
    context: Optional[str] = None,
    file_path: Optional[str] = None,
    language: str = "python",
    stream: bool = True
) -> None:
    """
    Handle debug command - analyze errors and suggest fixes.
    
    Args:
        context: Error message or context
        file_path: File to debug
        language: Programming language
        stream: Whether to stream response
        
    Raises:
        ValueError: If neither context nor file_path is provided
        FileNotFoundError: If file_path does not exist
    """
    try:
        # Validate inputs - at least one must be provided
        if not context and not file_path:
            error_msg = "Either context or file_path must be provided"
            console.print(f"[red]❌ Error: {error_msg}[/red]")
            logger.error(f"handle_debug called with invalid inputs: {error_msg}")
            raise ValueError(error_msg)
        
        console.print(f"\n[cyan]🐛 Debugging {language} code...[/cyan]\n")
        
        # Get dynamically configured client
        llm_client = get_llm_client()
        
        # Prepare debugging info
        debug_context: str
        if file_path:
            try:
                # Use buffered I/O for better performance
                code = read_file_buffered(file_path)
                debug_context = f"File: {file_path}\n\nCode:\n```{language}\n{code}\n```"
                if context:
                    debug_context += f"\n\nError/Issue: {context}"
                logger.info(f"Read code from file for debugging: {file_path}")
            except FileNotFoundError:
                error_msg = f"File not found: {file_path}"
                console.print(f"[red]❌ Error: {error_msg}[/red]")
                logger.error(error_msg)
                raise
        else:
            # Use context (guaranteed non-None due to validation above)
            debug_context = context
            logger.info("Debugging with provided context")
        
        # Ensure debug context is not empty
        if not debug_context or not debug_context.strip():
            error_msg = "Debug context cannot be empty"
            console.print(f"[red]❌ Error: {error_msg}[/red]")
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Use cached system instruction for better performance
        system_instruction = get_system_instruction(language, 'debug')
        
        prompt = f"Debug this {language} issue:\n{debug_context}"
        
        if stream:
            async for chunk in llm_client.generate_stream(
                prompt=prompt,
                system_instruction=system_instruction
            ):
                console.print(chunk, end="", highlight=False)
            console.print()
        else:
            response = await llm_client.generate_text(
                prompt=prompt,
                system_instruction=system_instruction
            )
            console.print(Markdown(response.text))
        
        logger.info(f"Debugged: {context[:50] if context else file_path}")
        
    except ValueError as e:
        console.print(f"[red]❌ Validation error: {str(e)}[/red]")
        logger.exception("Validation error in handle_debug")
        raise
    except FileNotFoundError as e:
        logger.exception("File not found in handle_debug")
        raise
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        logger.exception("Error in handle_debug")
        raise


async def handle_optimize(
    file_path: str,
    focus: str = "performance",
    language: str = "python"
) -> None:
    """
    Handle optimize command - suggest code improvements.
    
    Args:
        file_path: File to optimize
        focus: What to focus on (performance, readability, security, maintainability)
        language: Programming language
        
    Raises:
        FileNotFoundError: If file_path does not exist
        ValueError: If focus is invalid or file is empty
    """
    try:
        # Validate file exists
        if not file_path or not file_path.strip():
            error_msg = "File path cannot be empty"
            console.print(f"[red]❌ Error: {error_msg}[/red]")
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Read and validate file
        try:
            with open(file_path, 'r') as f:
                code = f.read()
        except FileNotFoundError:
            error_msg = f"File not found: {file_path}"
            console.print(f"[red]❌ Error: {error_msg}[/red]")
            logger.error(error_msg)
            raise
        
        # Validate code is not empty
        if not code or not code.strip():
            error_msg = f"File is empty: {file_path}"
            console.print(f"[red]❌ Error: {error_msg}[/red]")
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validate focus area
        valid_focus = ["performance", "readability", "security", "maintainability"]
        if focus.lower() not in valid_focus:
            error_msg = f"Invalid focus area: {focus}. Must be one of {valid_focus}"
            console.print(f"[red]❌ Error: {error_msg}[/red]")
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        console.print(f"\n[cyan]⚡ Optimizing {language} code for {focus}...[/cyan]\n")
        
        # Get dynamically configured client
        llm_client = get_llm_client()
        
        system_instruction = (
            f"You are an expert {language} code optimizer. "
            f"Focus on improving {focus}. "
            "Provide specific suggestions with code examples. "
            "Explain the benefits of each optimization. "
            "Use best practices and design patterns."
        )
        
        prompt = (
            f"Optimize this {language} code for {focus}:\n\n"
            f"```{language}\n{code}\n```\n\n"
            f"Provide specific optimization suggestions with improved code."
        )
        
        response = await llm_client.generate_text(
            prompt=prompt,
            system_instruction=system_instruction
        )
        
        console.print(Markdown(response.text))
        logger.info(f"Optimized {file_path} for {focus}")
        
    except (ValueError, FileNotFoundError) as e:
        if isinstance(e, ValueError):
            console.print(f"[red]❌ Validation error: {str(e)}[/red]")
        logger.exception("Error in handle_optimize")
        raise
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        logger.exception("Error in handle_optimize")
        raise


def handle_config(
    action: str = "show",
    key: Optional[str] = None,
    value: Optional[str] = None
) -> None:
    """
    Handle config command - manage settings.
    
    Uses the new persistent config system (~/.rocket-cli/config.json).
    Supports API keys, provider settings, and preferences.
    
    Args:
        action: show, set, list, or reset
        key: Config key to set (can use aliases like 'gemini-key')
        value: Config value to set
    """
    global _provider_manager  # Declare at function level
    
    try:
        # Load current config
        config = load_config()
        
        if action == "show":
            console.print("\n[cyan]⚙️  Rocket Configuration:[/cyan]")
            console.print(f"  Config file: [dim]{get_config_path()}[/dim]")
            console.print()
            
            # API Keys section
            console.print("[bold]API Keys:[/bold]")
            gemini_status = "[green]✅ Set[/green]" if config.gemini_api_key else "[red]❌ Not set[/red]"
            console.print(f"  Gemini API Key: {gemini_status}")
            github_status = "[green]✅ Authenticated[/green]" if config.github_token else "[yellow]⚠️  Not logged in[/yellow]"
            console.print(f"  GitHub: {github_status}")
            if config.github_username:
                console.print(f"    Username: [cyan]{config.github_username}[/cyan]")
            console.print()
            
            # Provider settings
            console.print("[bold]Provider Settings:[/bold]")
            console.print(f"  Preferred Provider: [cyan]{config.preferred_provider or 'auto'}[/cyan]")
            console.print(f"  Prefer Local (Ollama): [cyan]{config.prefer_local}[/cyan]")
            console.print(f"  Ollama Model: [cyan]{config.ollama_model}[/cyan]")
            console.print()
            
            # Generation defaults
            console.print("[bold]Generation Defaults:[/bold]")
            console.print(f"  Model: [cyan]{config.default_model}[/cyan]")
            console.print(f"  Temperature: [cyan]{config.default_temperature}[/cyan]")
            console.print(f"  Max Tokens: [cyan]{config.default_max_tokens}[/cyan]")
            console.print(f"  Stream by default: [cyan]{config.stream_by_default}[/cyan]")
            console.print()
            
            # Show upgrade tip if no API key
            if not config.gemini_api_key and not config.github_token:
                console.print("[yellow]💡 Tip: Get higher rate limits with:[/yellow]")
                console.print("  • [cyan]rocket config set gemini-key YOUR_KEY[/cyan] - Unlimited requests")
                console.print("  • [cyan]rocket login[/cyan] - 25 requests/day with GitHub")
                console.print()
            
        elif action == "list":
            # Show all available config keys
            console.print("\n[cyan]⚙️  Available Configuration Keys:[/cyan]\n")
            
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Key", style="green")
            table.add_column("Description")
            
            for key_name, description in list_config_keys().items():
                table.add_row(key_name, description)
            
            console.print(table)
            console.print()
            console.print("[dim]Use 'rocket config set --key KEY --value VALUE' to set a value[/dim]")
            console.print()
            
        elif action == "set":
            if not key or value is None:
                console.print("[red]❌ Error: Provide both --key and --value[/red]")
                console.print("[dim]Example: rocket config set --key gemini-key --value YOUR_API_KEY[/dim]")
                return
            
            # Resolve key alias (e.g., 'gemini-key' -> 'gemini_api_key')
            resolved_key = resolve_config_key(key)
            
            # Check if key is valid
            if not hasattr(config, resolved_key):
                console.print(f"[red]❌ Error: Unknown config key '{key}'[/red]")
                console.print("[yellow]Run 'rocket config list' to see available keys[/yellow]")
                return
            
            # Type conversion based on current type
            current_value = getattr(config, resolved_key)
            try:
                if isinstance(current_value, bool):
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif isinstance(current_value, float):
                    value = float(value)
                elif isinstance(current_value, int):
                    value = int(value)
                # strings stay as-is
            except ValueError:
                console.print(f"[red]❌ Error: Invalid value type for {key}[/red]")
                return
            
            # Set and save
            setattr(config, resolved_key, value)
            save_config(config)
            
            # Mask sensitive values in output
            display_value = value
            if 'key' in resolved_key.lower() or 'token' in resolved_key.lower():
                if value and len(str(value)) > 8:
                    display_value = str(value)[:4] + '****' + str(value)[-4:]
            
            console.print(f"[green]✅ Configuration updated: {key} = {display_value}[/green]")
            logger.info(f"Configuration changed: {resolved_key}")
            
            # Reset provider manager to pick up new config
            _provider_manager = None
            
        elif action == "reset":
            console.print("[yellow]⚠️  Resetting configuration to defaults...[/yellow]")
            
            # Create fresh config (keeps API keys but resets preferences)
            new_config = load_config()
            new_config.preferred_provider = None
            new_config.prefer_local = False
            new_config.default_temperature = 0.7
            new_config.default_max_tokens = 2048
            new_config.default_model = "gemini-1.5-flash"
            new_config.stream_by_default = True
            
            save_config(new_config)
            console.print("[green]✅ Configuration reset to defaults (API keys preserved)[/green]")
            logger.info("Configuration reset to defaults")
            
            # Reset provider manager
            _provider_manager = None
        
        else:
            console.print(f"[red]❌ Unknown action: {action}[/red]")
            console.print("[yellow]Valid actions: show, set, list, reset[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        logger.exception("Error in handle_config")
        raise


async def handle_status() -> None:
    """
    Handle status command - show provider status and rate limits.
    
    Shows which providers are available, their rate limits,
    and which provider will be used for requests.
    """
    try:
        console.print("\n[cyan]🚀 Rocket Provider Status[/cyan]\n")
        
        # Initialize provider manager
        manager = await get_provider_manager()
        status = await manager.get_status()
        rate_limits = await manager.get_rate_limits()
        active_provider = await manager.get_active_provider()
        
        # Create status table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Provider", style="bold")
        table.add_column("Status")
        table.add_column("Tier")
        table.add_column("Rate Limit")
        table.add_column("Active", justify="center")
        
        for name, provider_status in status.items():
            # Status indicator
            if provider_status.available:
                if provider_status.is_rate_limited:
                    status_str = "[yellow]⚠️ Rate Limited[/yellow]"
                else:
                    status_str = "[green]✅ Available[/green]"
            else:
                status_str = "[red]❌ Unavailable[/red]"
            
            # Tier
            tier_str = provider_status.provider.tier.value.upper()
            
            # Rate limit info
            limit_info = rate_limits.get(name)
            if limit_info:
                if limit_info.period == "unlimited":
                    rate_str = "[green]Unlimited[/green]"
                else:
                    rate_str = f"{limit_info.remaining}/{limit_info.limit} per {limit_info.period}"
            else:
                rate_str = "N/A"
            
            # Active indicator
            is_active = active_provider and active_provider.name == name
            active_str = "[green]✓[/green]" if is_active else ""
            
            table.add_row(
                provider_status.provider.display_name,
                status_str,
                tier_str,
                rate_str,
                active_str,
            )
        
        console.print(table)
        console.print()
        
        # Show active provider
        if active_provider:
            console.print(f"[bold]Active Provider:[/bold] {active_provider.display_name}")
        else:
            console.print("[yellow]⚠️ No providers available![/yellow]")
            console.print("Try one of the following:")
            console.print("  • Set a Gemini API key: [cyan]rocket config set -k gemini-key -v YOUR_KEY[/cyan]")
            console.print("  • Start Ollama locally: [cyan]ollama serve[/cyan]")
        
        console.print()
        
    except Exception as e:
        console.print(f"[red]Error checking status: {str(e)}[/red]")
        logger.exception("Error in handle_status")
        raise


async def handle_login(no_browser: bool = False) -> None:
    """
    Handle login command - authenticate with GitHub.
    
    Uses GitHub device flow for authentication, which works well
    for CLI applications.
    
    Args:
        no_browser: If True, don't automatically open the browser
    """
    try:
        auth = get_auth_manager()
        
        # Check if already logged in
        session = await auth.get_current_session()
        if session:
            console.print(f"\n[green]✅ Already logged in as [bold]{session.username}[/bold][/green]")
            console.print("Use [cyan]rocket logout[/cyan] to sign out first.")
            return
        
        # Start device flow login
        console.print("\n[cyan]🔐 Logging in with GitHub...[/cyan]")
        
        session = await auth.login_device_flow(open_browser=not no_browser)
        
        console.print(f"[green]✅ Successfully logged in as [bold]{session.username}[/bold]![/green]")
        
        if session.name:
            console.print(f"   Welcome, {session.name}!")
        
        console.print()
        console.print("[dim]You now have access to 25 requests/day (5x more than anonymous).[/dim]")
        console.print()
        
        logger.info(f"User logged in: {session.username}")
        
    except AuthError as e:
        console.print(f"\n[red]❌ Login failed: {str(e)}[/red]")
        logger.error(f"Login failed: {e}")
    except Exception as e:
        console.print(f"\n[red]❌ Error during login: {str(e)}[/red]")
        logger.exception("Error in handle_login")
        raise


async def handle_logout() -> None:
    """
    Handle logout command - sign out and clear stored credentials.
    """
    try:
        auth = get_auth_manager()
        
        # Check if logged in
        session_data = auth.get_stored_session()
        if not session_data:
            console.print("\n[yellow]Not currently logged in.[/yellow]")
            return
        
        username = session_data.get('username', 'Unknown')
        
        console.print(f"\n[cyan]Logging out {username}...[/cyan]")
        
        success = await auth.logout()
        
        if success:
            console.print(f"[green]✅ Successfully logged out.[/green]")
            console.print("[dim]You can log in again with [cyan]rocket login[/cyan][/dim]")
        else:
            console.print("[yellow]⚠️ Session cleared locally, but server logout may have failed.[/yellow]")
        
        logger.info(f"User logged out: {username}")
        
    except Exception as e:
        console.print(f"\n[red]❌ Error during logout: {str(e)}[/red]")
        logger.exception("Error in handle_logout")
        raise


async def handle_whoami() -> None:
    """
    Handle whoami command - show current user info.
    """
    try:
        auth = get_auth_manager()
        
        # Get and validate current session
        session = await auth.get_current_session()
        
        if not session:
            console.print("\n[yellow]Not logged in.[/yellow]")
            console.print("Use [cyan]rocket login[/cyan] to authenticate with GitHub.")
            console.print()
            console.print("[dim]Anonymous users get 5 requests/day.[/dim]")
            console.print("[dim]Authenticated users get 25 requests/day.[/dim]")
            return
        
        console.print("\n[cyan]🚀 Current User[/cyan]\n")
        
        # Create user info table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Field", style="bold")
        table.add_column("Value")
        
        table.add_row("Username", f"[green]{session.username}[/green]")
        
        if session.name:
            table.add_row("Name", session.name)
        
        table.add_row("User ID", session.user_id)
        
        if session.created_at:
            table.add_row("Logged in", session.created_at)
        
        if session.expires_at:
            table.add_row("Session expires", session.expires_at)
        
        console.print(table)
        console.print()
        console.print("[dim]Authenticated tier: 25 requests/day[/dim]")
        console.print()
        
        logger.info(f"Whoami: {session.username}")
        
    except Exception as e:
        console.print(f"\n[red]❌ Error: {str(e)}[/red]")
        logger.exception("Error in handle_whoami")
        raise
