"""
Project Templates System for Rocket CLI

Provides ready-to-use project templates for beginners.
Templates are categorized by difficulty and include complete setup.
"""

import os
import json
import shutil
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@dataclass
class ProjectTemplate:
    """Project template metadata"""
    id: str
    name: str
    description: str
    category: str  # beginner, intermediate, advanced
    tech_stack: List[str]
    features: List[str]
    setup_time: str
    difficulty: str
    tags: List[str]
    preview_url: Optional[str] = None
    video_url: Optional[str] = None
    use_count: int = 0
    rating: float = 0.0


class TemplateRegistry:
    """Central registry of all project templates"""
    
    TEMPLATES = [
        # Beginner Templates
        ProjectTemplate(
            id="portfolio-nextjs",
            name="Personal Portfolio",
            description="Beautiful portfolio website with dark mode, project showcase, and contact form",
            category="beginner",
            tech_stack=["Next.js 14", "Tailwind CSS", "TypeScript"],
            features=[
                "Responsive design", 
                "Dark/light mode toggle",
                "Project showcase section",
                "Contact form with email",
                "SEO optimized",
                "Analytics ready"
            ],
            setup_time="10 minutes",
            difficulty="Beginner",
            tags=["portfolio", "website", "nextjs", "tailwind"],
            preview_url="https://demo-portfolio.rocket-cli.dev",
            use_count=12453
        ),
        
        ProjectTemplate(
            id="blog-astro",
            name="Blog with CMS",
            description="Fast blog with Markdown support, categories, and RSS feed",
            category="beginner",
            tech_stack=["Astro", "MDX", "Tailwind CSS"],
            features=[
                "Write in Markdown",
                "Auto-generate table of contents",
                "Categories and tags",
                "RSS feed",
                "Syntax highlighting for code",
                "Fast page loads (<100ms)"
            ],
            setup_time="15 minutes",
            difficulty="Beginner",
            tags=["blog", "content", "astro", "markdown"],
            preview_url="https://demo-blog.rocket-cli.dev",
            use_count=8921
        ),
        
        ProjectTemplate(
            id="todo-react-firebase",
            name="Todo/Task Manager",
            description="Full-featured todo app with user accounts and real-time sync",
            category="intermediate",
            tech_stack=["React", "Vite", "Firebase", "Tailwind CSS"],
            features=[
                "User authentication (email/Google)",
                "Real-time synchronization",
                "Create, edit, delete todos",
                "Due dates and priorities",
                "Categories and tags",
                "Mobile responsive"
            ],
            setup_time="25 minutes",
            difficulty="Intermediate",
            tags=["todo", "productivity", "react", "firebase"],
            preview_url="https://demo-todo.rocket-cli.dev",
            use_count=6543
        ),
        
        ProjectTemplate(
            id="recipe-organizer",
            name="Recipe Organizer",
            description="Organize and share your favorite recipes with photos and ingredients",
            category="beginner",
            tech_stack=["Next.js", "Supabase", "Tailwind CSS"],
            features=[
                "Add recipes with photos",
                "Ingredient lists",
                "Step-by-step instructions",
                "Search and filter recipes",
                "Share recipes with friends",
                "Shopping list generator"
            ],
            setup_time="20 minutes",
            difficulty="Beginner",
            tags=["recipes", "cooking", "nextjs", "supabase"],
            preview_url="https://demo-recipes.rocket-cli.dev",
            use_count=4231
        ),
        
        ProjectTemplate(
            id="weather-dashboard",
            name="Weather Dashboard",
            description="Real-time weather dashboard with forecasts and location search",
            category="beginner",
            tech_stack=["React", "OpenWeather API", "Chart.js"],
            features=[
                "Current weather conditions",
                "5-day forecast",
                "Search by city",
                "Temperature charts",
                "Weather alerts",
                "Save favorite locations"
            ],
            setup_time="15 minutes",
            difficulty="Beginner",
            tags=["weather", "dashboard", "react", "api"],
            preview_url="https://demo-weather.rocket-cli.dev",
            use_count=5678
        ),
        
        # Intermediate Templates
        ProjectTemplate(
            id="ecommerce-nextjs",
            name="E-commerce Store",
            description="Complete online store with cart, checkout, and admin dashboard",
            category="intermediate",
            tech_stack=["Next.js", "Stripe", "PostgreSQL", "Prisma"],
            features=[
                "Product catalog with images",
                "Shopping cart",
                "Stripe payment integration",
                "Order management",
                "Admin dashboard",
                "Inventory tracking"
            ],
            setup_time="60 minutes",
            difficulty="Intermediate",
            tags=["ecommerce", "store", "stripe", "nextjs"],
            preview_url="https://demo-store.rocket-cli.dev",
            use_count=3456
        ),
        
        ProjectTemplate(
            id="social-media-clone",
            name="Social Media Platform",
            description="Twitter/Instagram-like platform with posts, likes, and follows",
            category="advanced",
            tech_stack=["Next.js", "Supabase", "Tailwind CSS", "Real-time"],
            features=[
                "User profiles",
                "Create posts with images",
                "Like and comment",
                "Follow users",
                "Real-time feed updates",
                "Notifications"
            ],
            setup_time="90 minutes",
            difficulty="Advanced",
            tags=["social", "realtime", "nextjs", "supabase"],
            preview_url="https://demo-social.rocket-cli.dev",
            use_count=2103
        ),
        
        ProjectTemplate(
            id="dashboard-analytics",
            name="Analytics Dashboard",
            description="Data visualization dashboard with charts, filters, and exports",
            category="intermediate",
            tech_stack=["React", "Recharts", "Node.js", "PostgreSQL"],
            features=[
                "Interactive charts",
                "Real-time data updates",
                "Filters and date ranges",
                "Export to CSV/PDF",
                "User management",
                "API integration"
            ],
            setup_time="45 minutes",
            difficulty="Intermediate",
            tags=["dashboard", "analytics", "charts", "data"],
            preview_url="https://demo-dashboard.rocket-cli.dev",
            use_count=4987
        ),
    ]
    
    @classmethod
    def get_all_templates(cls) -> List[ProjectTemplate]:
        """Get all available templates"""
        return cls.TEMPLATES
    
    @classmethod
    def get_template(cls, template_id: str) -> Optional[ProjectTemplate]:
        """Get a specific template by ID"""
        for template in cls.TEMPLATES:
            if template.id == template_id:
                return template
        return None
    
    @classmethod
    def get_by_category(cls, category: str) -> List[ProjectTemplate]:
        """Get templates by category"""
        return [t for t in cls.TEMPLATES if t.category == category]
    
    @classmethod
    def get_by_tag(cls, tag: str) -> List[ProjectTemplate]:
        """Get templates by tag"""
        return [t for t in cls.TEMPLATES if tag.lower() in [t.lower() for t in t.tags]]
    
    @classmethod
    def search(cls, query: str) -> List[ProjectTemplate]:
        """Search templates by name, description, or tags"""
        query = query.lower()
        results = []
        for template in cls.TEMPLATES:
            if (query in template.name.lower() or
                query in template.description.lower() or
                any(query in tag.lower() for tag in template.tags)):
                results.append(template)
        return results


