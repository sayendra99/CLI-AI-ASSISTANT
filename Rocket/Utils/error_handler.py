"""
Intelligent Error Handler for Rocket CLI

Transforms technical errors into plain English with actionable fixes.
Teaches users while helping them solve problems.
"""

import re
import sys
from typing import Dict, List, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


class ErrorHandler:
    """Intelligent error handler that explains errors and suggests fixes"""
    
    # Error patterns and their explanations
    ERROR_PATTERNS = {
        "ModuleNotFoundError: No module named '(.+)'": {
            "title": "Missing Library",
            "explain": lambda match: f"Your code needs '{match.group(1)}' but it's not installed.",
            "why": "This happens when you try to use a library that isn't in your project.",
            "fixes": lambda match: [
                f"Install it: pip install {match.group(1)}",
                f"Or use Rocket: rocket install {match.group(1)}",
                "Check if you're in the right folder",
            ],
            "learn_more": "https://docs.rocket-cli.dev/errors/missing-module"
        },
        
        "ImportError: cannot import name '(.+)' from '(.+)'": {
            "title": "Wrong Import",
            "explain": lambda match: f"'{match.group(2)}' doesn't have a '{match.group(1)}' to import.",
            "why": "The library exists, but the specific thing you're trying to import doesn't.",
            "fixes": lambda match: [
                f"Check the documentation for '{match.group(2)}'",
                f"Maybe it's in a different submodule?",
                "Could be a typo in the import name",
                f"rocket docs {match.group(2)} (see available exports)",
            ],
            "learn_more": "https://docs.rocket-cli.dev/errors/wrong-import"
        },
        
        "SyntaxError: invalid syntax": {
            "title": "Syntax Error",
            "explain": lambda match: "Python doesn't understand this code.",
            "why": "You have a typo or incorrect Python syntax.",
            "fixes": lambda match: [
                "Check for missing colons (:) at end of if/for/def lines",
                "Look for unclosed brackets, quotes, or parentheses",
                "Make sure indentation is consistent (use spaces, not tabs)",
                "rocket check-syntax (auto-detect common issues)",
            ],
            "learn_more": "https://docs.rocket-cli.dev/errors/syntax"
        },
        
        "IndentationError: (.+)": {
            "title": "Indentation Problem",
            "explain": lambda match: "Python is very strict about indentation (spaces at line start).",
            "why": lambda match: match.group(1),
            "fixes": lambda match: [
                "Use 4 spaces for each indentation level",
                "Don't mix tabs and spaces",
                "Make sure code inside if/for/def is indented",
                "rocket format (auto-fix indentation)",
            ],
            "learn_more": "https://docs.rocket-cli.dev/errors/indentation"
        },
        
        "NameError: name '(.+)' is not defined": {
            "title": "Unknown Variable",
            "explain": lambda match: f"Python doesn't know what '{match.group(1)}' means.",
            "why": "You're using a variable that doesn't exist or has a typo.",
            "fixes": lambda match: [
                f"Did you mean to define '{match.group(1)}' first?",
                "Check for typos in the variable name",
                "Make sure it's defined before you use it",
                f"Need to import it? rocket suggest-import {match.group(1)}",
            ],
            "learn_more": "https://docs.rocket-cli.dev/errors/name-error"
        },
        
        "TypeError: (.+)": {
            "title": "Type Mismatch",
            "explain": lambda match: f"You're using the wrong type of data: {match.group(1)}",
            "why": "Python expected one type (like a number) but got another (like text).",
            "fixes": lambda match: [
                "Check what type of data you're working with",
                "Use str() to convert to text, int() to number",
                "Print the variable to see what it actually contains",
                "rocket debug (run debugger to inspect values)",
            ],
            "learn_more": "https://docs.rocket-cli.dev/errors/type-error"
        },
        
        "AttributeError: '(.+)' object has no attribute '(.+)'": {
            "title": "Wrong Property/Method",
            "explain": lambda match: f"'{match.group(1)}' objects don't have a '{match.group(2)}' property.",
            "why": "You're trying to access something that doesn't exist on this object.",
            "fixes": lambda match: [
                f"Check the docs for '{match.group(1)}' to see available properties",
                "Could be a typo in the property name",
                "Maybe the object is None or a different type?",
                f"rocket inspect {match.group(1)} (see available properties)",
            ],
            "learn_more": "https://docs.rocket-cli.dev/errors/attribute-error"
        },
        
        "KeyError: '(.+)'": {
            "title": "Missing Dictionary Key",
            "explain": lambda match: f"The dictionary doesn't have a key named '{match.group(1)}'.",
            "why": "You're trying to access a key that doesn't exist.",
            "fixes": lambda match: [
                f"Use .get('{match.group(1)}', default) for safe access",
                "Check if the key exists first: if '{match.group(1)}' in dict:",
                "Print the dictionary to see available keys",
                "Maybe the key name has a typo?",
            ],
            "learn_more": "https://docs.rocket-cli.dev/errors/key-error"
        },
        
        "FileNotFoundError: \\[Errno 2\\] No such file or directory: '(.+)'": {
            "title": "File Not Found",
            "explain": lambda match: f"Python can't find the file '{match.group(1)}'.",
            "why": "The file doesn't exist or the path is wrong.",
            "fixes": lambda match: [
                "Check if the file exists in that location",
                "Use absolute paths: /full/path/to/file.txt",
                "Check for typos in the filename",
                f"Create the file: rocket create-file {match.group(1)}",
            ],
            "learn_more": "https://docs.rocket-cli.dev/errors/file-not-found"
        },
        
        "ConnectionError|requests\\.exceptions\\.ConnectionError": {
            "title": "Network Connection Failed",
            "explain": lambda match: "Can't connect to the server or API.",
            "why": "Network is down, server is offline, or URL is wrong.",
            "fixes": lambda match: [
                "Check your internet connection",
                "Verify the URL is correct",
                "Server might be temporarily down (try again later)",
                "Add error handling: try/except ConnectionError",
            ],
            "learn_more": "https://docs.rocket-cli.dev/errors/connection"
        },
    }
    
    @classmethod
    def explain_error(cls, error_message: str, error_type: Optional[str] = None) -> Dict:
        """
        Explain an error in plain English with actionable fixes
        
        Args:
            error_message: The error message from Python
            error_type: Optional error type (e.g., 'ModuleNotFoundError')
            
        Returns:
            Dict with explanation, fixes, and learning resources
        """
        # Try to match error patterns
        for pattern, info in cls.ERROR_PATTERNS.items():
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return {
                    "title": info["title"],
                    "explanation": info["explain"](match) if callable(info["explain"]) else info["explain"],
                    "why": info["why"](match) if callable(info["why"]) else info["why"],
                    "fixes": info["fixes"](match) if callable(info["fixes"]) else info["fixes"],
                    "learn_more": info.get("learn_more"),
                    "matched": True
                }
        
        # Generic fallback
        return {
            "title": error_type or "Error Occurred",
            "explanation": "Something went wrong in your code.",
            "why": "Python encountered an unexpected situation.",
            "fixes": [
                "Read the error message carefully",
                "Check the line number mentioned in the error",
                "Search online: Stack Overflow, Python docs",
                "rocket ask 'how to fix: " + error_message[:50] + "'",
            ],
            "learn_more": None,
            "matched": False
        }
    
    @classmethod
    def display_friendly_error(cls, error_message: str, error_type: Optional[str] = None, 
                               file_path: Optional[str] = None, line_number: Optional[int] = None):
        """
        Display a user-friendly error message with rich formatting
        
        Args:
            error_message: The error message
            error_type: Type of error
            file_path: File where error occurred
            line_number: Line number of error
        """
        explanation = cls.explain_error(error_message, error_type)
        
        # Build error display
        content = []
        
        # Location
        if file_path and line_number:
            content.append(f"📍 **Location**: {file_path}:{line_number}\n")
        
        # What happened
        content.append(f"❌ **{explanation['title']}**\n")
        content.append(f"{explanation['explanation']}\n")
        
        # Why it happened
        content.append(f"\n🤔 **Why did this happen?**")
        content.append(f"{explanation['why']}\n")
        
        # How to fix
        content.append(f"\n🔧 **How to fix it:**")
        for i, fix in enumerate(explanation['fixes'], 1):
            content.append(f"{i}. {fix}")
        
        # Learn more
        if explanation.get('learn_more'):
            content.append(f"\n📚 **Learn more**: {explanation['learn_more']}")
        
        # Display
        console.print(Panel(
            "\n".join(content),
            title="🚀 Rocket Error Helper",
            border_style="red",
            padding=(1, 2)
        ))
        
        # Offer to auto-fix if possible
        if explanation['matched']:
            console.print("\n💡 [yellow]Would you like Rocket to try fixing this? (Y/n)[/yellow]")
    
    @classmethod
    def suggest_fix(cls, error_message: str) -> Optional[str]:
        """
        Suggest an automatic fix command if available
        
        Args:
            error_message: The error message
            
        Returns:
            Command to run, or None if no automatic fix available
        """
        # Module not found -> install
        match = re.search(r"No module named '(.+)'", error_message)
        if match:
            module = match.group(1)
            return f"pip install {module}"
        
        # Syntax/formatting -> auto-format
        if "SyntaxError" in error_message or "IndentationError" in error_message:
            return "rocket format"
        
        return None


