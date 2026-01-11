"""
Rocket CLI - AI Coding Assistant
Main entry point for CLI commands and routes handling user requests
"""

import logging
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

# Configure logging with Rich formatting
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)
console = Console()

# Create Typer app
app = typer.Typer(
    name="rocket",
    help="Rocket CLI - AI-Powered Coding Assistant for developers",
    add_completion=True,
    pretty_exceptions_enable=True
)


@app.command("chat")
def chat(
    message: str = typer.Option(..., "--message", "-m", help="Question or request for the AI assistant"),
    stream: bool = typer.Option(False, "--stream", "-s", help="Stream response in real-time")
):
    """
    Chat with Rocket AI Assistant for coding solutions.
    
    Supports: Frontend, Backend, DevOps, System Design, and Enterprise Solutions
    
    Examples:
        rocket chat -m "Explain React hooks in detail"
        rocket chat -m "Create a FastAPI REST API with authentication" --stream
        rocket chat -m "Design a Kubernetes deployment for a microservice"
    """
    try:
        from Rocket.CLI.commands import handle_chat
        
        logger.info(f"💬 Chat command: {message[:60]}...")
        handle_chat(message=message, stream=stream)
        
    except Exception as e:
        console.print(f"[red]❌ Error in chat command: {str(e)}[/red]")
        logger.exception("Chat command failed")
        raise typer.Exit(1)


@app.command("generate")
def generate(
    description: str = typer.Argument(..., help="Description of what to generate"),
    language: str = typer.Option("python", "--language", "-l", help="Programming language (python, javascript, typescript, go, rust, java)"),
    stream: bool = typer.Option(True, "--stream", "-s", help="Stream response in real-time"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Save generated code to file")
):
    """
    Generate code snippets using Rocket AI Assistant.
    
    Supports multiple programming languages and frameworks.
    
    Examples:
        rocket generate "REST API with FastAPI" --language python
        rocket generate "React component with hooks" --language javascript
        rocket generate "Docker config for Node.js app" -o Dockerfile
        rocket generate "K8s deployment manifest" --language yaml --output deployment.yaml --stream
    """
    try:
        from Rocket.CLI.commands import handle_generate
        
        logger.info(f"🔧 Generate command: {description[:50]}... (Language: {language})")
        
        if not description or len(description.strip()) == 0:
            console.print("[red]❌ Error: Description cannot be empty[/red]")
            raise typer.Exit(1)
        
        handle_generate(
            description=description,
            language=language,
            stream=stream,
            output_file=output_file
        )
        
    except Exception as e:
        console.print(f"[red]❌ Error in generate command: {str(e)}[/red]")
        logger.exception("Generate command failed")
        raise typer.Exit(1)


@app.command("explain")
def explain(
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Path to file to explain"),
    code: Optional[str] = typer.Option(None, "--code", "-c", help="Code snippet to explain"),
    language: str = typer.Option("python", "--language", "-l", help="Programming language")
):
    """
    Explain code from a file or snippet.
    
    Analyzes and explains what the code does, line by line.
    
    Examples:
        rocket explain --file myapp.py
        rocket explain -c "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)"
        rocket explain --file async_handler.js --language javascript
    """
    try:
        from Rocket.CLI.commands import handle_explain
        
        # Validate input
        if not file and not code:
            console.print("[red]❌ Error: Provide either --file or --code[/red]")
            raise typer.Exit(1)
        
        if file and code:
            console.print("[yellow]⚠️  Warning: Both file and code provided. Using file.[/yellow]")
        
        logger.info(f"📖 Explain command: file={file or 'N/A'}, code_snippet={bool(code)}")
        
        handle_explain(
            file_path=file,
            code_snippet=code,
            language=language
        )
        
    except FileNotFoundError:
        console.print(f"[red]❌ Error: File not found: {file}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error in explain command: {str(e)}[/red]")
        logger.exception("Explain command failed")
        raise typer.Exit(1)


@app.command("debug")
def debug(
    context: Optional[str] = typer.Option(None, "--context", "-c", help="Error message or context"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="File path to debug"),
    language: str = typer.Option("python", "--language", "-l", help="Programming language"),
    stream: bool = typer.Option(True, "--stream", "-s", help="Stream response in real-time")
):
    """
    Debug errors and issues in your code.
    
    Analyzes error messages and suggests fixes.
    
    Examples:
        rocket debug -c "TypeError: 'NoneType' object is not subscriptable"
        rocket debug --file app.py
        rocket debug -c "CORS error when accessing API" --language javascript --stream
    """
    try:
        from Rocket.CLI.commands import handle_debug
        
        # Validate input
        if not context and not file:
            console.print("[red]❌ Error: Provide either --context or --file[/red]")
            raise typer.Exit(1)
        
        logger.info(f"🐛 Debug command: context={bool(context)}, file={file or 'N/A'}")
        
        handle_debug(
            context=context,
            file_path=file,
            language=language,
            stream=stream
        )
        
    except FileNotFoundError:
        console.print(f"[red]❌ Error: File not found: {file}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error in debug command: {str(e)}[/red]")
        logger.exception("Debug command failed")
        raise typer.Exit(1)


@app.command("optimize")
def optimize(
    file: str = typer.Option(..., "--file", "-f", help="File to optimize"),
    focus: str = typer.Option("performance", "--focus", "-fo", help="Focus area: performance, readability, security, maintainability"),
    language: str = typer.Option("python", "--language", "-l", help="Programming language")
):
    """
    Optimize code for performance, readability, or security.
    
    Suggests improvements and refactoring opportunities.
    
    Examples:
        rocket optimize --file app.py --focus performance
        rocket optimize -f component.jsx --language javascript --focus readability
    """
    try:
        from Rocket.CLI.commands import handle_optimize
        
        valid_focus = ["performance", "readability", "security", "maintainability"]
        if focus not in valid_focus:
            console.print(f"[red]❌ Error: Focus must be one of {valid_focus}[/red]")
            raise typer.Exit(1)
        
        logger.info(f"⚡ Optimize command: file={file}, focus={focus}")
        
        handle_optimize(
            file_path=file,
            focus=focus,
            language=language
        )
        
    except FileNotFoundError:
        console.print(f"[red]❌ Error: File not found: {file}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error in optimize command: {str(e)}[/red]")
        logger.exception("Optimize command failed")
        raise typer.Exit(1)


@app.command("version")
def version():
    """Show Rocket CLI version."""
    from Rocket import __version__
    console.print(f"[cyan]Rocket CLI v{__version__}[/cyan]")


@app.command("config")
def config(
    action: str = typer.Argument("show", help="Action: show, set, reset"),
    key: Optional[str] = typer.Option(None, "--key", "-k", help="Config key"),
    value: Optional[str] = typer.Option(None, "--value", "-v", help="Config value")
):
    """
    Manage Rocket CLI configuration.
    
    Examples:
        rocket config show
        rocket config set --key api_key --value your_key_here
        rocket config reset
    """
    try:
        from Rocket.CLI.commands import handle_config
        
        logger.info(f"⚙️  Config command: action={action}")
        
        handle_config(
            action=action,
            key=key,
            value=value
        )
        
    except Exception as e:
        console.print(f"[red]❌ Error in config command: {str(e)}[/red]")
        logger.exception("Config command failed")
        raise typer.Exit(1)


def main():
    """Main entry point for Rocket CLI."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Rocket CLI interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {str(e)}[/red]")
        logger.exception("Unexpected error in main")
        sys.exit(1)


if __name__ == "__main__":
    main()
            