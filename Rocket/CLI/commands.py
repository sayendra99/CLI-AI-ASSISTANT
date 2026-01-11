"""
Command handlers for Rocket CLI
Routes user requests to appropriate AI services
"""

import logging
from typing import Optional
from rich.console import Console
from rich.markdown import Markdown

from Rocket.LLM import GeminiClient
from Rocket.Utils.Config import settings

logger = logging.getLogger(__name__)
console = Console()


def get_llm_client() -> GeminiClient:
    """
    Get configured LLM client with settings applied.
    
    Constructs a new client on each call to respect dynamic configuration changes.
    This ensures that settings modifications via handle_config take effect immediately.
    
    Returns:
        Configured GeminiClient instance with current settings
    """
    return GeminiClient(
        model_name=settings.gemini_model,
        temperature=settings.temperature,
        max_retries=settings.max_retries,
        retry_delay=settings.retry_delay
    )


async def handle_chat(message: str, stream: bool = False) -> None:
    """
    Handle chat command - general conversation with AI.
    
    Args:
        message: User's question or request
        stream: Whether to stream the response
    """
    try:
        console.print(f"\n[cyan]🚀 Rocket:[/cyan]", end=" ")
        
        # Get dynamically configured client
        llm_client = get_llm_client()
        
        system_instruction = (
            "You are Rocket, an expert AI coding assistant. "
            "Help developers with code generation, debugging, optimization, and explanations. "
            "Provide practical, production-ready solutions. "
            "When showing code, use proper markdown formatting with language identifiers."
        )
        
        if stream:
            # Stream response
            async for chunk in llm_client.generate_stream(
                prompt=message,
                system_instruction=system_instruction
            ):
                console.print(chunk, end="", highlight=False)
            console.print()  # New line at end
        else:
            # Get full response
            response = await llm_client.generate_text(
                prompt=message,
                system_instruction=system_instruction
            )
            console.print(Markdown(response.text))
        
        # Log usage stats
        stats = llm_client.get_usage_stats()
        logger.info(f"Usage - Requests: {stats['total_requests']}, Tokens: {stats['total_tokens']}")
        
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
    
    Args:
        description: What to generate
        language: Programming language
        stream: Whether to stream response
        output_file: Optional file to save output
    """
    try:
        console.print(f"\n[cyan]🔧 Generating {language} code...[/cyan]\n")
        
        # Get dynamically configured client
        llm_client = get_llm_client()
        
        system_instruction = (
            f"You are an expert {language} developer. "
            "Generate production-ready, well-documented code. "
            "Include error handling and best practices. "
            "Format code with proper markdown code blocks."
        )
        
        prompt = f"Generate {language} code for: {description}"
        
        generated_code = ""
        
        if stream:
            async for chunk in llm_client.generate_stream(
                prompt=prompt,
                system_instruction=system_instruction
            ):
                console.print(chunk, end="", highlight=False)
                generated_code += chunk
            console.print()
        else:
            response = await llm_client.generate_text(
                prompt=prompt,
                system_instruction=system_instruction
            )
            console.print(Markdown(response.text))
            generated_code = response.text
        
        # Save to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                f.write(generated_code)
            console.print(f"[green]✅ Code saved to: {output_file}[/green]")
        
        logger.info(f"Generated code for: {description[:50]}")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
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
    """
    try:
        # Read file if provided
        code_to_explain = code_snippet
        if file_path:
            with open(file_path, 'r') as f:
                code_to_explain = f.read()
        
        console.print(f"\n[cyan]📖 Analyzing {language} code...[/cyan]\n")
        
        # Get dynamically configured client
        llm_client = get_llm_client()
        
        system_instruction = (
            f"You are an expert {language} code analyst. "
            "Explain the code clearly, line by line. "
            "Describe what it does, why it works, and any potential issues. "
            "Use simple language for beginners but be thorough."
        )
        
        prompt = f"Explain this {language} code:\n\n```{language}\n{code_to_explain}\n```"
        
        response = await llm_client.generate_text(
            prompt=prompt,
            system_instruction=system_instruction
        )
        
        console.print(Markdown(response.text))
        logger.info(f"Explained code from: {file_path or 'snippet'}")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
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
    """
    try:
        console.print(f"\n[cyan]🐛 Debugging {language} code...[/cyan]\n")
        
        # Get dynamically configured client
        llm_client = get_llm_client()
        
        # Prepare debugging info
        debug_context = context
        if file_path:
            with open(file_path, 'r') as f:
                code = f.read()
            debug_context = f"File: {file_path}\n\nCode:\n```{language}\n{code}\n```\n\nError/Issue: {context}"
        
        system_instruction = (
            f"You are an expert {language} debugger. "
            "Analyze the error or issue and provide clear, actionable solutions. "
            "Explain the root cause and show how to fix it with code examples. "
            "Include prevention tips for the future."
        )
        
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
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
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
    """
    try:
        with open(file_path, 'r') as f:
            code = f.read()
        
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
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        logger.exception("Error in handle_optimize")
        raise


def handle_config(
    action: str = "show",
    key: Optional[str] = None,
    value: Optional[str] = None
) -> None:
    """
    Handle config command - manage settings.
    
    Allows viewing and modifying LLM configuration settings.
    
    Args:
        action: show, set, or reset
        key: Config key to set
        value: Config value to set
    """
    try:
        if action == "show":
            console.print("\n[cyan]⚙️  Rocket Configuration:[/cyan]")
            console.print(f"  API Key: {'[green]✅ Set[/green]' if settings.gemini_api_key else '[red]❌ Not set[/red]'}")
            console.print(f"  Model: [cyan]{settings.gemini_model}[/cyan]")
            console.print(f"  Temperature: [cyan]{settings.temperature}[/cyan]")
            console.print(f"  Max Retries: [cyan]{settings.max_retries}[/cyan]")
            console.print(f"  Retry Delay: [cyan]{settings.retry_delay}s[/cyan]")
            console.print()
            
        elif action == "set":
            if not key or not value:
                console.print("[red]❌ Error: Provide both --key and --value[/red]")
                return
            
            # Validate and set configuration
            valid_keys = {
                "model": "gemini_model",
                "temperature": "temperature",
                "max_retries": "max_retries",
                "retry_delay": "retry_delay",
                "api_key": "gemini_api_key"
            }
            
            if key.lower() not in valid_keys:
                console.print(f"[red]❌ Error: Unknown config key '{key}'[/red]")
                console.print(f"[yellow]Valid keys: {', '.join(valid_keys.keys())}[/yellow]")
                return
            
            attr_name = valid_keys[key.lower()]
            
            # Type conversion for numeric fields
            try:
                if attr_name == "temperature":
                    value = float(value)
                elif attr_name == "max_retries":
                    value = int(value)
                elif attr_name == "retry_delay":
                    value = float(value)
            except ValueError:
                console.print(f"[red]❌ Error: Invalid value type for {key}[/red]")
                return
            
            # Set the attribute
            setattr(settings, attr_name, value)
            console.print(f"[green]✅ Configuration updated: {key} = {value}[/green]")
            logger.info(f"Configuration changed: {key} = {value}")
            
        elif action == "reset":
            console.print("[yellow]⚠️  Resetting to default configuration...[/yellow]")
            settings.gemini_model = "gemini-1.5-flash"
            settings.temperature = 0.7
            settings.max_retries = 3
            settings.retry_delay = 1.0
            console.print("[green]✅ Configuration reset to defaults[/green]")
            logger.info("Configuration reset to defaults")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        logger.exception("Error in handle_config")
        raise
