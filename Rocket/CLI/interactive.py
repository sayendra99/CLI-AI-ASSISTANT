"""
Interactive Shell Mode for Rocket CLI
Premium user experience with session personalization and rich UI
"""

import asyncio
import sys
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from rich import box

from Rocket.CLI.commands import (
    handle_chat,
    handle_generate,
    handle_explain,
    handle_debug,
    get_provider_manager,
)
from Rocket.LLM.providers import GenerateOptions
from Rocket.Utils.Config import settings

console = Console()


class SessionManager:
    """Manages interactive session state and personalization."""
    
    def __init__(self, name: str = "Rocket"):
        self.name = name
        self.start_time = datetime.now()
        self.message_count = 0
        self.history: List[dict] = []
        
    def add_message(self, role: str, content: str):
        """Add message to history."""
        self.message_count += 1
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })
    
    def get_greeting(self) -> str:
        """Get personalized greeting based on time of day."""
        hour = datetime.now().hour
        if hour < 12:
            return f"Good morning! I'm {self.name}, ready to assist you! ☀️"
        elif hour < 18:
            return f"Good afternoon! I'm {self.name}, let's build something amazing! 🚀"
        else:
            return f"Good evening! I'm {self.name}, here to help you code! 🌙"


def display_welcome_banner(session_name: str):
    """Display welcome banner with giant colorful rocket ship."""
    from rich.text import Text
    from rich.console import Console
    
    console = Console()
    logo = Text()
    
    # Stars border
    logo.append("\n    ", style="")
    for color in ["red", "yellow", "green", "cyan", "blue", "magenta"]:
        logo.append("★", style=f"bold {color}")
    logo.append(" " * 58, style="")
    for color in ["magenta", "blue", "cyan", "green", "yellow", "red"]:
        logo.append("★", style=f"bold {color}")
    logo.append("\n\n", style="")
    
    # Giant Rocket Ship ASCII art
    rocket_lines = [
        ("                    ", [("╔═══╗", "bold bright_red on black")]),
        ("                    ", [("║", "bold bright_red on black"), ("███", "bold bright_yellow on black"), ("║", "bold bright_red on black")]),
        ("                   ", [("╔", "bold red on black"), ("═", "bold yellow on black"), ("╩", "bold bright_red on black"), ("═", "bold yellow on black"), ("╩", "bold bright_red on black"), ("═", "bold yellow on black"), ("╗", "bold red on black")]),
        ("                   ", [("║", "bold red on black"), ("█████", "bold bright_cyan on black"), ("║", "bold red on black"), ("   ", ""), ("╔═══════════════════════════════╗", "bold bright_magenta")]),
        ("                   ", [("║", "bold red on black"), ("█", "bold bright_cyan on black"), ("▓▓▓", "bold cyan on black"), ("█", "bold bright_cyan on black"), ("║", "bold red on black"), ("   ", ""), ("║  ", "bold bright_magenta"), ("R  O  C  K  E  T", "bold bright_cyan"), ("    ", ""), ("C  L  I", "bold bright_yellow"), ("  ║", "bold bright_magenta")]),
        ("                   ", [("║", "bold red on black"), ("█", "bold bright_cyan on black"), ("███", "bold bright_white on black"), ("█", "bold bright_cyan on black"), ("║", "bold red on black"), ("   ", ""), ("╚═══════════════════════════════╝", "bold bright_magenta")]),
        ("                   ", [("║", "bold bright_blue on black"), ("█████", "bold bright_white on black"), ("║", "bold bright_blue on black")]),
        ("                  ", [("╔", "bold blue on black"), ("═", "bold cyan on black"), ("╩", "bold bright_blue on black"), ("═══", "bold white on black"), ("╩", "bold bright_blue on black"), ("═", "bold cyan on black"), ("╗", "bold blue on black")]),
        ("                  ", [("║", "bold blue on black"), ("███████", "bold bright_white on black"), ("║", "bold blue on black")]),
        ("                  ", [("║", "bold blue on black"), ("█", "bold bright_white on black"), ("▓▓▓▓▓", "bold white on black"), ("█", "bold bright_white on black"), ("║", "bold blue on black")]),
        ("                  ", [("║", "bold blue on black"), ("███████", "bold bright_white on black"), ("║", "bold blue on black")]),
        ("                  ", [("╠", "bold bright_green on black"), ("═══════", "bold green on black"), ("╣", "bold bright_green on black")]),
        ("                  ", [("║", "bold green on black"), ("███████", "bold bright_green on black"), ("║", "bold green on black")]),
        ("                  ", [("║", "bold green on black"), ("███████", "bold bright_green on black"), ("║", "bold green on black")]),
        ("                  ", [("╠", "bold bright_yellow on black"), ("═══════", "bold yellow on black"), ("╣", "bold bright_yellow on black")]),
        ("                  ", [("║", "bold yellow on black"), ("███████", "bold bright_yellow on black"), ("║", "bold yellow on black")]),
        ("                  ", [("║", "bold yellow on black"), ("███████", "bold bright_yellow on black"), ("║", "bold yellow on black")]),
        ("                  ", [("╚", "bold bright_yellow on black"), ("═══════", "bold yellow on black"), ("╝", "bold bright_yellow on black")]),
        ("                 ", [("╔", "bold red on black"), ("═", "bold bright_red on black"), ("╝", "bold bright_yellow on black"), ("     ", ""), ("╚", "bold bright_yellow on black"), ("═", "bold bright_red on black"), ("╗", "bold red on black")]),
        ("                ", [("╔", "bold bright_red on black"), ("╝", "bold bright_yellow on black"), ("         ", ""), ("╚", "bold bright_yellow on black"), ("╗", "bold bright_red on black")]),
        ("               ", [("║", "bold bright_red on black"), ("🔥", ""), ("         ", ""), ("🔥", ""), ("║", "bold bright_red on black")]),
        ("               ", [("╚", "bold bright_yellow on black"), ("═══════════", "bold bright_red on black"), ("╝", "bold bright_yellow on black")]),
    ]
    
    for prefix, parts in rocket_lines:
        logo.append(prefix, style="")
        for text, style in parts:
            logo.append(text, style=style)
        logo.append("\n", style="")
    
    # Subtitle
    logo.append("\n              🚀 ", style="")
    logo.append("AI-Powered Coding Assistant", style="bold bright_cyan")
    logo.append(" 🚀\n", style="")
    logo.append("                ", style="")
    logo.append("Your Personal Development Partner", style="cyan italic")
    logo.append("\n\n    ", style="")
    
    # Bottom stars
    for color in ["red", "yellow", "green", "cyan", "blue", "magenta"]:
        logo.append("★", style=f"bold {color}")
    logo.append(" " * 58, style="")
    for color in ["magenta", "blue", "cyan", "green", "yellow", "red"]:
        logo.append("★", style=f"bold {color}")
    logo.append("\n", style="")
    
    console.print(logo)
    console.print()
    
    # Session info
    session = SessionManager(name=session_name)
    greeting = Text()
    greeting.append("\n              ╭", style="bold cyan")
    greeting.append("─" * 48, style="bold magenta")
    greeting.append("╮\n", style="bold cyan")
    greeting.append("              │  🎉 ", style="bold cyan")
    greeting.append(session.get_greeting(), style="bold green")
    greeting.append("  │\n", style="bold magenta")
    greeting.append("              │  💼 Session: ", style="bold magenta")
    greeting.append(session_name, style="bold bright_cyan on black")
    greeting.append("  │  ⚡ ", style="")
    greeting.append("Ollama", style="bold bright_yellow on black")
    greeting.append("  │  🎯 ", style="")
    greeting.append("Ready!", style="bold bright_green on black")
    greeting.append("  │\n", style="bold yellow")
    greeting.append("              │  💡 Type ", style="bold yellow")
    greeting.append("help", style="bold bright_magenta on black")
    greeting.append(" or just chat! ✨🌈           │\n", style="white")
    greeting.append("              ╰", style="bold green")
    greeting.append("─" * 48, style="bold blue")
    greeting.append("╯\n", style="bold green")
    
    console.print(greeting)
    console.print()
    
    return session


