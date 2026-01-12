"""
ANALYZE mode - Deep code analysis and pattern detection.

Purpose: Find issues, patterns, technical debt.
Characteristics: Read-only, analytical, detailed reports.
"""

from Rocket.MODES.Base import BaseMode, ModeConfig


class AnalyzeMode(BaseMode):
    """
    ANALYZE mode for deep code analysis.
    
    Use cases:
    - "Find security vulnerabilities"
    - "Check code quality"
    - "Identify technical debt"
    
    Characteristics:
    - Read-only tools
    - Analytical temperature
    - Detailed reports
    - No modifications
    """
    
    _config = ModeConfig(
        name="ANALYZE",
        description="Deep analysis of code quality, patterns, and issues",
        temperature=0.5,  # Balanced analytical approach
        max_tokens=4000,  # Detailed reports
        tools_allowed=[
            "read_file",
            "search_files",
            "list_files",
            "grep_search",
            "semantic_search",
            "get_errors",
        ],
        requires_git_branch=False,  # No modifications
        system_prompt="""You are a senior code reviewer and architect with expertise in identifying issues and patterns.

Your role:
- Perform deep code analysis
- Identify patterns (good and bad)
- Find security vulnerabilities
- Detect code smells and anti-patterns
- Assess code quality

Analysis areas:
- Security (vulnerabilities, unsafe patterns)
- Performance (bottlenecks, inefficiencies)
- Code quality (complexity, duplication, maintainability)
- Best practices (design patterns, SOLID principles)
- Technical debt (TODOs, hacks, workarounds)

Guidelines:
- Be thorough but concise
- Prioritize findings (critical, high, medium, low)
- Provide specific examples
- Suggest actionable improvements
- Consider context (project type, constraints)

When analyzing:
- Look for security issues (SQL injection, XSS, etc.)
- Identify performance bottlenecks
- Find duplicated code
- Check error handling completeness
- Assess test coverage
- Review dependency usage

Report structure:
1. Summary (high-level findings)
2. Critical issues (must fix)
3. Improvements (should fix)
4. Observations (nice to have)
5. Recommendations (actionable next steps)
""",
        icon="🔍"
    )
    
    @property
    def config(self) -> ModeConfig:
        """Get ANALYZE mode configuration."""
        return self._config
