"""
Rocket CLI - One-Click Deployment System
Deploys projects to Vercel, Netlify, or other platforms with zero configuration
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


class ProjectDetector:
    """Detects project type and framework from project structure"""
    
    @staticmethod
    def detect_project_type(project_path: str) -> Dict[str, any]:
        """
        Detect project type, framework, and build settings
        
        Returns:
            Dict with: type, framework, build_command, output_dir, install_command
        """
        path = Path(project_path)
        
        # Check for package.json (Node.js projects)
        package_json = path / "package.json"
        if package_json.exists():
            with open(package_json, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
                
            dependencies = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
            scripts = package_data.get("scripts", {})
            
            # Next.js
            if "next" in dependencies:
                return {
                    "type": "node",
                    "framework": "Next.js",
                    "build_command": scripts.get("build", "npm run build"),
                    "install_command": "npm install",
                    "output_dir": ".next",
                    "dev_command": scripts.get("dev", "npm run dev"),
                    "platform": "vercel"
                }
            
            # React (Vite)
            elif "vite" in dependencies:
                return {
                    "type": "node",
                    "framework": "Vite + React",
                    "build_command": scripts.get("build", "npm run build"),
                    "install_command": "npm install",
                    "output_dir": "dist",
                    "dev_command": scripts.get("dev", "npm run dev"),
                    "platform": "vercel"
                }
            
            # React (Create React App)
            elif "react-scripts" in dependencies:
                return {
                    "type": "node",
                    "framework": "Create React App",
                    "build_command": scripts.get("build", "npm run build"),
                    "install_command": "npm install",
                    "output_dir": "build",
                    "dev_command": scripts.get("start", "npm start"),
                    "platform": "vercel"
                }
            
            # Vue.js
            elif "vue" in dependencies:
                return {
                    "type": "node",
                    "framework": "Vue.js",
                    "build_command": scripts.get("build", "npm run build"),
                    "install_command": "npm install",
                    "output_dir": "dist",
                    "dev_command": scripts.get("dev", "npm run dev"),
                    "platform": "vercel"
                }
            
            # Generic Node.js
            else:
                return {
                    "type": "node",
                    "framework": "Node.js",
                    "build_command": scripts.get("build", ""),
                    "install_command": "npm install",
                    "output_dir": "",
                    "dev_command": scripts.get("start", "node index.js"),
                    "platform": "vercel"
                }
        
        # Check for Astro
        astro_config = path / "astro.config.mjs"
        if astro_config.exists():
            return {
                "type": "node",
                "framework": "Astro",
                "build_command": "npm run build",
                "install_command": "npm install",
                "output_dir": "dist",
                "dev_command": "npm run dev",
                "platform": "vercel"
            }
        
        # Check for Python projects
        requirements_txt = path / "requirements.txt"
        pyproject_toml = path / "pyproject.toml"
        
        if requirements_txt.exists() or pyproject_toml.exists():
            # Check for Flask
            if requirements_txt.exists():
                with open(requirements_txt, 'r') as f:
                    reqs = f.read()
                    if "flask" in reqs.lower():
                        return {
                            "type": "python",
                            "framework": "Flask",
                            "build_command": "",
                            "install_command": "pip install -r requirements.txt",
                            "output_dir": "",
                            "dev_command": "python app.py",
                            "platform": "vercel"
                        }
                    elif "fastapi" in reqs.lower():
                        return {
                            "type": "python",
                            "framework": "FastAPI",
                            "build_command": "",
                            "install_command": "pip install -r requirements.txt",
                            "output_dir": "",
                            "dev_command": "uvicorn main:app --reload",
                            "platform": "vercel"
                        }
            
            return {
                "type": "python",
                "framework": "Python",
                "build_command": "",
                "install_command": "pip install -r requirements.txt" if requirements_txt.exists() else "",
                "output_dir": "",
                "dev_command": "python main.py",
                "platform": "vercel"
            }
        
        # Static HTML site
        index_html = path / "index.html"
        if index_html.exists():
            return {
                "type": "static",
                "framework": "Static HTML",
                "build_command": "",
                "install_command": "",
                "output_dir": ".",
                "dev_command": "python -m http.server 8000",
                "platform": "vercel"
            }
        
        # Unknown project type
        return {
            "type": "unknown",
            "framework": "Unknown",
            "build_command": "",
            "install_command": "",
            "output_dir": "",
            "dev_command": "",
            "platform": "vercel"
        }


class VercelDeployer:
    """Handles deployment to Vercel"""
    
    @staticmethod
    def check_vercel_cli() -> bool:
        """Check if Vercel CLI is installed"""
        try:
            result = subprocess.run(
                ["vercel", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    @staticmethod
    def install_vercel_cli() -> bool:
        """Install Vercel CLI globally"""
        console.print("[yellow]📦 Installing Vercel CLI...[/yellow]")
        
        try:
            # Try npm first
            result = subprocess.run(
                ["npm", "install", "-g", "vercel"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                console.print("[green]✅ Vercel CLI installed successfully![/green]")
                return True
            else:
                console.print(f"[red]❌ Failed to install Vercel CLI: {result.stderr}[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]❌ Error installing Vercel CLI: {str(e)}[/red]")
            return False
    
    @staticmethod
    def create_vercel_json(project_path: str, project_info: Dict) -> bool:
        """Create vercel.json configuration file"""
        
        vercel_config = {}
        
        # Framework-specific configurations
        if project_info["framework"] == "Next.js":
            vercel_config = {
                "buildCommand": project_info["build_command"],
                "outputDirectory": project_info["output_dir"],
                "framework": "nextjs"
            }
        
        elif project_info["framework"] in ["Vite + React", "Create React App"]:
            vercel_config = {
                "buildCommand": project_info["build_command"],
                "outputDirectory": project_info["output_dir"],
                "framework": "vite" if "Vite" in project_info["framework"] else "create-react-app"
            }
        
        elif project_info["framework"] == "Astro":
            vercel_config = {
                "buildCommand": project_info["build_command"],
                "outputDirectory": project_info["output_dir"],
                "framework": "astro"
            }
        
        elif project_info["framework"] in ["Flask", "FastAPI"]:
            # Python API configuration
            vercel_config = {
                "builds": [
                    {
                        "src": "*.py",
                        "use": "@vercel/python"
                    }
                ],
                "routes": [
                    {
                        "src": "/(.*)",
                        "dest": "app.py" if project_info["framework"] == "Flask" else "main.py"
                    }
                ]
            }
        
        elif project_info["framework"] == "Static HTML":
            vercel_config = {
                "public": True
            }
        
        # Write vercel.json
        try:
            vercel_json_path = Path(project_path) / "vercel.json"
            
            # Check if vercel.json already exists
            if vercel_json_path.exists():
                console.print("[yellow]⚠️  vercel.json already exists, skipping creation[/yellow]")
                return True
            
            with open(vercel_json_path, 'w', encoding='utf-8') as f:
                json.dump(vercel_config, f, indent=2)
            
            console.print(f"[green]✅ Created vercel.json configuration[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Error creating vercel.json: {str(e)}[/red]")
            return False
    
    @staticmethod
    def deploy(project_path: str, production: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Deploy project to Vercel
        
        Returns:
            (success: bool, deployment_url: Optional[str])
        """
        try:
            # Build deploy command
            deploy_cmd = ["vercel"]
            
            if production:
                deploy_cmd.append("--prod")
            
            # Change to project directory and deploy
            console.print(f"\n[cyan]🚀 Deploying to Vercel{'(Production)' if production else '(Preview)'}...[/cyan]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Deploying project...", total=None)
                
                result = subprocess.run(
                    deploy_cmd,
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes timeout
                )
                
                progress.update(task, completed=True)
            
            if result.returncode == 0:
                # Extract deployment URL from output
                output = result.stdout
                deployment_url = None
                
                # Look for URL in output
                for line in output.split('\n'):
                    if 'https://' in line and 'vercel.app' in line:
                        # Extract URL
                        import re
                        url_match = re.search(r'https://[^\s]+', line)
                        if url_match:
                            deployment_url = url_match.group(0)
                            break
                
                return True, deployment_url
            else:
                console.print(f"[red]❌ Deployment failed: {result.stderr}[/red]")
                return False, None
                
        except subprocess.TimeoutExpired:
            console.print("[red]❌ Deployment timed out (5 minutes)[/red]")
            return False, None
        except Exception as e:
            console.print(f"[red]❌ Deployment error: {str(e)}[/red]")
            return False, None