def display_help():
    """Display command help with beautiful formatting."""
    
    help_table = Table(
        title="🎯 Rocket CLI Commands",
        show_header=True,
        header_style="bold magenta",
        border_style="cyan",
        box=box.ROUNDED
    )
    
    help_table.add_column("Command", style="cyan bold", no_wrap=True)
    help_table.add_column("Description", style="white")
    help_table.add_column("Example", style="dim")
    
    commands = [
        ("Just type!", "Chat naturally with AI", "What is FastAPI?"),
        ("/generate", "Generate code snippets", "/generate REST API with auth"),
        ("/explain", "Explain code concepts", "/explain decorators in Python"),
        ("/debug", "Debug errors & issues", "/debug TypeError in my code"),
        ("/code", "Show code with syntax highlighting", "/code myapp.py"),
        ("/clear", "Clear screen", "/clear"),
        ("/history", "Show conversation history", "/history"),
        ("/rename", "Rename session", "/rename MySession"),
        ("/exit", "Exit interactive mode", "/exit or Ctrl+C"),
        ("help", "Show this help", "help"),
    ]
    
    for cmd, desc, example in commands:
        help_table.add_row(cmd, desc, example)
    
    console.print(help_table)
    console.print()


def display_code_block(code: str, language: str = "python"):
    """Display code with syntax highlighting."""
    syntax = Syntax(
        code,
        language,
        theme="monokai",
        line_numbers=True,
        word_wrap=True,
        background_color="default"
    )
    console.print(Panel(
        syntax,
        title=f"[bold cyan]{language.upper()} Code[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED
    ))


