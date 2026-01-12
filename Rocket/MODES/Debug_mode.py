"""
DEBUG mode - Find and fix bugs in code.

Purpose: Diagnose issues, analyze errors, suggest fixes.
Characteristics: Read files, run tests, analyze errors, can suggest fixes.
"""

from Rocket.MODES.Base import BaseMode, ModeConfig


class DebugMode(BaseMode):
    """
    DEBUG mode for finding and fixing bugs.
    
    Use cases:
    - "Why is this function failing?"
    - "Fix this error message"
    - "Debug the authentication issue"
    
    Characteristics:
    - Read-only + error analysis tools
    - Medium temperature (analytical)
    - Can suggest fixes but not implement them
    - No git branch creation
    """
    
    _config = ModeConfig(
        name="DEBUG",
        description="Find and fix bugs in code",
        temperature=0.4,  # Analytical but creative
        max_tokens=3000,  # Detailed debugging explanations
        tools_allowed=[
            "read_file",
            "search_files",
            "list_files",
            "grep_search",
            "semantic_search",
            "get_errors",
            "run_in_terminal",
            "get_terminal_output",
        ],
        requires_git_branch=False,  # No modifications
        system_prompt="""You are a debugging expert specializing in finding and fixing code issues.

Your role:
- Analyze error messages and stack traces
- Identify root causes of bugs
- Suggest specific fixes with explanations
- Test hypotheses by running code

Guidelines:
- Focus on understanding the problem first
- Analyze error messages carefully
- Trace execution flow to find issues
- Suggest precise fixes with rationale
- Consider edge cases and potential side effects

When debugging:
1. Understand the expected behavior
2. Identify the actual behavior
3. Locate the source of the problem
4. Suggest a fix with explanation
5. Consider testing the fix
""",
        icon="🐛"
    )
    
    @property
    def config(self) -> ModeConfig:
        """Get DEBUG mode configuration."""
        return self._config
