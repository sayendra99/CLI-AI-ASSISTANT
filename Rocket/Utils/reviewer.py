"""
Rocket CLI - AI Code Review System
Analyzes code for security, performance, and best practices
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.markdown import Markdown

console = Console()


class CodeScanner:
    """Scans codebase for common issues"""
    
    # Security patterns to detect
    SECURITY_PATTERNS = {
        "hardcoded_secrets": {
            "patterns": [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']',
                r'token\s*=\s*["\'][^"\']+["\']',
                r'AWS_SECRET_ACCESS_KEY',
                r'PRIVATE_KEY'
            ],
            "severity": "HIGH",
            "message": "Hardcoded secrets detected",
            "fix": "Use environment variables or secret management tools"
        },
        "sql_injection": {
            "patterns": [
                r'execute\(["\'].*\%s.*["\']',
                r'cursor\.execute\(.*\+.*\)',
                r'\.raw\(.*\+.*\)'
            ],
            "severity": "HIGH",
            "message": "Potential SQL injection vulnerability",
            "fix": "Use parameterized queries or ORM with prepared statements"
        },
        "unsafe_eval": {
            "patterns": [
                r'\beval\(',
                r'\bexec\('
            ],
            "severity": "MEDIUM",
            "message": "Unsafe use of eval() or exec()",
            "fix": "Avoid eval/exec or validate input thoroughly"
        }
    }
    
    # Performance anti-patterns
    PERFORMANCE_PATTERNS = {
        "nested_loops": {
            "severity": "MEDIUM",
            "message": "Nested loops detected (O(n²) complexity)",
            "fix": "Consider using hash maps or optimizing algorithm"
        },
        "inefficient_append": {
            "patterns": [
                r'for\s+.*:\s*.*\+=\s*["\']'
            ],
            "severity": "LOW",
            "message": "String concatenation in loop",
            "fix": "Use list.append() and ''.join() for better performance"
        }
    }
    
    @staticmethod
    def scan_file(file_path: str) -> List[Dict]:
        """
        Scan a single file for issues
        
        Returns:
            List of issues found with line numbers
        """
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, start=1):
                # Check security patterns
                for check_name, check_info in CodeScanner.SECURITY_PATTERNS.items():
                    import re
                    for pattern in check_info["patterns"]:
                        if re.search(pattern, line, re.IGNORECASE):
                            issues.append({
                                "file": file_path,
                                "line": line_num,
                                "type": "security",
                                "severity": check_info["severity"],
                                "message": check_info["message"],
                                "fix": check_info["fix"],
                                "code": line.strip()
                            })
                
                # Check performance patterns
                for check_name, check_info in CodeScanner.PERFORMANCE_PATTERNS.items():
                    if "patterns" in check_info:
                        for pattern in check_info["patterns"]:
                            if re.search(pattern, line, re.IGNORECASE):
                                issues.append({
                                    "file": file_path,
                                    "line": line_num,
                                    "type": "performance",
                                    "severity": check_info["severity"],
                                    "message": check_info["message"],
                                    "fix": check_info["fix"],
                                    "code": line.strip()
                                })
            
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not scan {file_path}: {str(e)}[/yellow]")
        
        return issues
    
    @staticmethod
    def scan_directory(directory: str, extensions: Set[str]) -> List[Dict]:
        """
        Recursively scan directory for code issues
        
        Args:
            directory: Root directory to scan
            extensions: Set of file extensions to scan (e.g., {'.py', '.js'})
        """
        all_issues = []
        scanned_files = 0
        
        # Directories to skip
        skip_dirs = {
            'node_modules', '__pycache__', '.git', 'venv', 'env',
            'dist', 'build', '.next', 'coverage', '.pytest_cache'
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Scanning files...", total=None)
            
            for root, dirs, files in os.walk(directory):
                # Remove skip directories from traversal
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                
                for file in files:
                    file_path = Path(root) / file
                    
                    if file_path.suffix in extensions:
                        scanned_files += 1
                        progress.update(task, description=f"Scanning {file_path.name}...")
                        
                        file_issues = CodeScanner.scan_file(str(file_path))
                        all_issues.extend(file_issues)
        
        console.print(f"[green]✅ Scanned {scanned_files} files[/green]\n")
        return all_issues


class BestPracticesChecker:
    """Checks for language-specific best practices"""
    
    @staticmethod
    def check_python_file(file_path: str) -> List[Dict]:
        """Check Python-specific best practices"""
        suggestions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for missing docstrings in functions/classes
            import re
            func_pattern = r'^\s*def\s+\w+\s*\('
            class_pattern = r'^\s*class\s+\w+\s*[:(]'
            
            for i, line in enumerate(lines):
                if re.match(func_pattern, line) or re.match(class_pattern, line):
                    # Check if next non-empty line is a docstring
                    next_line_idx = i + 1
                    while next_line_idx < len(lines) and not lines[next_line_idx].strip():
                        next_line_idx += 1
                    
                    if next_line_idx < len(lines):
                        next_line = lines[next_line_idx].strip()
                        if not (next_line.startswith('"""') or next_line.startswith("'''")):
                            suggestions.append({
                                "file": file_path,
                                "line": i + 1,
                                "type": "best_practice",
                                "severity": "LOW",
                                "message": "Missing docstring",
                                "fix": "Add docstring to document function/class purpose",
                                "code": line.strip()
                            })
            
            # Check for broad exception catching
            broad_except_pattern = r'except\s*:'
            for i, line in enumerate(lines):
                if re.search(broad_except_pattern, line):
                    suggestions.append({
                        "file": file_path,
                        "line": i + 1,
                        "type": "best_practice",
                        "severity": "LOW",
                        "message": "Bare except clause catches all exceptions",
                        "fix": "Catch specific exceptions (e.g., except ValueError:)",
                        "code": line.strip()
                    })
            
        except Exception as e:
            pass
        
        return suggestions
    
    @staticmethod
    def check_javascript_file(file_path: str) -> List[Dict]:
        """Check JavaScript-specific best practices"""
        suggestions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            import re
            
            # Check for var instead of let/const
            var_pattern = r'\bvar\s+\w+'
            for i, line in enumerate(lines, start=1):
                if re.search(var_pattern, line):
                    suggestions.append({
                        "file": file_path,
                        "line": i,
                        "type": "best_practice",
                        "severity": "LOW",
                        "message": "Use 'let' or 'const' instead of 'var'",
                        "fix": "Replace 'var' with 'const' (immutable) or 'let' (mutable)",
                        "code": line.strip()
                    })
            
            # Check for console.log in production code
            console_pattern = r'console\.log\('
            for i, line in enumerate(lines, start=1):
                if re.search(console_pattern, line):
                    suggestions.append({
                        "file": file_path,
                        "line": i,
                        "type": "best_practice",
                        "severity": "LOW",
                        "message": "console.log() found in code",
                        "fix": "Remove debug logs or use proper logging library",
                        "code": line.strip()
                    })
            
        except Exception as e:
            pass
        
        return suggestions


