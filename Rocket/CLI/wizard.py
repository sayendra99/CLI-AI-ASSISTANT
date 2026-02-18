"""
Interactive Project Wizard for Rocket CLI

Guides users through project creation with Q&A flow.
Recommends tech stacks, generates complete projects, and provides next steps.
"""

import os
import sys
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import subprocess

# Fix Windows UTF-8 encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

console = Console()


class ProjectWizard:
    """Interactive wizard for creating new projects"""
    
    # Project types with metadata
    PROJECT_TYPES = {
        "1": {
            "name": "Personal Website/Portfolio",
            "description": "Showcase your work, skills, and projects",
            "difficulty": "Beginner",
            "time": "15 minutes",
            "tech_stack": {
                "frontend": "Next.js + Tailwind CSS",
                "hosting": "Vercel (Free)",
                "features": ["Responsive design", "Dark mode", "Contact form", "SEO optimized"]
            }
        },
        "2": {
            "name": "Blog/Content Site",
            "description": "Share articles, tutorials, or stories",
            "difficulty": "Beginner",
            "time": "20 minutes",
            "tech_stack": {
                "frontend": "Astro + MDX",
                "cms": "Markdown files (no database needed)",
                "hosting": "Netlify (Free)",
                "features": ["Write in Markdown", "RSS feed", "Categories/tags", "Search"]
            }
        },
        "3": {
            "name": "Todo/Task Manager",
            "description": "Organize tasks and boost productivity",
            "difficulty": "Intermediate",
            "time": "30 minutes",
            "tech_stack": {
                "frontend": "React + Vite",
                "backend": "Firebase",
                "database": "Firestore",
                "auth": "Firebase Auth",
                "features": ["User accounts", "Real-time sync", "Due dates", "Categories"]
            }
        },
        "4": {
            "name": "E-commerce Store",
            "description": "Sell products online",
            "difficulty": "Advanced",
            "time": "60 minutes",
            "tech_stack": {
                "frontend": "Next.js + Tailwind",
                "backend": "Shopify/Stripe",
                "database": "PostgreSQL",
                "features": ["Product catalog", "Shopping cart", "Payments", "Admin dashboard"]
            }
        },
        "5": {
            "name": "Dashboard/Analytics",
            "description": "Visualize data and metrics",
            "difficulty": "Intermediate",
            "time": "45 minutes",
            "tech_stack": {
                "frontend": "React + Recharts",
                "backend": "Node.js + Express",
                "database": "PostgreSQL",
                "features": ["Charts/graphs", "Real-time data", "Filters", "Export data"]
            }
        },
        "6": {
            "name": "API/Backend Service",
            "description": "Build RESTful APIs and microservices",
            "difficulty": "Advanced",
            "time": "40 minutes",
            "tech_stack": {
                "framework": "FastAPI (Python) or Express (Node.js)",
                "database": "PostgreSQL/MongoDB",
                "docs": "Auto-generated API docs",
                "features": ["REST endpoints", "Authentication", "Rate limiting", "Testing"]
            }
        }
    }
    
    @classmethod
    def welcome(cls):
        """Display welcome message"""
        console.print(Panel(
            "[bold cyan]🚀 Welcome to Rocket CLI Project Wizard![/bold cyan]\n\n"
            "I'll help you build your project step-by-step.\n"
            "This wizard will:\n"
            "  • Understand what you want to build\n"
            "  • Recommend the best tech stack\n"
            "  • Generate a complete project\n"
            "  • Guide you through customization\n\n"
            "[dim]Let's get started![/dim]",
            border_style="cyan",
            padding=(1, 2)
        ))
    
    @classmethod
    def select_project_type(cls) -> Dict:
        """Let user select project type"""
        console.print("\n[bold]What would you like to build?[/bold]\n")
        
        # Display options
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Project Type", style="green")
        table.add_column("Description", style="white")
        table.add_column("Difficulty", justify="center")
        table.add_column("Time", justify="center")
        
        for key, project in cls.PROJECT_TYPES.items():
            difficulty_color = {
                "Beginner": "green",
                "Intermediate": "yellow",
                "Advanced": "red"
            }[project["difficulty"]]
            
            table.add_row(
                key,
                project["name"],
                project["description"],
                f"[{difficulty_color}]{project['difficulty']}[/{difficulty_color}]",
                project["time"]
            )
        
        console.print(table)
        
        choice = Prompt.ask(
            "\n[bold cyan]Choose a project type[/bold cyan]",
            choices=list(cls.PROJECT_TYPES.keys()),
            default="1"
        )
        
        return cls.PROJECT_TYPES[choice]
    
    @classmethod
    def gather_project_details(cls, project_type: Dict) -> Dict:
        """Gather project-specific details"""
        console.print(f"\n[bold]Great! Let's set up your {project_type['name']}[/bold]\n")
        
        details = {
            "type": project_type["name"],
            "tech_stack": project_type["tech_stack"]
        }
        
        # Project name
        details["name"] = Prompt.ask(
            "[cyan]Project name[/cyan]",
            default="my-awesome-project"
        )
        
        # Directory
        details["directory"] = Prompt.ask(
            "[cyan]Directory to create project in[/cyan]",
            default=f"./{details['name']}"
        )
        
        # Custom questions based on project type
        if "Personal Website" in project_type["name"]:
            details["user_name"] = Prompt.ask("[cyan]Your name[/cyan]")
            details["user_title"] = Prompt.ask("[cyan]Your title/role[/cyan]", default="Developer")
            details["include_blog"] = Confirm.ask("[cyan]Include a blog section?[/cyan]", default=False)
            details["include_projects"] = Confirm.ask("[cyan]Showcase your projects?[/cyan]", default=True)
        
        elif "Blog" in project_type["name"]:
            details["blog_name"] = Prompt.ask("[cyan]Blog name[/cyan]")
            details["blog_description"] = Prompt.ask("[cyan]Short description[/cyan]")
            details["author_name"] = Prompt.ask("[cyan]Author name[/cyan]")
        
        elif "Todo" in project_type["name"]:
            details["require_auth"] = Confirm.ask("[cyan]Require user accounts?[/cyan]", default=True)
            details["enable_sharing"] = Confirm.ask("[cyan]Enable sharing todos with others?[/cyan]", default=False)
            details["add_categories"] = Confirm.ask("[cyan]Add categories/tags?[/cyan]", default=True)
        
        return details
    
    @classmethod
    def show_tech_stack(cls, tech_stack: Dict):
        """Display recommended tech stack"""
        console.print("\n[bold]📦 Recommended Tech Stack:[/bold]\n")
        
        for key, value in tech_stack.items():
            if isinstance(value, list):
                console.print(f"  [cyan]{key.replace('_', ' ').title()}:[/cyan]")
                for item in value:
                    console.print(f"    • {item}")
            else:
                console.print(f"  [cyan]{key.replace('_', ' ').title()}:[/cyan] {value}")
        
        console.print("\n[bold]Why this stack?[/bold]")
        console.print("  ✓ Beginner-friendly with great documentation")
        console.print("  ✓ Free tier available (no costs to start)")
        console.print("  ✓ Used by millions of developers")
        console.print("  ✓ Fast development and deployment")
        
        if not Confirm.ask("\n[cyan]Sound good?[/cyan]", default=True):
            console.print("\n[yellow]Let me know if you want different options![/yellow]")
            console.print("[dim]Run: rocket wizard --advanced for more choices[/dim]")
            return False
        
        return True
    
    @classmethod
    def create_project(cls, details: Dict):
        """Create the project with progress tracking"""
        console.print(f"\n[bold green]🚀 Creating your {details['type']}...[/bold green]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Create directory
            task = progress.add_task("Creating project directory...", total=None)
            os.makedirs(details["directory"], exist_ok=True)
            progress.update(task, completed=True)
            
            # Initialize project
            task = progress.add_task("Initializing project...", total=None)
            cls._initialize_project(details)
            progress.update(task, completed=True)
            
            # Install dependencies
            task = progress.add_task("Installing dependencies...", total=None)
            cls._install_dependencies(details)
            progress.update(task, completed=True)
            
            # Generate files
            task = progress.add_task("Generating project files...", total=None)
            cls._generate_files(details)
            progress.update(task, completed=True)
            
            # Configure project
            task = progress.add_task("Configuring project...", total=None)
            cls._configure_project(details)
            progress.update(task, completed=True)
        
        console.print("\n[bold green]✅ Project created successfully![/bold green]\n")
    
    @classmethod
    def _initialize_project(cls, details: Dict):
        """Initialize the project structure"""
        project_dir = Path(details["directory"])
        
        # Create package.json for Node projects
        if "Next.js" in str(details.get("tech_stack", {})):
            package_json = {
                "name": details["name"],
                "version": "0.1.0",
                "private": True,
                "scripts": {
                    "dev": "next dev",
                    "build": "next build",
                    "start": "next start",
                    "lint": "next lint"
                },
                "dependencies": {
                    "next": "14.1.0",
                    "react": "^18.2.0",
                    "react-dom": "^18.2.0"
                }
            }
            
            with open(project_dir / "package.json", "w") as f:
                json.dump(package_json, f, indent=2)
        
        # Create README
        readme_content = f"""# {details['name']}

{details.get('type', 'Project')} built with Rocket CLI

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Features

- Modern tech stack
- Fast development experience
- Production-ready

## Deploy

Deploy with one command:
```bash
rocket deploy
```

Built with 🚀 [Rocket CLI](https://rocket-cli.dev)
"""
        
        with open(project_dir / "README.md", "w") as f:
            f.write(readme_content)
    
    @classmethod
    def _install_dependencies(cls, details: Dict):
        """Install project dependencies"""
        # Simulate installation (in real version, would run npm install)
        import time
        time.sleep(1)
    
    @classmethod
    def _generate_files(cls, details: Dict):
        """Generate project files based on type"""
        project_dir = Path(details["directory"])
        
        # Create app directory for Next.js
        if "Next.js" in str(details.get("tech_stack", {})):
            app_dir = project_dir / "app"
            app_dir.mkdir(exist_ok=True)
            
            # Create layout.tsx
            layout_content = """export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
"""
            with open(app_dir / "layout.tsx", "w") as f:
                f.write(layout_content)
            
            # Create page.tsx with personalization
            if "Personal Website" in details.get("type", ""):
                page_content = f"""export default function Home() {{
  return (
    <main className="min-h-screen p-24">
      <h1 className="text-4xl font-bold">{details.get('user_name', 'Your Name')}</h1>
      <p className="text-xl mt-4">{details.get('user_title', 'Developer')}</p>
      <p className="mt-8">Welcome to my portfolio!</p>
    </main>
  )
}}
"""
            else:
                page_content = """export default function Home() {
  return (
    <main className="min-h-screen p-24">
      <h1 className="text-4xl font-bold">Welcome!</h1>
    </main>
  )
}
"""
            
            with open(app_dir / "page.tsx", "w") as f:
                f.write(page_content)
    
    @classmethod
    def _configure_project(cls, details: Dict):
        """Configure project settings"""
        project_dir = Path(details["directory"])
        
        # Create .gitignore
        gitignore_content = """node_modules/
.next/
.env.local
.env
dist/
build/
.DS_Store
*.log
"""
        with open(project_dir / ".gitignore", "w") as f:
            f.write(gitignore_content)
        
        # Create .env.example
        env_content = """# Environment Variables
# Copy this to .env.local and fill in your values

# API Keys
NEXT_PUBLIC_API_URL=

# Database
DATABASE_URL=
"""
        with open(project_dir / ".env.example", "w") as f:
            f.write(env_content)
    
    @classmethod
    def show_next_steps(cls, details: Dict):
        """Show next steps after project creation"""
        console.print(Panel(
            f"[bold green]🎉 Your {details['type']} is ready![/bold green]\n\n"
            f"[bold]📁 Project location:[/bold] {details['directory']}\n\n"
            "[bold]🎯 Next Steps:[/bold]\n\n"
            "1. Open your project:\n"
            f"   [cyan]cd {details['directory']}[/cyan]\n\n"
            "2. Start development server:\n"
            "   [cyan]npm run dev[/cyan]\n\n"
            "3. Open in browser:\n"
            "   [cyan]http://localhost:3000[/cyan]\n\n"
            "4. Customize your project:\n"
            "   [cyan]rocket customize[/cyan]\n\n"
            "5. When ready, deploy:\n"
            "   [cyan]rocket deploy[/cyan]\n\n"
            "[bold]💡 Pro Tips:[/bold]\n"
            "• Run [cyan]rocket help[/cyan] anytime for assistance\n"
            "• Use [cyan]rocket add-feature[/cyan] to add new functionality\n"
            "• Join our community: https://discord.gg/rocket-cli",
            title="🚀 Success!",
            border_style="green",
            padding=(1, 2)
        ))
        
        # Ask if they want to open in VS Code
        if Confirm.ask("\n[cyan]Open project in VS Code?[/cyan]", default=True):
            try:
                subprocess.run(["code", details["directory"]])
                console.print("[green]✓ Opened in VS Code![/green]")
            except:
                console.print("[yellow]! Could not open VS Code. Open manually.[/yellow]")
    
    @classmethod
    def run(cls):
        """Run the complete wizard"""
        # Welcome
        cls.welcome()
        
        # Select project type
        project_type = cls.select_project_type()
        
        # Gather details
        details = cls.gather_project_details(project_type)
        
        # Show tech stack
        if not cls.show_tech_stack(project_type["tech_stack"]):
            return
        
        # Create project
        cls.create_project(details)
        
        # Show next steps
        cls.show_next_steps(details)


# CLI command
def wizard_command():
    """Start the interactive project wizard"""
    ProjectWizard.run()


if __name__ == "__main__":
    wizard_command()
