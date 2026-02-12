"""
Test Suite for Phase 1 Enhancements
Tests: Error Handler, Project Wizard, Templates System
"""

import sys
import os
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    try:
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
        if sys.stderr.encoding != 'utf-8':
            sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel

console = Console()


def test_error_handler():
    """Test the intelligent error handler"""
    console.print("\n[bold cyan]Testing Error Handler...[/bold cyan]\n")
    
    from Rocket.Utils.error_handler import ErrorHandler
    
    test_cases = [
        ("ModuleNotFoundError: No module named 'requests'", "Missing Library"),
        ("SyntaxError: invalid syntax", "Syntax Error"),
        ("NameError: name 'user' is not defined", "Unknown Variable"),
        ("TypeError: can only concatenate str (not 'int') to str", "Type Mismatch"),
        ("KeyError: 'email'", "Missing Dictionary Key"),
    ]
    
    passed = 0
    failed = 0
    
    for error_msg, expected_title in test_cases:
        result = ErrorHandler.explain_error(error_msg)
        
        if result["title"] == expected_title:
            console.print(f"✅ {expected_title}: [green]PASS[/green]")
            passed += 1
        else:
            console.print(f"❌ {expected_title}: [red]FAIL[/red] (got '{result['title']}')")
            failed += 1
    
    console.print(f"\n[bold]Error Handler Results:[/bold] {passed}/{len(test_cases)} passed")
    
    # Show example output
    console.print("\n[dim]Example error explanation:[/dim]")
    ErrorHandler.display_friendly_error(
        "ModuleNotFoundError: No module named 'requests'",
        "ModuleNotFoundError"
    )
    
    return passed, failed


def test_templates_system():
    """Test the templates registry and manager"""
    console.print("\n[bold cyan]Testing Templates System...[/bold cyan]\n")
    
    from Rocket.Utils.templates import TemplateRegistry, TemplateManager
    
    tests = []
    
    # Test 1: Get all templates
    try:
        templates = TemplateRegistry.get_all_templates()
        if len(templates) >= 5:
            console.print(f"✅ Templates loaded: [green]{len(templates)} templates[/green]")
            tests.append(True)
        else:
            console.print(f"❌ Templates loaded: [red]Expected >= 5, got {len(templates)}[/red]")
            tests.append(False)
    except Exception as e:
        console.print(f"❌ Get all templates: [red]FAILED - {e}[/red]")
        tests.append(False)
    
    # Test 2: Get template by ID
    try:
        template = TemplateRegistry.get_template("portfolio-nextjs")
        if template and template.name == "Personal Portfolio":
            console.print(f"✅ Get template by ID: [green]PASS[/green]")
            tests.append(True)
        else:
            console.print(f"❌ Get template by ID: [red]FAIL[/red]")
            tests.append(False)
    except Exception as e:
        console.print(f"❌ Get template by ID: [red]FAILED - {e}[/red]")
        tests.append(False)
    
    # Test 3: Filter by category
    try:
        beginner_templates = TemplateRegistry.get_by_category("beginner")
        if len(beginner_templates) >= 3:
            console.print(f"✅ Filter by category: [green]{len(beginner_templates)} beginner templates[/green]")
            tests.append(True)
        else:
            console.print(f"❌ Filter by category: [red]FAIL[/red]")
            tests.append(False)
    except Exception as e:
        console.print(f"❌ Filter by category: [red]FAILED - {e}[/red]")
        tests.append(False)
    
    # Test 4: Search templates
    try:
        results = TemplateRegistry.search("portfolio")
        if len(results) > 0:
            console.print(f"✅ Search templates: [green]Found {len(results)} results[/green]")
            tests.append(True)
        else:
            console.print(f"❌ Search templates: [red]FAIL[/red]")
            tests.append(False)
    except Exception as e:
        console.print(f"❌ Search templates: [red]FAILED - {e}[/red]")
        tests.append(False)
    
    # Show template list
    console.print("\n[dim]Template catalog preview:[/dim]")
    TemplateManager.list_templates(category="beginner")
    
    passed = sum(tests)
    failed = len(tests) - passed
    console.print(f"\n[bold]Templates System Results:[/bold] {passed}/{len(tests)} passed")
    
    return passed, failed


