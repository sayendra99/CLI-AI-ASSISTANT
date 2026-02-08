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


def display_welcome_banner(session_name: str, theme: str = "ocean-foam"):
    """Display welcome banner with clean, professional branding."""
    from rich.text import Text
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    
    # Theme gradients (hex colors)
    THEMES = {
        "synthwave": ("#2193b0", "#6dd5ed"),        # Cyberpunk blue
        "electric-purple": ("#cc2b5e", "#753a88"),  # Purple energy
        "neon-aqua": ("#26C0FC", "#61FFFA"),        # Bright cyan
        "cyber-rose": ("#ED1E79", "#662D8C"),       # Pink purple
        "toxic-lime": ("#56ab2f", "#a8e063"),       # Green glow
        "hyper-blue": ("#283AB8", "#16F1FA"),       # Deep to bright blue
        "blood-moon": ("#ff512f", "#dd2476"),       # Red orange
        "cosmic-ray": ("#8900ff", "#00ecff"),       # Purple cyan
        "slate-mist": ("#bdc3c7", "#2c3e50"),       # Professional gray
        "nordic-ice": ("#93A5CF", "#E4EfE9"),       # Cool blue white
        "deep-sea": ("#09203F", "#537895"),         # Dark blue
        "muted-forest": ("#436553", "#A0B4A9"),     # Green gray
        "soft-steel": ("#868F96", "#596164"),       # Gray tones
        "pale-wood": ("#eacda3", "#d6ae7b"),        # Warm beige
        "arctic-frost": ("#000428", "#004e92"),     # Dark to blue
        "sunburst": ("#ff9966", "#ff5e62"),         # Orange red
        "morning-sky": ("#ff5f6d", "#ffc371"),      # Pink orange
        "mango-salsa": ("#FCCF31", "#F55555"),      # Yellow red
        "ocean-foam": ("#2E3192", "#1BFFFF"),       # Blue cyan
        "spring-bud": ("#009245", "#FCEE21"),       # Green yellow
        "emerald-shore": ("#43cea2", "#185a9d"),    # Teal blue
        "lush-meadow": ("#06beb6", "#48b1bf"),      # Teal gradient
        "peach-glow": ("#ed4264", "#ffedbc"),       # Coral cream
        "fire-watch": ("#f45c43", "#eb3349"),       # Red flames
        "rocket-launch": ("#00ff00", "#ffff00", "#ff0000"),  # Green Yellow Red
    }
    
    # Get theme colors
    colors = THEMES.get(theme, THEMES["ocean-foam"])
    
    # Convert hex to RGB and create gradient
    def hex_to_rgb(h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    
    def rgb_style(rgb):
        return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"
    
    # Generate 6 color stops for gradient
    if len(colors) == 2:
        start, end = hex_to_rgb(colors[0]), hex_to_rgb(colors[1])
        gradient = []
        for i in range(6):
            factor = i / 5
            r = int(start[0] + (end[0] - start[0]) * factor)
            g = int(start[1] + (end[1] - start[1]) * factor)
            b = int(start[2] + (end[2] - start[2]) * factor)
            gradient.append((r, g, b))
    else:  # 3 colors
        start, mid, end = hex_to_rgb(colors[0]), hex_to_rgb(colors[1]), hex_to_rgb(colors[2])
        gradient = []
        for i in range(3):
            factor = i / 2
            r = int(start[0] + (mid[0] - start[0]) * factor)
            g = int(start[1] + (mid[1] - start[1]) * factor)
            b = int(start[2] + (mid[2] - start[2]) * factor)
            gradient.append((r, g, b))
        for i in range(3):
            factor = i / 2
            r = int(mid[0] + (end[0] - mid[0]) * factor)
            g = int(mid[1] + (end[1] - mid[1]) * factor)
            b = int(mid[2] + (end[2] - mid[2]) * factor)
            gradient.append((r, g, b))
    
    # Clean, modern logo design with side-by-side panels
    logo = Text()
    logo.append("\n")
    
    # Rocket emoji at top centered
    logo.append("                                  ", style="")
    logo.append("🚀", style="")
    logo.append("\n\n", style="")
    
    # Line 1: Top borders
    logo.append("    ╔", style=rgb_style(gradient[0]))
    logo.append("═" * 68, style=rgb_style(gradient[1]))
    logo.append("╗", style=rgb_style(gradient[2]))
    logo.append("  ", style="")
    logo.append("★", style=f"bold {rgb_style(gradient[0])}")
    logo.append("═" * 32, style=rgb_style(gradient[2]))
    logo.append("★\n", style=f"bold {rgb_style(gradient[5])}")
    
    # Line 2: Empty + Title
    logo.append("    ║", style=rgb_style(gradient[0]))
    logo.append("                                                                    ", style="")
    logo.append("║", style=rgb_style(gradient[0]))
    logo.append("  ", style="")
    logo.append("★  ", style=f"bold {rgb_style(gradient[0])}")
    logo.append("🚀 FREE & OPEN SOURCE", style=f"bold bright_green")
    logo.append("      ★\n", style=f"bold {rgb_style(gradient[5])}")
    
    # Line 3: ROCKET R + Multi-Language
    logo.append("    ║        ", style=rgb_style(gradient[0]))
    logo.append("██████╗  ", style=f"bold {rgb_style(gradient[0])} on black")
    logo.append("  ██████╗  ", style=f"bold {rgb_style(gradient[1])} on black")
    logo.append("  ██████╗ ", style=f"bold {rgb_style(gradient[2])} on black")
    logo.append(" ██╗  ██╗", style=f"bold {rgb_style(gradient[3])} on black")
    logo.append(" ███████╗", style=f"bold {rgb_style(gradient[4])} on black")
    logo.append(" ████████╗", style=f"bold {rgb_style(gradient[5])} on black")
    logo.append("   ", style="")
    logo.append("║", style=rgb_style(gradient[1]))
    logo.append("  ", style="")
    logo.append("★  ", style=f"bold {rgb_style(gradient[1])}")
    logo.append("Communicate in ", style=f"{rgb_style(gradient[3])}")
    logo.append("ANY", style=f"bold bright_cyan")
    logo.append(" language ", style=f"{rgb_style(gradient[3])}")
    logo.append(" ★\n", style=f"bold {rgb_style(gradient[2])}")
    
    # Line 4: Second row + Zero Cost
    logo.append("    ║        ", style=rgb_style(gradient[1]))
    logo.append("██╔══██╗ ", style=f"bold {rgb_style(gradient[0])} on black")
    logo.append(" ██╔═══██╗", style=f"bold {rgb_style(gradient[1])} on black")
    logo.append(" ██╔════╝", style=f"bold {rgb_style(gradient[2])} on black")
    logo.append(" ██║ ██╔╝", style=f"bold {rgb_style(gradient[3])} on black")
    logo.append(" ██╔════╝", style=f"bold {rgb_style(gradient[4])} on black")
    logo.append(" ╚══██╔══╝", style=f"bold {rgb_style(gradient[5])} on black")
    logo.append("   ", style="")
    logo.append("║", style=rgb_style(gradient[2]))
    logo.append("  ", style="")
    logo.append("★  ", style=f"bold {rgb_style(gradient[2])}")
    logo.append("100% ", style=f"bold bright_green")
    logo.append("Zero Cost Forever", style=f"{rgb_style(gradient[4])}")
    logo.append("      ★\n", style=f"bold {rgb_style(gradient[3])}")
    
    # Line 5: Third row + Local AI
    logo.append("    ║        ", style=rgb_style(gradient[2]))
    logo.append("██████╔╝ ", style=f"bold {rgb_style(gradient[0])} on black")
    logo.append(" ██║   ██║", style=f"bold {rgb_style(gradient[1])} on black")
    logo.append(" ██║     ", style=f"bold {rgb_style(gradient[2])} on black")
    logo.append(" █████╔╝ ", style=f"bold {rgb_style(gradient[3])} on black")
    logo.append(" █████╗  ", style=f"bold {rgb_style(gradient[4])} on black")
    logo.append("    ██║   ", style=f"bold {rgb_style(gradient[5])} on black")
    logo.append("   ", style="")
    logo.append("║", style=rgb_style(gradient[3]))
    logo.append("  ", style="")
    logo.append("★  ", style=f"bold {rgb_style(gradient[3])}")
    logo.append("🔒 ", style="")
    logo.append("Local AI • No API Keys", style=f"{rgb_style(gradient[5])}")
    logo.append("     ★\n", style=f"bold {rgb_style(gradient[4])}")
    
    # Line 6: Fourth row + Privacy
    logo.append("    ║        ", style=rgb_style(gradient[3]))
    logo.append("██╔══██╗ ", style=f"bold {rgb_style(gradient[0])} on black")
    logo.append(" ██║   ██║", style=f"bold {rgb_style(gradient[2])} on black")
    logo.append(" ██║     ", style=f"bold {rgb_style(gradient[2])} on black")
    logo.append(" ██╔═██╗ ", style=f"bold {rgb_style(gradient[3])} on black")
    logo.append(" ██╔══╝  ", style=f"bold {rgb_style(gradient[4])} on black")
    logo.append("    ██║   ", style=f"bold {rgb_style(gradient[5])} on black")
    logo.append("   ", style="")
    logo.append("║", style=rgb_style(gradient[4]))
    logo.append("  ", style="")
    logo.append("★  ", style=f"bold {rgb_style(gradient[4])}")
    logo.append("Your data stays ", style=f"{rgb_style(gradient[4])}")
    logo.append("private", style=f"bold bright_green")
    logo.append("      ★\n", style=f"bold {rgb_style(gradient[5])}")
    
    # Line 7: Fifth row + Commands
    logo.append("    ║        ", style=rgb_style(gradient[4]))
    logo.append("██║  ██║ ", style=f"bold {rgb_style(gradient[1])} on black")
    logo.append(" ╚██████╔╝", style=f"bold {rgb_style(gradient[2])} on black")
    logo.append(" ╚██████╗", style=f"bold {rgb_style(gradient[3])} on black")
    logo.append(" ██║  ██╗", style=f"bold {rgb_style(gradient[4])} on black")
    logo.append(" ███████╗", style=f"bold {rgb_style(gradient[5])} on black")
    logo.append("    ██║   ", style=f"bold {rgb_style(gradient[5])} on black")
    logo.append("   ", style="")
    logo.append("║", style=rgb_style(gradient[5]))
    logo.append("  ", style="")
    logo.append("★  ", style=f"bold {rgb_style(gradient[5])}")
    logo.append("⚡ Quick: ", style=f"{rgb_style(gradient[4])}")
    logo.append("/generate /explain", style=f"bold bright_cyan")
    logo.append("  ★\n", style=f"bold {rgb_style(gradient[0])}")
    
    # Line 8: Sixth row + More Commands
    logo.append("    ║        ", style=rgb_style(gradient[5]))
    logo.append("╚═╝  ╚═╝ ", style=f"bold {rgb_style(gradient[2])} on black")
    logo.append("  ╚═════╝ ", style=f"bold {rgb_style(gradient[3])} on black")
    logo.append("  ╚═════╝", style=f"bold {rgb_style(gradient[4])} on black")
    logo.append(" ╚═╝  ╚═╝", style=f"bold {rgb_style(gradient[5])} on black")
    logo.append(" ╚══════╝", style=f"bold {rgb_style(gradient[5])} on black")
    logo.append("    ╚═╝   ", style=f"bold {rgb_style(gradient[5])} on black")
    logo.append("   ", style="")
    logo.append("║", style=rgb_style(gradient[5]))
    logo.append("  ", style="")
    logo.append("★  ", style=f"bold {rgb_style(gradient[0])}")
    logo.append("         ", style="")
    logo.append("/debug help", style=f"bold bright_cyan")
    logo.append("          ★\n", style=f"bold {rgb_style(gradient[1])}")
    
    # Line 9: Empty + Status
    logo.append("    ║", style=rgb_style(gradient[5]))
    logo.append("                                                                    ", style="")
    logo.append("║", style=rgb_style(gradient[5]))
    logo.append("  ", style="")
    logo.append("★  ", style=f"bold {rgb_style(gradient[2])}")
    logo.append("Status: ", style=f"{rgb_style(gradient[3])}")
    logo.append("Ollama ", style=f"{rgb_style(gradient[4])}")
    logo.append("✅ Fast", style="bold bright_green")
    logo.append("      ★\n", style=f"bold {rgb_style(gradient[3])}")
    
    # Line 10: Subtitle + Usage
    logo.append("    ║              ", style=rgb_style(gradient[5]))
    logo.append("🚀  ", style="")
    logo.append("AI-Powered Coding Assistant", style=f"bold {rgb_style(gradient[3])}")
    logo.append("  🚀", style="")
    logo.append("              ║", style=rgb_style(gradient[5]))
    logo.append("  ", style="")
    logo.append("★  ", style=f"bold {rgb_style(gradient[4])}")
    logo.append("Messages Today: ", style=f"{rgb_style(gradient[4])}")
    logo.append("12", style=f"bold {rgb_style(gradient[5])}")
    logo.append("          ★\n", style=f"bold {rgb_style(gradient[4])}")
    
    # Line 11: Partner text + Bottom
    logo.append("    ║                  ", style=rgb_style(gradient[5]))
    logo.append("Your Personal Development Partner", style=f"{rgb_style(gradient[2])} italic")
    logo.append("                  ║", style=rgb_style(gradient[5]))
    logo.append("  ", style="")
    logo.append("★", style=f"bold {rgb_style(gradient[5])}")
    logo.append("═" * 32, style=rgb_style(gradient[3]))
    logo.append("★\n", style=f"bold {rgb_style(gradient[5])}")
    
    # Line 12: Empty
    logo.append("    ║", style=rgb_style(gradient[5]))
    logo.append("                                                                    ", style="")
    logo.append("║\n", style=rgb_style(gradient[5]))
    
    # Line 13: Bottom border
    logo.append("    ╚", style=rgb_style(gradient[5]))
    logo.append("═" * 68, style=rgb_style(gradient[3]))
    logo.append("╝\n", style=rgb_style(gradient[0]))
    
    console.print(logo)
    
    # Session info with gradient colors
    session = SessionManager(name=session_name)
    greeting = Text()
    greeting.append("\n    ╭", style=rgb_style(gradient[0]))
    greeting.append("═" * 56, style=rgb_style(gradient[2]))
    greeting.append("╮", style=rgb_style(gradient[4]))
    greeting.append("  ", style="")
    greeting.append("╭", style=rgb_style(gradient[0]))
    greeting.append("═" * 44, style=rgb_style(gradient[2]))
    greeting.append("╮\n", style=rgb_style(gradient[4]))
    
    # Line 1: Greeting + Quick Commands Header
    greeting.append("    │ 🎉 ", style=rgb_style(gradient[0]))
    greeting.append("Greetings from Sai! ", style=f"bold bright_cyan")
    greeting.append(session.get_greeting(), style=f"bold {rgb_style(gradient[3])}")
    greeting.append(" 🌙", style="")
    greeting.append("   │", style=rgb_style(gradient[2]))
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[0]))
    greeting.append("⚡ QUICK COMMANDS", style=f"bold {rgb_style(gradient[4])}")
    greeting.append("                 │\n", style=rgb_style(gradient[2]))
    
    # Line 2: Mission + Command 1
    greeting.append("    │ ", style=rgb_style(gradient[1]))
    greeting.append("💪 ", style="")
    greeting.append("\"Struggle for Existence - Code Your Future\"", style=f"bold italic {rgb_style(gradient[4])}")
    greeting.append("  │", style=rgb_style(gradient[2]))
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[1]))
    greeting.append("/generate", style=f"bold bright_cyan")
    greeting.append(" [desc] - Generate code    │\n", style=f"{rgb_style(gradient[3])}")
    
    # Line 3: Separator + Command 2
    greeting.append("    │ ", style=rgb_style(gradient[2]))
    greeting.append("─" * 54, style=rgb_style(gradient[3]))
    greeting.append(" │", style=rgb_style(gradient[4]))
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[2]))
    greeting.append("/explain", style=f"bold bright_cyan")
    greeting.append(" [code] - Explain concepts  │\n", style=f"{rgb_style(gradient[3])}")
    
    # Line 4: ROCKET description + Command 3
    greeting.append("    │ 🚀 ", style=rgb_style(gradient[3]))
    greeting.append("ROCKET", style=f"bold {rgb_style(gradient[4])}")
    greeting.append(" is your ", style=f"{rgb_style(gradient[3])}")
    greeting.append("FREE, open-source", style=f"bold bright_green")
    greeting.append(" AI companion │", style=f"{rgb_style(gradient[3])}")
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[3]))
    greeting.append("/debug", style=f"bold bright_cyan")
    greeting.append(" [error] - Fix issues       │\n", style=f"{rgb_style(gradient[3])}")
    
    # Line 5: Built for developers + Command 4
    greeting.append("    │   Built for developers who refuse to be limited.  │", style=f"{rgb_style(gradient[4])}")
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[4]))
    greeting.append("help", style=f"bold bright_cyan")
    greeting.append(" - Show all commands         │\n", style=f"{rgb_style(gradient[3])}")
    
    # Line 6: Empty + Separator
    greeting.append("    │                                                        │", style=rgb_style(gradient[5]))
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[5]))
    greeting.append("─" * 40, style=rgb_style(gradient[3]))
    greeting.append("  │\n", style=rgb_style(gradient[0]))
    
    # Line 7: Programming languages + Examples Header
    greeting.append("    │ 💻 ", style=rgb_style(gradient[0]))
    greeting.append("Program in ANY language:", style=f"bold {rgb_style(gradient[4])}")
    greeting.append(" Python, JS, Java  │", style=f"{rgb_style(gradient[3])}")
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[1]))
    greeting.append("📝 EXAMPLES", style=f"bold {rgb_style(gradient[4])}")
    greeting.append("                      │\n", style=rgb_style(gradient[2]))
    
    # Line 8: More languages + Example 1
    greeting.append("    │   C++, Go, Rust, PHP, Ruby, Swift, Kotlin & more!  │", style=f"{rgb_style(gradient[5])}")
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[2]))
    greeting.append("\"Create a REST API\"", style=f"italic {rgb_style(gradient[4])}")
    greeting.append("              │\n", style=f"{rgb_style(gradient[3])}")
    
    # Line 9: Empty + Example 2
    greeting.append("    │                                                        │", style=rgb_style(gradient[1]))
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[3]))
    greeting.append("\"Explain async/await\"", style=f"italic {rgb_style(gradient[4])}")
    greeting.append("            │\n", style=f"{rgb_style(gradient[3])}")
    
    # Line 10: Speak your language + Example 3
    greeting.append("    │ 🌍 ", style=rgb_style(gradient[2]))
    greeting.append("Speak YOUR language:", style=f"bold {rgb_style(gradient[4])}")
    greeting.append(" English, Hindi,     │", style=f"{rgb_style(gradient[3])}")
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[4]))
    greeting.append("\"Debug my code error\"", style=f"italic {rgb_style(gradient[4])}")
    greeting.append("           │\n", style=f"{rgb_style(gradient[3])}")
    
    # Line 11: More languages + Native language note
    greeting.append("    │   Spanish, French, German, Chinese, Arabic & 50+!  │", style=f"{rgb_style(gradient[5])}")
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[5]))
    greeting.append("या हिंदी में बात करें! ", style=f"italic {rgb_style(gradient[4])}")
    greeting.append("       │\n", style=f"{rgb_style(gradient[3])}")
    
    # Line 12: Empty + Separator
    greeting.append("    │                                                        │", style=rgb_style(gradient[3]))
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[0]))
    greeting.append("─" * 40, style=rgb_style(gradient[3]))
    greeting.append("  │\n", style=rgb_style(gradient[1]))
    
    # Line 13: Core Values Header + AI Status
    greeting.append("    │ ✨ ", style=rgb_style(gradient[4]))
    greeting.append("Core Values:", style=f"bold {rgb_style(gradient[4])}")
    greeting.append("                                  │", style=f"{rgb_style(gradient[1])}")
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[1]))
    greeting.append("🤖 AI: ", style=f"{rgb_style(gradient[3])}")
    greeting.append("Ollama", style=f"bold bright_green")
    greeting.append(" ", style="")
    greeting.append("✅ Ready", style=f"bold bright_green")
    greeting.append("        │\n", style=f"{rgb_style(gradient[2])}")
    
    # Line 14: Value 1 + Session info
    greeting.append("    │   • ", style=rgb_style(gradient[5]))
    greeting.append("100% Free Forever", style=f"bold bright_green")
    greeting.append(" - No costs, no limits   │", style=f"{rgb_style(gradient[3])}")
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[2]))
    greeting.append("💼 Session: ", style=f"{rgb_style(gradient[3])}")
    greeting.append(session_name, style=f"bold bright_cyan")
    greeting.append("              │\n", style=f"{rgb_style(gradient[3])}")
    
    # Line 15: Value 2 + Messages count
    greeting.append("    │   • ", style=rgb_style(gradient[0]))
    greeting.append("Your Privacy Matters", style=f"bold bright_cyan")
    greeting.append(" - Runs locally       │", style=f"{rgb_style(gradient[4])}")
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[3]))
    greeting.append("📊 Today: ", style=f"{rgb_style(gradient[4])}")
    greeting.append("12", style=f"bold {rgb_style(gradient[5])}")
    greeting.append(" msgs  ", style=f"{rgb_style(gradient[4])}")
    greeting.append("🔥 5d", style=f"bold {rgb_style(gradient[5])}")
    greeting.append("    │\n", style=f"{rgb_style(gradient[4])}")
    
    # Line 16: Value 3 + Response time
    greeting.append("    │   • ", style=rgb_style(gradient[1]))
    greeting.append("No API Keys Required", style=f"bold bright_green")
    greeting.append(" - No vendor lock-in  │", style=f"{rgb_style(gradient[5])}")
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[4]))
    greeting.append("⚡ Response: ", style=f"{rgb_style(gradient[4])}")
    greeting.append("~0.8s", style=f"bold bright_cyan")
    greeting.append("            │\n", style=f"{rgb_style(gradient[5])}")
    
    # Line 17: Value 4 + GitHub link
    greeting.append("    │   • ", style=rgb_style(gradient[2]))
    greeting.append("Built by Developers", style=f"bold bright_cyan")
    greeting.append(" - Community-driven   │", style=f"{rgb_style(gradient[3])}")
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[5]))
    greeting.append("⭐ Star us on GitHub!", style=f"bold {rgb_style(gradient[4])}")
    greeting.append("         │\n", style=f"{rgb_style(gradient[0])}")
    
    # Line 18: Bottom separator
    greeting.append("    │ ", style=rgb_style(gradient[3]))
    greeting.append("─" * 54, style=rgb_style(gradient[3]))
    greeting.append(" │", style=rgb_style(gradient[0]))
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[0]))
    greeting.append("─" * 40, style=rgb_style(gradient[3]))
    greeting.append("  │\n", style=rgb_style(gradient[1]))
    
    # Line 19: Quick start message
    greeting.append("    │ 💡 Type ", style=rgb_style(gradient[5]))
    greeting.append("help", style=f"bold bright_cyan")
    greeting.append(" or just start chatting naturally! ✨   │", style="white")
    greeting.append("  ", style="")
    greeting.append("│  ", style=rgb_style(gradient[1]))
    greeting.append("Type ", style=f"{rgb_style(gradient[3])}")
    greeting.append("/clear", style=f"bold bright_cyan")
    greeting.append(" to clear screen     │\n", style=f"{rgb_style(gradient[3])}")
    
    # Bottom borders
    greeting.append("    ╰", style=rgb_style(gradient[5]))
    greeting.append("═" * 56, style=rgb_style(gradient[3]))
    greeting.append("╯", style=rgb_style(gradient[0]))
    greeting.append("  ", style="")
    greeting.append("╰", style=rgb_style(gradient[1]))
    greeting.append("═" * 44, style=rgb_style(gradient[3]))
    greeting.append("╯\n", style=rgb_style(gradient[0]))
    
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
    session = display_welcome_banner(session_name, theme="ocean-foam")
    
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
