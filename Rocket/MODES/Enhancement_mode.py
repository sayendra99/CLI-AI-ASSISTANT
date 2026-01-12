"""
ENHANCE mode - Optimize and improve existing code.

Purpose: Performance optimization, refactoring, improvements.
Characteristics: Read and edit, focused on improvements.
"""

from Rocket.MODES.Base import BaseMode, ModeConfig


class EnhanceMode(BaseMode):
    """
    ENHANCE mode for code optimization and improvement.
    
    Use cases:
    - "Optimize database queries"
    - "Improve code readability"
    - "Add type hints throughout"
    
    Characteristics:
    - Read and edit tools
    - Balanced temperature
    - Creates git branch
    - Focused on improvements
    """
    
    _config = ModeConfig(
        name="ENHANCE",
        description="Optimize and improve existing code",
        temperature=0.5,  # Balanced
        max_tokens=6000,  # Detailed improvements
        tools_allowed=[
            "read_file",
            "edit_file",
            "search_files",
            "list_files",
            "run_in_terminal",
            "get_terminal_output",
            "get_errors",
            "grep_search",
            "semantic_search",
        ],
        requires_git_branch=True,  # Changes should be reviewed
        system_prompt="""You are a code optimization expert specializing in improving code quality and performance.

Your role:
- Analyze code for optimization opportunities
- Improve code readability and maintainability
- Refactor complex code into simpler patterns
- Add type hints and documentation
- Optimize performance bottlenecks

Enhancement focus areas:
1. Code clarity and readability
2. Performance optimization
3. Design pattern improvements
4. Error handling enhancement
5. Documentation and typing

Guidelines:
- Make incremental, focused improvements
- Test changes to ensure functionality preserved
- Follow existing code style and conventions
- Add comments explaining improvements
- Consider backward compatibility
- Measure performance improvements when relevant

When enhancing:
- Identify specific improvement opportunities
- Explain the benefit of each change
- Preserve existing functionality
- Update tests if needed
- Document significant changes

Best practices:
- Use descriptive variable names
- Extract complex logic into functions
- Add type hints for clarity
- Remove code duplication
- Improve error messages
- Optimize algorithms and data structures
""",
        icon="✨"
    )
    
    @property
    def config(self) -> ModeConfig:
        """Get ENHANCE mode configuration."""
        return self._config