def test_project_wizard():
    """Test the project wizard (structure only, not interactive)"""
    console.print("\n[bold cyan]Testing Project Wizard...[/bold cyan]\n")
    
    from Rocket.CLI.wizard import ProjectWizard
    
    tests = []
    
    # Test 1: Check project types exist
    try:
        if len(ProjectWizard.PROJECT_TYPES) >= 5:
            console.print(f"✅ Project types defined: [green]{len(ProjectWizard.PROJECT_TYPES)} types[/green]")
            tests.append(True)
        else:
            console.print(f"❌ Project types: [red]FAIL[/red]")
            tests.append(False)
    except Exception as e:
        console.print(f"❌ Project types: [red]FAILED - {e}[/red]")
        tests.append(False)
    
    # Test 2: Check project type structure
    try:
        portfolio = ProjectWizard.PROJECT_TYPES.get("1")
        required_keys = ["name", "description", "difficulty", "time", "tech_stack"]
        has_all_keys = all(key in portfolio for key in required_keys)
        
        if portfolio and has_all_keys:
            console.print(f"✅ Project type structure: [green]PASS[/green]")
            tests.append(True)
        else:
            missing = [key for key in required_keys if key not in portfolio]
            console.print(f"❌ Project type structure: [red]FAIL - Missing keys: {missing}[/red]")
            tests.append(False)
    except Exception as e:
        console.print(f"❌ Project type structure: [red]FAILED - {e}[/red]")
        tests.append(False)
    
    # Test 3: Check wizard methods exist
    try:
        methods = ["welcome", "select_project_type", "gather_project_details", 
                  "show_tech_stack", "create_project", "show_next_steps"]
        all_exist = all(hasattr(ProjectWizard, method) for method in methods)
        
        if all_exist:
            console.print(f"✅ Wizard methods: [green]All required methods exist[/green]")
            tests.append(True)
        else:
            console.print(f"❌ Wizard methods: [red]FAIL[/red]")
            tests.append(False)
    except Exception as e:
        console.print(f"❌ Wizard methods: [red]FAILED - {e}[/red]")
        tests.append(False)
    
    # Show project types
    console.print("\n[dim]Available project types:[/dim]")
    from rich.table import Table
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="cyan", width=3)
    table.add_column("Project Type", style="green")
    table.add_column("Difficulty", justify="center")
    table.add_column("Time", justify="center")
    
    for key, project in ProjectWizard.PROJECT_TYPES.items():
        difficulty_color = {
            "Beginner": "green",
            "Intermediate": "yellow",
            "Advanced": "red"
        }.get(project["difficulty"], "white")
        
        table.add_row(
            key,
            project["name"],
            f"[{difficulty_color}]{project['difficulty']}[/{difficulty_color}]",
            project["time"]
        )
    
    console.print(table)
    
    passed = sum(tests)
    failed = len(tests) - passed
    console.print(f"\n[bold]Project Wizard Results:[/bold] {passed}/{len(tests)} passed")
    
    return passed, failed


def test_integration():
    """Test that all components work together"""
    console.print("\n[bold cyan]Testing Integration...[/bold cyan]\n")
    
    tests = []
    
    # Test 1: Can import all modules
    try:
        from Rocket.Utils.error_handler import ErrorHandler, ExceptionWrapper
        from Rocket.CLI.wizard import ProjectWizard
        from Rocket.Utils.templates import TemplateRegistry, TemplateManager
        
        console.print("✅ All modules import successfully: [green]PASS[/green]")
        tests.append(True)
    except Exception as e:
        console.print(f"❌ Module imports: [red]FAILED - {e}[/red]")
        tests.append(False)
    
    # Test 2: Error handler works with templates
    try:
        from Rocket.Utils.error_handler import ErrorHandler
        from Rocket.Utils.templates import TemplateRegistry
        
        # Simulate an error when template not found
        template = TemplateRegistry.get_template("non-existent")
        if template is None:
            # This is expected behavior
            console.print("✅ Error handling in templates: [green]PASS[/green]")
            tests.append(True)
        else:
            console.print("❌ Error handling in templates: [red]FAIL[/red]")
            tests.append(False)
    except Exception as e:
        console.print(f"❌ Error handling integration: [red]FAILED - {e}[/red]")
        tests.append(False)
    
    # Test 3: Template can be used in wizard context
    try:
        from Rocket.Utils.templates import TemplateRegistry
        
        template = TemplateRegistry.get_template("portfolio-nextjs")
        if template and hasattr(template, 'tech_stack') and hasattr(template, 'features'):
            console.print("✅ Template-Wizard compatibility: [green]PASS[/green]")
            tests.append(True)
        else:
            console.print("❌ Template-Wizard compatibility: [red]FAIL[/red]")
            tests.append(False)
    except Exception as e:
        console.print(f"❌ Template-Wizard integration: [red]FAILED - {e}[/red]")
        tests.append(False)
    
    passed = sum(tests)
    failed = len(tests) - passed
    console.print(f"\n[bold]Integration Results:[/bold] {passed}/{len(tests)} passed")
    
    return passed, failed


def main():
    """Run all tests"""
    console.print(Panel(
        "[bold cyan]🧪 Rocket CLI - Phase 1 Enhancement Tests[/bold cyan]\n\n"
        "Testing:\n"
        "  • Error Handler (Smart error messages)\n"
        "  • Project Wizard (Interactive setup)\n"
        "  • Templates System (Ready-to-use projects)\n"
        "  • Integration (All components together)",
        border_style="cyan",
        padding=(1, 2)
    ))
    
    total_passed = 0
    total_failed = 0
    
    # Run tests
    p, f = test_error_handler()
    total_passed += p
    total_failed += f
    
    p, f = test_templates_system()
    total_passed += p
    total_failed += f
    
    p, f = test_project_wizard()
    total_passed += p
    total_failed += f
    
    p, f = test_integration()
    total_passed += p
    total_failed += f
    
    # Summary
    console.print("\n" + "="*70)
    console.print(Panel(
        f"[bold]📊 TEST SUMMARY[/bold]\n\n"
        f"Total Tests: {total_passed + total_failed}\n"
        f"[green]✅ Passed: {total_passed}[/green]\n"
        f"[red]❌ Failed: {total_failed}[/red]\n\n"
        f"Success Rate: {total_passed / (total_passed + total_failed) * 100:.1f}%",
        border_style="green" if total_failed == 0 else "yellow",
        padding=(1, 2)
    ))
    
    if total_failed == 0:
        console.print("\n[bold green]🎉 All tests passed! Phase 1 enhancements are working![/bold green]")
        console.print("\n[bold]Ready to use:[/bold]")
        console.print("  • [cyan]rocket start[/cyan] - Interactive project wizard")
        console.print("  • [cyan]rocket templates[/cyan] - Browse project templates")
        console.print("  • Error messages are now beginner-friendly!")
    else:
        console.print(f"\n[yellow]⚠️  {total_failed} tests failed. Review the output above.[/yellow]")
    
    return total_failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
