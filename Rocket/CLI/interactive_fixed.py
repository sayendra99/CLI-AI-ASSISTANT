# Copy the giant rocket ASCII art here
def display_welcome_banner_rocket(session_name: str):
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
    
    # Giant Rocket Ship
    lines = [
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
    
    for prefix, parts in lines:
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
    from datetime import datetime
    
    class QuickSession:
        def __init__(self, name):
            self.name = name
        def get_greeting(self):
            hour = datetime.now().hour
            if hour < 12:
                return f"Good morning! I'm {self.name}, ready to assist you! ☀️"
            elif hour < 18:
                return f"Good afternoon! I'm {self.name}, let's build something amazing! 🚀"
            else:
                return f"Good evening! I'm {self.name}, here to help you code! 🌙"
    
    session = QuickSession(session_name)
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
