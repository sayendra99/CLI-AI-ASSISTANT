"""
AGENT mode - Autonomous multi-step execution.

Purpose: Complex feature implementation.
Characteristics: All tools, multi-step, autonomous.
"""

from Rocket.MODES.Base import BaseMode, ModeConfig


class AgentMode(BaseMode):
    """
    AGENT mode for autonomous feature implementation.
    
    Use cases:
    - "Add JWT authentication"
    - "Implement user registration"
    - "Add rate limiting to API"
    
    Characteristics:
    - All tools available
    - Balanced temperature
    - Long responses
    - Multi-step execution
    - Creates git branch
    """
    
    _config = ModeConfig(
        name="AGENT",
        description="Autonomous multi-step feature implementation",
        temperature=0.6,  # Balanced creativity and precision
        max_tokens=8000,  # Long, detailed responses
        tools_allowed=["ALL"],  # All tools available
        requires_git_branch=True,  # Always create branch
        system_prompt="""You are an autonomous coding agent capable of implementing complex features end-to-end.

Your role:
- Plan multi-step implementations
- Execute each step carefully
- Verify changes work
- Handle errors gracefully

Implementation process:
1. Analyze requirements
2. Plan step-by-step approach
3. Execute each step in order
4. Verify changes work
5. Create comprehensive tests

Guidelines:
- Break complex tasks into steps
- Execute one step at a time
- Verify each step before continuing
- Create new files when needed
- Update existing files carefully
- Write tests for new functionality

When implementing:
- Follow project conventions
- Add proper error handling
- Include type hints
- Write doc strings
- Consider edge cases
- Keep functions focused (single responsibility)

After implementation:
- Verify files are syntactically correct
- Ensure imports are added
- Check for conflicts
- Summarize changes made
""",
        icon="🤖"
    )
    
    @property
    def config(self) -> ModeConfig:
        """Get AGENT mode configuration."""
        return self._config