class ExceptionWrapper:
    """Context manager to wrap exceptions with friendly explanations"""
    
    def __init__(self, show_traceback: bool = False):
        self.show_traceback = show_traceback
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Get error details
            error_type = exc_type.__name__
            error_message = str(exc_val)
            
            # Try to get file and line number
            file_path = None
            line_number = None
            if exc_tb:
                file_path = exc_tb.tb_frame.f_code.co_filename
                line_number = exc_tb.tb_lineno
            
            # Display friendly error
            ErrorHandler.display_friendly_error(
                error_message, 
                error_type, 
                file_path, 
                line_number
            )
            
            # Show traceback if requested
            if self.show_traceback:
                console.print("\n[dim]Full traceback:[/dim]")
                import traceback
                traceback.print_exception(exc_type, exc_val, exc_tb)
            
            # Suggest auto-fix
            fix_cmd = ErrorHandler.suggest_fix(error_message)
            if fix_cmd:
                console.print(f"\n✨ [green]Quick fix: {fix_cmd}[/green]")
                console.print("[dim]Run this command to fix the issue[/dim]")
            
            return True  # Suppress the exception
        
        return False


# Convenience functions
def explain(error_message: str, error_type: Optional[str] = None):
    """Explain an error message"""
    ErrorHandler.display_friendly_error(error_message, error_type)


def wrap_exceptions(show_traceback: bool = False):
    """Decorator to wrap exceptions with friendly explanations"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with ExceptionWrapper(show_traceback=show_traceback):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Example usage
if __name__ == "__main__":
    # Test error explanations
    test_errors = [
        "ModuleNotFoundError: No module named 'requests'",
        "SyntaxError: invalid syntax",
        "NameError: name 'user' is not defined",
        "TypeError: can only concatenate str (not 'int') to str",
    ]
    
    for error in test_errors:
        console.print(f"\n{'='*60}")
        ErrorHandler.display_friendly_error(error)
        console.print()
