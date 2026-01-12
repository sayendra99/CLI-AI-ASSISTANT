"""
THINK mode - Planning and reasoning without code changes.

Purpose: Architecture planning, design decisions.
Characteristics: No tools, pure reasoning, creative.
"""

from Rocket.MODES.Base import BaseMode, ModeConfig


class ThinkMode(BaseMode):
    """
    THINK mode for planning and architecture.
    
    Use cases:
    - "How should I add caching?"
    - "Design a microservices architecture"
    - "Plan database migration strategy"
    
    Characteristics:
    - No tools (pure reasoning)
    - High temperature (creative)
    - Long responses (detailed plans)
    - No code changes
    """
    
    _config = ModeConfig(
        name="THINK",
        description="Plan architecture and design solutions",
        temperature=0.8,  # Creative, exploratory
        max_tokens=8000,  # Long, detailed reasoning
        tools_allowed=[],  # NO TOOLS - pure thinking
        requires_git_branch=False,  # No code changes
        system_prompt="""You are a senior software architect with expertise in system design and best practices.

Your role:
- Think deeply about architectural decisions
- Consider trade-offs and alternatives
- Provide structured, actionable plans
- Anticipate challenges and risks

Planning approach:
1. Understand the problem deeply
2. Consider multiple approaches
3. Analyze trade-offs
4. Recommend best solution
5. Provide implementation plan

Guidelines:
- Think step-by-step
- Consider scalability, maintainability, performance
- Reference design patterns where appropriate
- Highlight potential pitfalls
- Be realistic about complexity

When planning:
- Break down into phases
- Identify dependencies
- Estimate complexity
- Suggest testing strategies
- Consider migration paths
""",
        icon="🧠"
    )
    
    @property
    def config(self) -> ModeConfig:
        """Get THINK mode configuration."""
        return self._config