def format_ai_response(text: str, session_name: str = "Rocket"):
    """Format AI response with rich styling."""
    
    # Create header
    header = Text()
    header.append(f"💬 {session_name}", style="bold cyan")
    header.append(" says:", style="dim")
    
    console.print()
    console.print(header)
    console.print()
    
    # Format response as markdown
    md = Markdown(text)
    console.print(Panel(
        md,
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2)
    ))
    console.print()


async def handle_interactive_command(command: str, session: SessionManager) -> bool:
    """
    Handle special interactive commands.
    
    Returns:
        True to continue, False to exit
    """
    command = command.strip().lower()
    
    if command in ["/exit", "/quit", "exit", "quit"]:
        console.print(f"\n[bold green]👋 Goodbye! {session.name} signing off![/bold green]")
        console.print(f"[dim]Messages this session: {session.message_count}[/dim]\n")
        return False
    
    elif command in ["/clear", "clear"]:
        console.clear()
        display_welcome_banner(session.name)
        return True
    
    elif command in ["/help", "help", "?"]:
        display_help()
        return True
    
    elif command.startswith("/rename "):
        new_name = command[8:].strip()
        if new_name:
            old_name = session.name
            session.name = new_name
            console.print(f"\n[green]✓ Session renamed from '{old_name}' to '{new_name}'![/green]\n")
        return True
    
    elif command in ["/history", "history"]:
        if not session.history:
            console.print("\n[yellow]No conversation history yet. Start chatting![/yellow]\n")
        else:
            history_table = Table(
                title="📜 Conversation History",
                show_header=True,
                header_style="bold cyan",
                border_style="cyan"
            )
            history_table.add_column("#", style="dim", width=4)
            history_table.add_column("Time", style="cyan", width=12)
            history_table.add_column("Role", style="yellow", width=10)
            history_table.add_column("Message", style="white")
            
            for i, msg in enumerate(session.history[-10:], 1):  # Last 10 messages
                time_str = msg["timestamp"].strftime("%H:%M:%S")
                content = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
                history_table.add_row(str(i), time_str, msg["role"], content)
            
            console.print()
            console.print(history_table)
            console.print()
        return True
    
    elif command.startswith("/generate "):
        prompt = command[10:].strip()
        if prompt:
            with console.status(f"[bold cyan]{session.name} is generating code...", spinner="dots"):
                await handle_generate(
                    description=prompt,
                    language="python",
                    stream=False,
                    output_file=None
                )
        return True
    
    elif command.startswith("/code "):
        filepath = command[6:].strip()
        try:
            path = Path(filepath)
            if path.exists():
                code = path.read_text()
                language = path.suffix[1:] if path.suffix else "python"
                display_code_block(code, language)
            else:
                console.print(f"[red]File not found: {filepath}[/red]")
        except Exception as e:
            console.print(f"[red]Error reading file: {e}[/red]")
        return True
    
    return True


