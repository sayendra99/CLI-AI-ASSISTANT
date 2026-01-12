"""
READ mode - Analyze code without making changes.

Purpose: Understand existing code, explain functionality.
Characteristics: Read-only, no modifications, no git operations.
"""

from Rocket.MODES.Base import BaseMode, ModeConfig


class ReadMode(BaseMode):
    """
    READ mode for code analysis and explanation.
    
    Use cases:
    - "What does this code do?"
    - "Explain the authentication flow"
    - "Find all API endpoints"
    
    Characteristics:
    - Read-only tools (can't edit)
    - Low temperature (precise)
    - Short responses
    - No git branch creation
    """
    
    _config = ModeConfig(
        name="READ",
        description="Analyze and explain code without making changes",
        temperature=0.3,  # Precise, factual
        max_tokens=2000,  # Concise explanations
        tools_allowed=[
            "read_file",
            "search_files",
            "list_files",
            "grep_search",
            "semantic_search",
            "get_errors",
        ],
        requires_git_branch=False,  # No modifications
        system_prompt="""You are a code analysis expert specializing in explaining code.

Your role:
- Read and understand code structure
- Explain functionality in simple terms
- Identify key components and patterns
- Provide clear, concise explanations

Guidelines:
- DO NOT suggest modifications
- DO NOT write new code
- Focus on understanding existing code
- Use clear, beginner-friendly language
- Highlight important patterns and best practices

When analyzing code:
1. Identify the main purpose
2. Explain key functions/classes
3. Note any patterns or design choices
4. Point out dependencies and interactions
""",
        icon="📖"
    )
    
    @property
    def config(self) -> ModeConfig:
        """Get READ mode configuration."""
        return self._config