class CodeReviewer:
    """Main code review orchestrator"""
    
    @staticmethod
    def review_project(
        project_path: str = ".",
        include_security: bool = True,
        include_performance: bool = True,
        include_best_practices: bool = True
    ):
        """
        Comprehensive code review
        
        Args:
            project_path: Path to project directory
            include_security: Check for security vulnerabilities
            include_performance: Check for performance issues
            include_best_practices: Check for best practices
        """
        
        console.print("\n")
        console.print(Panel.fit(
            "[bold cyan]🔍 Rocket Review[/bold cyan]\n"
            "AI-Powered Code Quality Analysis",
            border_style="cyan"
        ))
        console.print("\n")
        
        # Detect project type and determine file extensions
        extensions_to_scan = set()
        
        if Path(project_path, "package.json").exists():
            extensions_to_scan.update({'.js', '.jsx', '.ts', '.tsx'})
        
        if Path(project_path, "requirements.txt").exists() or Path(project_path, "pyproject.toml").exists():
            extensions_to_scan.add('.py')
        
        if not extensions_to_scan:
            # Default: scan common file types
            extensions_to_scan = {'.py', '.js', '.jsx', '.ts', '.tsx'}
        
        console.print(f"[cyan]📁 Scanning: {project_path}[/cyan]")
        console.print(f"[cyan]📄 File types: {', '.join(extensions_to_scan)}[/cyan]\n")
        
        # Scan for issues
        all_issues = []
        
        if include_security or include_performance:
            all_issues.extend(CodeScanner.scan_directory(project_path, extensions_to_scan))
        
        # Check best practices
        if include_best_practices:
            for root, dirs, files in os.walk(project_path):
                skip_dirs = {'node_modules', '__pycache__', '.git', 'venv'}
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                
                for file in files:
                    file_path = Path(root) / file
                    
                    if file_path.suffix == '.py':
                        all_issues.extend(BestPracticesChecker.check_python_file(str(file_path)))
                    elif file_path.suffix in {'.js', '.jsx', '.ts', '.tsx'}:
                        all_issues.extend(BestPracticesChecker.check_javascript_file(str(file_path)))
        
        # Display results
        CodeReviewer._display_results(all_issues)
    
    @staticmethod
    def _display_results(issues: List[Dict]):
        """Display review results in a beautiful format"""
        
        if not issues:
            console.print(Panel.fit(
                "[bold green]🎉 Excellent![/bold green]\n\n"
                "No issues found in your codebase.\n"
                "Your code follows security best practices and performance guidelines.",
                border_style="green",
                title="✨ Clean Code"
            ))
            return
        
        # Group issues by severity
        high_severity = [i for i in issues if i["severity"] == "HIGH"]
        medium_severity = [i for i in issues if i["severity"] == "MEDIUM"]
        low_severity = [i for i in issues if i["severity"] == "LOW"]
        
        # Summary
        console.print(Panel.fit(
            f"[bold]Found {len(issues)} issues:[/bold]\n"
            f"🔴 High: {len(high_severity)}\n"
            f"🟡 Medium: {len(medium_severity)}\n"
            f"🟢 Low: {len(low_severity)}",
            border_style="yellow",
            title="📊 Summary"
        ))
        console.print("\n")
        
        # Display issues by severity
        for severity, severity_issues, color in [
            ("HIGH", high_severity, "red"),
            ("MEDIUM", medium_severity, "yellow"),
            ("LOW", low_severity, "blue")
        ]:
            if not severity_issues:
                continue
            
            console.print(f"\n[bold {color}]{'🔴' if severity == 'HIGH' else '🟡' if severity == 'MEDIUM' else '🟢'} {severity} PRIORITY ({len(severity_issues)} issues)[/bold {color}]\n")
            
            for i, issue in enumerate(severity_issues[:5], 1):  # Show first 5
                file_rel = Path(issue["file"]).name
                
                console.print(Panel(
                    f"[bold]{issue['message']}[/bold]\n\n"
                    f"[cyan]📁 File:[/cyan] {file_rel}:{issue['line']}\n"
                    f"[cyan]💡 Fix:[/cyan] {issue['fix']}\n\n"
                    f"[dim]Code:[/dim]\n[dim]{issue['code']}[/dim]",
                    border_style=color,
                    title=f"Issue #{i}"
                ))
            
            if len(severity_issues) > 5:
                console.print(f"[dim]... and {len(severity_issues) - 5} more {severity.lower()} priority issues[/dim]\n")
        
        # Recommendations
        console.print("\n")
        console.print(Panel.fit(
            "[bold cyan]📝 Next Steps:[/bold cyan]\n\n"
            "1. Fix HIGH priority security issues immediately\n"
            "2. Address MEDIUM priority performance issues\n"
            "3. Improve code quality with LOW priority suggestions\n"
            "4. Run 'rocket review' again after fixes\n\n"
            "[yellow]💡 Tip:[/yellow] Focus on security issues first!",
            border_style="cyan",
            title="✨ Recommendations"
        ))