async def run_interactive_shell(session_name: Optional[str] = None):
    """
    Run interactive shell mode with rich UI.
    
    This is the main entry point for the enhanced user experience.
    """
    
    # Prompt for session name if not provided
    if not session_name:
        console.print("\n[bold cyan]🚀 Welcome to Rocket CLI![/bold cyan]\n")
        use_custom = Confirm.ask(
            "[yellow]Would you like to personalize your session with a custom name?[/yellow]",
            default=False
        )
        
        if use_custom:
            session_name = Prompt.ask(
                "[cyan]Enter your session name[/cyan]",
                default="Rocket"
            )
        else:
            session_name = "Rocket"
    
    # Display welcome
    console.clear()
    session = display_welcome_banner(session_name)
    
    # Get provider manager (initialize once)
    try:
        manager = await get_provider_manager()
    except Exception as e:
        console.print(f"[red]Failed to initialize AI provider: {e}[/red]")
        return
    
    # Main interaction loop
    while True:
        try:
            # Get user input with custom prompt
            prompt_text = Text()
            prompt_text.append("┌─[", style="dim")
            prompt_text.append("You", style="bold green")
            prompt_text.append("]", style="dim")
            console.print(prompt_text)
            
            user_input = Prompt.ask("[dim]└─>[/dim]", default="").strip()
            
            if not user_input:
                continue
            
            # Handle special commands
            if user_input.startswith("/") or user_input in ["help", "exit", "quit", "clear"]:
                should_continue = await handle_interactive_command(user_input, session)
                if not should_continue:
                    break
                continue
            
            # Add to history
            session.add_message("user", user_input)
            
            # Show thinking indicator
            console.print()
            with Live(
                Spinner("dots", text=f"[cyan]{session.name} is thinking...[/cyan]"),
                console=console,
                transient=True
            ):
                # Generate response
                system_instruction = (
                    f"You are {session.name}, an enthusiastic and helpful AI coding assistant. "
                    "Provide clear, practical solutions with code examples. "
                    "Be friendly and encouraging. Use emojis occasionally. "
                    "Format code with proper markdown."
                )
                
                options = GenerateOptions(
                    prompt=user_input,
                    system_instruction=system_instruction,
                    temperature=0.7,
                    max_tokens=2048,
                    stream=False
                )
                
                response = await manager.generate(options)
            
            # Add response to history
            session.add_message("assistant", response.text)
            
            # Display response
            format_ai_response(response.text, session.name)
            
        except KeyboardInterrupt:
            console.print(f"\n\n[yellow]Session interrupted. Type '/exit' to quit or continue chatting.[/yellow]\n")
            continue
        except EOFError:
            console.print(f"\n[bold green]👋 Goodbye! {session.name} signing off![/bold green]\n")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]\n")
            console.print("[dim]Type 'help' for assistance or '/exit' to quit.[/dim]\n")
    
    # Cleanup
    from Rocket.CLI.commands import _cleanup_manager
    await _cleanup_manager(manager)


def start_interactive_mode(session_name: Optional[str] = None):
    """Start interactive shell (sync wrapper)."""
    try:
        asyncio.run(run_interactive_shell(session_name))
    except KeyboardInterrupt:
        console.print("\n[bold green]👋 Goodbye![/bold green]\n")
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]\n")
        raise