class DeploymentManager:
    """Main deployment orchestrator"""
    
    @staticmethod
    def deploy_project(project_path: str = ".", production: bool = True, auto_confirm: bool = False):
        """
        One-click deployment workflow
        
        Steps:
        1. Detect project type and framework
        2. Show detected configuration
        3. Check/install Vercel CLI
        4. Create vercel.json if needed
        5. Deploy to Vercel
        6. Show deployment URL
        """
        
        console.print("\n")
        console.print(Panel.fit(
            "[bold cyan]🚀 Rocket Deploy[/bold cyan]\n"
            "One-click deployment to production",
            border_style="cyan"
        ))
        
        # Step 1: Detect project
        console.print("\n[cyan]📋 Detecting project...[/cyan]")
        project_info = ProjectDetector.detect_project_type(project_path)
        
        if project_info["type"] == "unknown":
            console.print("[red]❌ Could not detect project type[/red]")
            console.print("[yellow]💡 Supported: Next.js, React, Vue, Astro, Flask, FastAPI, Static HTML[/yellow]")
            return
        
        # Step 2: Show detected configuration
        table = Table(title="🎯 Detected Project Configuration", show_header=True, header_style="bold magenta")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Framework", project_info["framework"])
        table.add_row("Build Command", project_info["build_command"] or "(none)")
        table.add_row("Output Directory", project_info["output_dir"] or "(none)")
        table.add_row("Install Command", project_info["install_command"] or "(none)")
        table.add_row("Platform", project_info["platform"].title())
        
        console.print("\n")
        console.print(table)
        console.print("\n")
        
        # Confirm deployment
        if not auto_confirm:
            proceed = Confirm.ask("🚀 Deploy this project?", default=True)
            if not proceed:
                console.print("[yellow]Deployment cancelled[/yellow]")
                return
        
        # Step 3: Check Vercel CLI
        console.print("\n[cyan]🔍 Checking Vercel CLI...[/cyan]")
        
        if not VercelDeployer.check_vercel_cli():
            console.print("[yellow]⚠️  Vercel CLI not found[/yellow]")
            
            if auto_confirm or Confirm.ask("Install Vercel CLI now?", default=True):
                if not VercelDeployer.install_vercel_cli():
                    console.print("[red]❌ Failed to install Vercel CLI. Please install manually: npm install -g vercel[/red]")
                    return
            else:
                console.print("[yellow]Deployment cancelled[/yellow]")
                return
        else:
            console.print("[green]✅ Vercel CLI is installed[/green]")
        
        # Step 4: Create vercel.json
        console.print("\n[cyan]📝 Creating deployment configuration...[/cyan]")
        VercelDeployer.create_vercel_json(project_path, project_info)
        
        # Step 5: Deploy
        success, deployment_url = VercelDeployer.deploy(project_path, production=production)
        
        # Step 6: Show results
        if success:
            console.print("\n")
            console.print(Panel.fit(
                f"[bold green]🎉 Deployment Successful![/bold green]\n\n"
                f"[cyan]Your project is live at:[/cyan]\n"
                f"[bold white]{deployment_url or 'Check Vercel dashboard for URL'}[/bold white]\n\n"
                f"[yellow]💡 Next steps:[/yellow]\n"
                f"  • Visit your site and test it\n"
                f"  • Share the URL with others\n"
                f"  • Connect a custom domain in Vercel dashboard",
                border_style="green",
                title="✨ Success"
            ))
        else:
            console.print("\n")
            console.print(Panel.fit(
                "[bold red]❌ Deployment Failed[/bold red]\n\n"
                "[yellow]Troubleshooting:[/yellow]\n"
                "  1. Check if you're logged into Vercel: vercel login\n"
                "  2. Ensure your project builds locally: npm run build\n"
                "  3. Check vercel.json configuration\n"
                "  4. Try manual deployment: vercel --prod\n\n"
                "[cyan]Need help?[/cyan] rocket debug -c 'vercel deployment failed'",
                border_style="red",
                title="❌ Error"
            ))