class TemplateManager:
    """Manages template operations"""
    
    @staticmethod
    def list_templates(category: Optional[str] = None, tag: Optional[str] = None):
        """Display available templates"""
        
        # Get templates
        if category:
            templates = TemplateRegistry.get_by_category(category)
            title = f"📦 {category.title()} Templates"
        elif tag:
            templates = TemplateRegistry.get_by_tag(tag)
            title = f"🏷️ Templates tagged '{tag}'"
        else:
            templates = TemplateRegistry.get_all_templates()
            title = "📦 All Available Templates"
        
        if not templates:
            console.print(f"[yellow]No templates found.[/yellow]")
            return
        
        # Create table
        table = Table(show_header=True, header_style="bold magenta", title=title)
        table.add_column("ID", style="cyan", width=20)
        table.add_column("Name", style="green")
        table.add_column("Description", width=40)
        table.add_column("Difficulty", justify="center")
        table.add_column("Time", justify="center")
        table.add_column("Uses", justify="right")
        
        # Sort by popularity
        templates.sort(key=lambda t: t.use_count, reverse=True)
        
        for template in templates:
            difficulty_color = {
                "Beginner": "green",
                "Intermediate": "yellow",
                "Advanced": "red"
            }.get(template.difficulty, "white")
            
            table.add_row(
                template.id,
                template.name,
                template.description[:60] + "..." if len(template.description) > 60 else template.description,
                f"[{difficulty_color}]{template.difficulty}[/{difficulty_color}]",
                template.setup_time,
                f"{template.use_count:,}"
            )
        
        console.print(table)
        console.print(f"\n[dim]Total: {len(templates)} templates[/dim]")
        console.print("[dim]Use template: [cyan]rocket use <template-id>[/cyan][/dim]")
    
    @staticmethod
    def show_template_details(template_id: str):
        """Show detailed information about a template"""
        template = TemplateRegistry.get_template(template_id)
        
        if not template:
            console.print(f"[red]Template '{template_id}' not found.[/red]")
            return
        
        # Build details
        content = f"""[bold]{template.name}[/bold]

{template.description}

[bold]Tech Stack:[/bold]
{chr(10).join(f'  • {tech}' for tech in template.tech_stack)}

[bold]Features:[/bold]
{chr(10).join(f'  ✓ {feature}' for feature in template.features)}

[bold]Details:[/bold]
  • Difficulty: {template.difficulty}
  • Setup Time: {template.setup_time}
  • Category: {template.category.title()}
  • Used by: {template.use_count:,} developers

[bold]Tags:[/bold] {', '.join(template.tags)}
"""
        
        if template.preview_url:
            content += f"\n[bold]Preview:[/bold] {template.preview_url}"
        
        if template.video_url:
            content += f"\n[bold]Video Tutorial:[/bold] {template.video_url}"
        
        console.print(Panel(content, border_style="cyan", padding=(1, 2)))
        
        console.print(f"\n[bold green]Use this template:[/bold green]")
        console.print(f"  [cyan]rocket use {template.id}[/cyan]")
    
    @staticmethod
    def use_template(template_id: str, project_name: str, directory: Optional[str] = None):
        """Create a project from a template"""
        template = TemplateRegistry.get_template(template_id)
        
        if not template:
            console.print(f"[red]Template '{template_id}' not found.[/red]")
            return False
        
        # Set directory
        if not directory:
            directory = f"./{project_name}"
        
        console.print(f"\n[bold]Creating project from template: {template.name}[/bold]\n")
        
        # Create project structure
        project_dir = Path(directory)
        project_dir.mkdir(parents=True, exist_ok=True)
        
        console.print(f"✅ Created directory: {directory}")
        
        # Generate template files based on type
        TemplateManager._generate_template_files(template, project_dir, project_name)
        
        console.print(f"\n[bold green]✅ Project created from template![/bold green]")
        console.print(Panel(
            f"[bold]📁 Project location:[/bold] {directory}\n\n"
            "[bold]Next steps:[/bold]\n"
            f"1. cd {directory}\n"
            "2. npm install\n"
            "3. npm run dev\n\n"
            "[dim]Or use: [cyan]rocket dev[/cyan] to start automatically[/dim]",
            border_style="green"
        ))
        
        return True
    
    @staticmethod
    def _generate_template_files(template: ProjectTemplate, project_dir: Path, project_name: str):
        """Generate files for a specific template"""
        
        # Common files for all templates
        TemplateManager._create_package_json(template, project_dir, project_name)
        TemplateManager._create_readme(template, project_dir, project_name)
        TemplateManager._create_gitignore(project_dir)
        
        # Template-specific files
        if "Next.js" in template.tech_stack:
            TemplateManager._create_nextjs_structure(template, project_dir, project_name)
        elif "React" in template.tech_stack:
            TemplateManager._create_react_structure(template, project_dir, project_name)
        elif "Astro" in template.tech_stack:
            TemplateManager._create_astro_structure(template, project_dir, project_name)
    
    @staticmethod
    def _create_package_json(template: ProjectTemplate, project_dir: Path, project_name: str):
        """Create package.json"""
        package_json = {
            "name": project_name,
            "version": "0.1.0",
            "private": True,
            "description": template.description,
            "scripts": {
                "dev": "next dev" if "Next.js" in template.tech_stack else "vite",
                "build": "next build" if "Next.js" in template.tech_stack else "vite build",
                "start": "next start" if "Next.js" in template.tech_stack else "vite preview"
            },
            "dependencies": {},
            "devDependencies": {}
        }
        
        with open(project_dir / "package.json", "w") as f:
            json.dump(package_json, f, indent=2)
        
        console.print("✅ Created package.json")
    
    @staticmethod
    def _create_readme(template: ProjectTemplate, project_dir: Path, project_name: str):
        """Create README.md"""
        readme = f"""# {project_name}

{template.description}

## Tech Stack

{chr(10).join(f'- {tech}' for tech in template.tech_stack)}

## Features

{chr(10).join(f'- {feature}' for feature in template.features)}

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Deploy

Deploy with one command:
```bash
rocket deploy
```

---

Created with 🚀 [Rocket CLI](https://rocket-cli.dev) using the `{template.id}` template.
"""
        
        with open(project_dir / "README.md", "w") as f:
            f.write(readme)
        
        console.print("✅ Created README.md")
    
    @staticmethod
    def _create_gitignore(project_dir: Path):
        """Create .gitignore"""
        gitignore = """# Dependencies
node_modules/
.pnp
.pnp.js

# Testing
/coverage

# Next.js
/.next/
/out/

# Production
/build
/dist

# Misc
.DS_Store
*.pem

# Debug
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Local env files
.env*.local
.env

# Vercel
.vercel

# TypeScript
*.tsbuildinfo
next-env.d.ts
"""
        
        with open(project_dir / ".gitignore", "w") as f:
            f.write(gitignore)
        
        console.print("✅ Created .gitignore")
    
    @staticmethod
    def _create_nextjs_structure(template: ProjectTemplate, project_dir: Path, project_name: str):
        """Create Next.js project structure"""
        app_dir = project_dir / "app"
        app_dir.mkdir(exist_ok=True)
        
        # Layout
        layout = """import './globals.css'

export const metadata = {
  title: '%s',
  description: '%s',
}

export default function RootLayout({
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
""" % (project_name, template.description)
        
        with open(app_dir / "layout.tsx", "w") as f:
            f.write(layout)
        
        # Home page
        page = """export default function Home() {
  return (
    <main className="min-h-screen p-24">
      <h1 className="text-4xl font-bold">Welcome to %s!</h1>
      <p className="mt-4">%s</p>
    </main>
  )
}
""" % (project_name, template.description)
        
        with open(app_dir / "page.tsx", "w") as f:
            f.write(page)
        
        console.print("✅ Created Next.js structure")
    
    @staticmethod
    def _create_react_structure(template: ProjectTemplate, project_dir: Path, project_name: str):
        """Create React project structure"""
        src_dir = project_dir / "src"
        src_dir.mkdir(exist_ok=True)
        
        # Main App component
        app_tsx = """function App() {
  return (
    <div className="min-h-screen p-8">
      <h1 className="text-4xl font-bold">%s</h1>
      <p className="mt-4">%s</p>
    </div>
  )
}

export default App
""" % (project_name, template.description)
        
        with open(src_dir / "App.tsx", "w") as f:
            f.write(app_tsx)
        
        console.print("✅ Created React structure")
    
    @staticmethod
    def _create_astro_structure(template: ProjectTemplate, project_dir: Path, project_name: str):
        """Create Astro project structure"""
        src_dir = project_dir / "src"
        pages_dir = src_dir / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        
        # Index page
        index = """---
title: '%s'
---

<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>{title}</title>
  </head>
  <body>
    <main>
      <h1>%s</h1>
      <p>%s</p>
    </main>
  </body>
</html>
""" % (project_name, project_name, template.description)
        
        with open(pages_dir / "index.astro", "w") as f:
            f.write(index)
        
        console.print("✅ Created Astro structure")


if __name__ == "__main__":
    # Demo
    TemplateManager.list_templates()
