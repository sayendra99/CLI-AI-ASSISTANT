"""
Automatic mode selection based on user intent.

Uses LLM to classify user prompt and select appropriate mode.
"""

import asyncio
from typing import Optional

from Rocket.LLM.Client import GeminiClient
from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)


class ModeSelector:
    """
    Automatically select the best mode for a user request.
    
    Uses LLM to analyze user intent and choose appropriate mode.
    """
    
    # Default mode if selection fails
    DEFAULT_MODE = "READ"
    
    # Valid mode names
    VALID_MODES = ["READ", "DEBUG", "THINK", "AGENT", "ENHANCE", "ANALYZE"]
    
    def __init__(self, llm_client: Optional[GeminiClient] = None):
        """
        Initialize mode selector.
        
        Args:
            llm_client: LLM client for classification (uses default if None)
        """
        self.llm = llm_client or GeminiClient(temperature=0.2)  # Low temp for classification
    
    async def select_mode(self, user_prompt: str) -> str:
        """
        Select appropriate mode based on user prompt.
        
        Args:
            user_prompt: User's request/question
            
        Returns:
            Mode name (READ, DEBUG, THINK, AGENT, ENHANCE, ANALYZE)
            
        Examples:
            "What does this code do?" → "READ"
            "Fix the login bug" → "DEBUG"
            "Add authentication" → "AGENT"
            "How should I architect this?" → "THINK"
        """
        logger.debug(f"Selecting mode for: {user_prompt[:50]}...")
        
        classification_prompt = f"""Analyze this user request and select the BEST mode:

User request: "{user_prompt}"

Available modes:
- READ: Understanding/explaining existing code (no changes)
- DEBUG: Fixing a specific bug or error
- THINK: Planning/designing architecture (no code)
- AGENT: Implementing new features (multi-step, complex)
- ENHANCE: Improving/optimizing existing code
- ANALYZE: Deep analysis of code quality/issues (no changes)

Selection criteria:
- READ: Questions about code, "what does", "explain", "show me"
- DEBUG: "fix bug", "error", "not working", "failing"
- THINK: "how should I", "plan", "design", "architect"
- AGENT: "add", "implement", "create feature", multi-step tasks
- ENHANCE: "optimize", "improve", "refactor", "make better"
- ANALYZE: "find issues", "check quality", "security audit"

Output ONLY the mode name (READ, DEBUG, THINK, AGENT, ENHANCE, ANALYZE)
No explanation, just the mode name."""
        
        try:
            response = await self.llm.generate(
                prompt=classification_prompt,
                max_output_tokens=10
            )
            
            mode = response.text.strip().upper()
            
            # Validate mode
            if mode not in self.VALID_MODES:
                logger.warning(f"Invalid mode '{mode}', using default: {self.DEFAULT_MODE}")
                mode = self.DEFAULT_MODE
            
            logger.info(f"Selected mode: {mode}")
            return mode
            
        except Exception as e:
            logger.error(f"Mode selection failed: {e}, using default: {self.DEFAULT_MODE}")
            return self.DEFAULT_MODE
    
    def select_mode_sync(self, user_prompt: str) -> str:
        """
        Synchronous wrapper for select_mode.
        
        Args:
            user_prompt: User's request
            
        Returns:
            Mode name
        """
        return asyncio.run(self.select_mode(user_prompt))
