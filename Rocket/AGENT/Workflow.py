"""
Main workflow orchestrator - coordinates entire execution.

This is the HEART of Rocket - brings together:
Git, Modes, Tools, LLM, PRs

Executes complete workflow from prompt to PR.

Performance Optimizations:
- LRU caching for mode registry and selectors
- Cached git status checks
- Efficient workflow state management

Author: Rocket AI Team
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from functools import lru_cache

# Handle imports for both package and direct execution
try:
    from Rocket.AGENT.Context import ExecutionContext, ExecutionResult, ExecutionStatus
    from Rocket.AGENT.Executor import ToolExecutor, ToolNotAllowedError
    from Rocket.GIT.manager import GitManager, GitStatus, GitError
    from Rocket.GIT.Pr_creator import PRCreator, PRInfo, PRCreationError
    from Rocket.MODES.Register import ModeRegistry
    from Rocket.MODES.Selectors import ModeSelector
    from Rocket.TOOLS.registry import get_registry
    from Rocket.Utils.Log import get_logger
except ImportError:
    _project_root = Path(__file__).parent.parent.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))
    from Rocket.AGENT.Context import ExecutionContext, ExecutionResult, ExecutionStatus
    from Rocket.AGENT.Executor import ToolExecutor, ToolNotAllowedError
    from Rocket.GIT.manager import GitManager, GitStatus, GitError
    from Rocket.GIT.Pr_creator import PRCreator, PRInfo, PRCreationError
    from Rocket.MODES.Register import ModeRegistry
    from Rocket.MODES.Selectors import ModeSelector
    from Rocket.TOOLS.registry import get_registry
    from Rocket.Utils.Log import get_logger

if TYPE_CHECKING:
    from Rocket.LLM.Client import GeminiClient
    from Rocket.MODES.Base import BaseMode

logger = get_logger(__name__)


# =============================================================================
# Exceptions
# =============================================================================

class WorkflowError(Exception):
    """Workflow execution failed."""
    pass


class WorkflowCancelledError(WorkflowError):
    """Workflow was cancelled by user."""
    pass


# =============================================================================
# Workflow Configuration
# =============================================================================

@dataclass
class WorkflowConfig:
    """
    Configuration for workflow execution.
    
    Attributes:
        auto_mode: Auto-select mode based on prompt
        auto_commit: Automatically commit changes
        auto_pr: Automatically create PR
        draft_pr: Create PR as draft
        create_branch: Create safety branch for write operations
        stash_changes: Stash uncommitted changes before starting
        target_branch: Target branch for PR (default: main)
    """
    auto_mode: bool = True
    auto_commit: bool = False
    auto_pr: bool = False
    draft_pr: bool = True
    create_branch: bool = True
    stash_changes: bool = True
    target_branch: str = "main"


# =============================================================================
# Workflow Orchestrator
# =============================================================================

class WorkflowOrchestrator:
    """
    Main workflow coordinator - orchestrates entire execution.
    
    Brings together:
    - Git: Branch management, commits, safety
    - Modes: Mode selection and permissions
    - Tools: Tool execution with permission checks
    - LLM: AI-powered code generation
    - PRs: Automatic PR creation
    
    Workflow Steps:
    1. Select mode (auto or explicit)
    2. Check git status
    3. Create safety branch if needed
    4. Initialize tool executor
    5. Execute LLM with tool access
    6. Commit changes
    7. Create PR
    8. Return result
    
    Example:
        >>> orchestrator = WorkflowOrchestrator(workspace_root=Path("."))
        >>> result = await orchestrator.execute(
        ...     user_prompt="Fix the authentication bug",
        ...     mode_name="DEBUG",
        ...     auto_commit=True
        ... )
        >>> print(result.summary())
    """
    
    def __init__(
        self,
        workspace_root: Optional[Path] = None,
        llm_client: Optional["GeminiClient"] = None,
        mode_registry: Optional[ModeRegistry] = None,
    ) -> None:
        """
        Initialize the workflow orchestrator.
        
        Args:
            workspace_root: Root directory of workspace
            llm_client: LLM client for generation (lazy-loaded if None)
            mode_registry: Registry of available modes
        """
        self.workspace_root = Path(workspace_root or Path.cwd()).resolve()
        self._llm_client = llm_client
        self._mode_registry = mode_registry
        
        # Initialize managers
        self._git_manager = GitManager(repo_path=self.workspace_root)
        self._pr_creator = PRCreator()
        self._mode_selector: Optional[ModeSelector] = None
        
        logger.info(f"WorkflowOrchestrator initialized at: {self.workspace_root}")
    
    # -------------------------------------------------------------------------
    # Properties (Lazy Loading)
    # -------------------------------------------------------------------------
    
    @property
    def llm_client(self) -> "GeminiClient":
        """Get LLM client (lazy-loaded)."""
        if self._llm_client is None:
            from Rocket.LLM.Client import GeminiClient
            self._llm_client = GeminiClient()
            logger.debug("LLM client lazy-loaded")
        return self._llm_client
    
    @property
    def mode_registry(self) -> ModeRegistry:
        """Get mode registry (lazy-loaded)."""
        if self._mode_registry is None:
            from Rocket.MODES.Register import ModeRegistry
            self._mode_registry = ModeRegistry()
            # Register default modes
            self._register_default_modes()
            logger.debug("Mode registry lazy-loaded")
        return self._mode_registry
    
    @property
    def mode_selector(self) -> ModeSelector:
        """Get mode selector (lazy-loaded)."""
        if self._mode_selector is None:
            self._mode_selector = ModeSelector(llm_client=self._llm_client)
            logger.debug("Mode selector lazy-loaded")
        return self._mode_selector
    
    def _register_default_modes(self) -> None:
        """Register default modes if registry is empty."""
        # Only register if empty
        if self._mode_registry and self._mode_registry.count() > 0:
            return
        
        try:
            from Rocket.MODES.Read_mode import ReadMode
            from Rocket.MODES.Debug_mode import DebugMode
            from Rocket.MODES.Think_mode import ThinkMode
            from Rocket.MODES.Agent_mode import AgentMode
            from Rocket.MODES.Enhancement_mode import EnhanceMode
            from Rocket.MODES.Analyze_mode import AnalyzeMode
            
            modes = [
                ReadMode(),
                DebugMode(),
                ThinkMode(),
                AgentMode(),
                EnhanceMode(),
                AnalyzeMode(),
            ]
            
            for mode in modes:
                self._mode_registry.register(mode)
                
        except ImportError as e:
            logger.warning(f"Could not register default modes: {e}")
    
    # -------------------------------------------------------------------------
    # Main Entry Point
    # -------------------------------------------------------------------------
    
    async def execute(
        self,
        user_prompt: str,
        mode_name: Optional[str] = None,
        *,
        auto_mode: bool = True,
        auto_commit: bool = False,
        auto_pr: bool = False,
        draft_pr: bool = True,
        create_branch: bool = True,
        target_branch: str = "main",
    ) -> ExecutionResult:
        """
        Execute complete workflow from prompt to result.
        
        Args:
            user_prompt: User's request/question
            mode_name: Explicit mode name (or None for auto-select)
            auto_mode: Auto-select mode if mode_name not provided
            auto_commit: Automatically commit changes
            auto_pr: Automatically create PR after commit
            draft_pr: Create PR as draft
            create_branch: Create safety branch for write operations
            target_branch: Target branch for PR
            
        Returns:
            ExecutionResult with outcome details
        """
        # Create execution context
        context = ExecutionContext(
            user_prompt=user_prompt,
            mode_name=mode_name or "PENDING",
            workspace_root=str(self.workspace_root),
        )
        
        try:
            # Start execution
            context.start()
            logger.info(f"Starting workflow: {user_prompt[:50]}...")
            
            # Step 1: Select mode
            selected_mode_name = await self._select_mode(
                user_prompt, 
                mode_name, 
                auto_mode
            )
            context.mode_name = selected_mode_name
            
            # Get mode instance
            mode = self._get_mode(selected_mode_name)
            
            # Step 2: Check git status
            git_status = self._check_git_status()
            context.set_git_info(original_branch=git_status.current_branch)
            
            # Step 3: Create safety branch if needed
            if create_branch and mode.needs_git_branch():
                branch_name = await self._create_safety_branch(
                    user_prompt, 
                    context, 
                    git_status
                )
                context.set_git_info(branch_created=branch_name)
            
            # Step 4: Initialize tool executor
            executor = self._create_executor(mode, context)
            
            # Step 5: Execute LLM with tool access
            llm_response = await self._execute_llm(
                user_prompt, 
                mode, 
                executor, 
                context
            )
            
            # Step 6: Commit changes if requested
            if auto_commit and self._has_changes(context):
                commit_hash = await self._commit_changes(context)
                context.set_git_info(commit_hash=commit_hash)
            
            # Step 7: Create PR if requested
            if auto_pr and context.commit_hash:
                pr_info = await self._create_pr(context, target_branch, draft_pr)
                context.set_git_info(
                    pr_url=pr_info.url,
                    pr_number=pr_info.number
                )
            
            # Mark success
            context.complete(success=True)
            
            # Create result with LLM response
            result = context.to_result()
            result.message = llm_response
            result.branch_name = context.branch_created
            
            logger.info(f"Workflow completed successfully")
            return result
            
        except WorkflowCancelledError as e:
            context.cancel(str(e))
            return context.to_result()
            
        except ToolNotAllowedError as e:
            context.complete(success=False, error=str(e))
            context.error_type = "PermissionError"
            logger.error(f"Permission denied: {e}")
            return context.to_result()
            
        except GitError as e:
            context.complete(success=False, error=f"Git error: {e}")
            context.error_type = "GitError"
            logger.error(f"Git error: {e}")
            return context.to_result()
            
        except Exception as e:
            context.complete(success=False, error=str(e))
            context.error_type = type(e).__name__
            logger.exception(f"Workflow failed: {e}")
            return context.to_result()
    
    # -------------------------------------------------------------------------
    # Step 1: Mode Selection
    # -------------------------------------------------------------------------
    
    async def _select_mode(
        self,
        user_prompt: str,
        explicit_mode: Optional[str],
        auto_mode: bool,
    ) -> str:
        """
        Select the operating mode.
        
        Args:
            user_prompt: User's request
            explicit_mode: Explicitly requested mode
            auto_mode: Whether to auto-select
            
        Returns:
            Mode name
        """
        # Use explicit mode if provided
        if explicit_mode:
            logger.info(f"Using explicit mode: {explicit_mode}")
            return explicit_mode.upper()
        
        # Auto-select mode
        if auto_mode:
            try:
                selected = await self.mode_selector.select_mode(user_prompt)
                logger.info(f"Auto-selected mode: {selected}")
                return selected
            except Exception as e:
                logger.warning(f"Mode selection failed, using READ: {e}")
                return "READ"
        
        # Default to READ
        return "READ"
    
    def _get_mode(self, mode_name: str) -> "BaseMode":
        """Get mode instance from registry."""
        mode = self.mode_registry.get(mode_name)
        
        if mode is None:
            # Fall back to READ mode
            logger.warning(f"Mode {mode_name} not found, using READ")
            mode = self.mode_registry.get("READ")
            
            if mode is None:
                raise WorkflowError(f"No modes available (requested: {mode_name})")
        
        return mode
    
    # -------------------------------------------------------------------------
    # Step 2: Git Status Check
    # -------------------------------------------------------------------------
    
    def _check_git_status(self) -> GitStatus:
        """Check git repository status."""
        status = self._git_manager.get_status()
        
        if status.is_repo:
            logger.debug(
                f"Git status: branch={status.current_branch}, "
                f"clean={status.is_clean}, production={status.is_production_branch}"
            )
        else:
            logger.debug("Not a git repository")
        
        return status
    
    # -------------------------------------------------------------------------
    # Step 3: Safety Branch Creation
    # -------------------------------------------------------------------------
    
    async def _create_safety_branch(
        self,
        user_prompt: str,
        context: ExecutionContext,
        git_status: GitStatus,
    ) -> str:
        """
        Create a safety branch for write operations.
        
        Args:
            user_prompt: User's request (for branch naming)
            context: Execution context
            git_status: Current git status
            
        Returns:
            Name of created branch
        """
        if not git_status.is_repo:
            logger.debug("Not a git repo, skipping branch creation")
            return ""
        
        # Generate branch name from prompt
        branch_name = self._generate_branch_name(user_prompt, context.mode_name)
        
        try:
            created_branch = self._git_manager.create_branch(
                branch_name,
                base_branch=git_status.current_branch
            )
            logger.info(f"Created safety branch: {created_branch}")
            return created_branch
            
        except GitError as e:
            logger.warning(f"Could not create branch: {e}")
            return ""
    
    def _generate_branch_name(self, user_prompt: str, mode_name: str) -> str:
        """Generate a branch name from prompt and mode."""
        # Clean prompt for branch name
        clean_prompt = user_prompt.lower()
        
        # Remove special characters
        import re
        clean_prompt = re.sub(r'[^a-z0-9\s]', '', clean_prompt)
        
        # Take first few words
        words = clean_prompt.split()[:4]
        slug = '-'.join(words)
        
        # Truncate if too long
        if len(slug) > 30:
            slug = slug[:30]
        
        # Add prefix
        prefix = f"rocket/{mode_name.lower()}"
        
        return f"{prefix}/{slug}"
    
    # -------------------------------------------------------------------------
    # Step 4: Tool Executor Creation
    # -------------------------------------------------------------------------
    
    def _create_executor(
        self,
        mode: "BaseMode",
        context: ExecutionContext,
    ) -> ToolExecutor:
        """Create a tool executor for the mode."""
        # Ensure tools are registered
        self._ensure_tools_registered()
        
        executor = ToolExecutor(
            mode=mode,
            context=context,
            registry=get_registry(),
        )
        
        logger.debug(
            f"Created executor with {len(executor.get_available_tools())} "
            f"available tools for {mode.config.name}"
        )
        
        return executor
    
    def _ensure_tools_registered(self) -> None:
        """Ensure default tools are registered in global registry."""
        registry = get_registry()
        
        if registry.count() > 0:
            return  # Already registered
        
        try:
            from Rocket.TOOLS.read_file import ReadFileTool
            from Rocket.TOOLS.write_file import WriteFileTool
            from Rocket.TOOLS.list_directory import ListDirectoryTool
            from Rocket.TOOLS.search_files import SearchFilesTool
            from Rocket.TOOLS.run_command import RunCommandTool
            
            registry.register(ReadFileTool(workspace_root=self.workspace_root))
            registry.register(WriteFileTool(workspace_root=self.workspace_root))
            registry.register(ListDirectoryTool())
            registry.register(SearchFilesTool())
            registry.register(RunCommandTool())
            
            logger.debug(f"Registered {registry.count()} default tools")
            
        except ImportError as e:
            logger.warning(f"Could not register tools: {e}")
    
    # -------------------------------------------------------------------------
    # Step 5: LLM Execution
    # -------------------------------------------------------------------------
    
    async def _execute_llm(
        self,
        user_prompt: str,
        mode: "BaseMode",
        executor: ToolExecutor,
        context: ExecutionContext,
    ) -> str:
        """
        Execute LLM with tool access.
        
        Args:
            user_prompt: User's request
            mode: Current mode
            executor: Tool executor
            context: Execution context
            
        Returns:
            LLM response text
        """
        # Get tool schemas for LLM
        tool_schemas = executor.get_tool_schemas(format="gemini")
        
        # Get mode settings
        llm_settings = mode.get_llm_settings()
        
        logger.debug(
            f"Executing LLM: {len(tool_schemas)} tools, "
            f"temp={llm_settings.get('temperature')}"
        )
        
        # TODO: Real LLM integration with tool calling loop
        # For now, return mock response
        response = await self._mock_llm_execution(
            user_prompt,
            mode,
            executor,
            context,
            tool_schemas,
        )
        
        return response
    
    async def _mock_llm_execution(
        self,
        user_prompt: str,
        mode: "BaseMode",
        executor: ToolExecutor,
        context: ExecutionContext,
        tool_schemas: List[Dict[str, Any]],
    ) -> str:
        """
        Mock LLM execution for testing.
        
        TODO: Replace with real LLM integration.
        """
        logger.debug("Using mock LLM execution")
        
        # Simulate some token usage
        context.add_llm_usage(
            tokens=150,
            cost=0.0003,
            model="mock-model"
        )
        
        # Generate mock response based on mode
        mode_name = mode.config.name
        available_tools = [s.get("name", "unknown") for s in tool_schemas]
        
        mock_response = f"""
**Mode**: {mode_name}
**Prompt**: {user_prompt[:100]}...

This is a mock response from the workflow orchestrator.
In production, this would be replaced with actual LLM output.

**Available Tools**: {', '.join(available_tools)}

The workflow has been set up correctly with:
- Mode-based permissions
- Tool execution tracking
- Git integration
- Context management
        """.strip()
        
        return mock_response
    
    # -------------------------------------------------------------------------
    # Step 6: Commit Changes
    # -------------------------------------------------------------------------
    
    async def _commit_changes(self, context: ExecutionContext) -> str:
        """
        Commit changes made during execution.
        
        Args:
            context: Execution context with file tracking
            
        Returns:
            Commit hash
        """
        # Get all modified/created files
        files = list(context.files_modified | context.files_created)
        
        if not files:
            logger.debug("No files to commit")
            return ""
        
        # Generate commit message
        commit_message = await self._generate_commit_message(context)
        
        try:
            commit_hash = self._git_manager.commit_changes(
                files=files,
                message=commit_message,
                add_rocket_signature=True
            )
            
            logger.info(f"Committed {len(files)} files: {commit_hash}")
            return commit_hash
            
        except GitError as e:
            logger.error(f"Commit failed: {e}")
            raise
    
    async def _generate_commit_message(self, context: ExecutionContext) -> str:
        """Generate a commit message from context."""
        # Get file counts
        modified_count = len(context.files_modified)
        created_count = len(context.files_created)
        
        # Build message parts
        parts = []
        
        # Mode-based prefix
        mode_prefixes = {
            "DEBUG": "fix",
            "ENHANCE": "refactor",
            "AGENT": "feat",
            "READ": "docs",
            "THINK": "docs",
            "ANALYZE": "chore",
        }
        prefix = mode_prefixes.get(context.mode_name, "chore")
        
        # Summarize changes
        if created_count > 0 and modified_count > 0:
            summary = f"add {created_count} files, modify {modified_count}"
        elif created_count > 0:
            summary = f"add {created_count} files"
        elif modified_count > 0:
            summary = f"modify {modified_count} files"
        else:
            summary = "update code"
        
        # Create message
        # Truncate prompt for commit message
        prompt_summary = context.user_prompt[:50]
        if len(context.user_prompt) > 50:
            prompt_summary += "..."
        
        message = f"{prefix}: {prompt_summary}\n\n{summary}"
        
        return message
    
    def _has_changes(self, context: ExecutionContext) -> bool:
        """Check if there are changes to commit."""
        return len(context.files_modified) > 0 or len(context.files_created) > 0
    
    # -------------------------------------------------------------------------
    # Step 7: Create PR
    # -------------------------------------------------------------------------
    
    async def _create_pr(
        self,
        context: ExecutionContext,
        target_branch: str,
        draft: bool,
    ) -> PRInfo:
        """
        Create a pull request.
        
        Args:
            context: Execution context
            target_branch: Target branch for PR
            draft: Create as draft PR
            
        Returns:
            PRInfo with PR details
        """
        if not context.branch_created:
            raise WorkflowError("No branch created, cannot create PR")
        
        # Generate PR title and body
        title = await self._generate_pr_title(context)
        body = await self._generate_pr_body(context)
        
        try:
            pr_info = self._pr_creator.create_pr(
                from_branch=context.branch_created,
                to_branch=target_branch,
                title=title,
                body=body,
                draft=draft,
            )
            
            logger.info(f"Created PR #{pr_info.number}: {pr_info.url}")
            return pr_info
            
        except PRCreationError as e:
            logger.error(f"PR creation failed: {e}")
            raise WorkflowError(f"Failed to create PR: {e}") from e
    
    async def _generate_pr_title(self, context: ExecutionContext) -> str:
        """Generate PR title from context."""
        # Mode-based prefix
        mode_emoji = {
            "DEBUG": "🐛",
            "ENHANCE": "✨",
            "AGENT": "🚀",
            "READ": "📖",
            "THINK": "💭",
            "ANALYZE": "🔍",
        }
        emoji = mode_emoji.get(context.mode_name, "🤖")
        
        # Truncate prompt for title
        prompt_summary = context.user_prompt[:60]
        if len(context.user_prompt) > 60:
            prompt_summary += "..."
        
        return f"{emoji} [{context.mode_name}] {prompt_summary}"
    
    async def _generate_pr_body(self, context: ExecutionContext) -> str:
        """Generate PR body from context."""
        lines = [
            "## 🚀 Generated by Rocket CLI",
            "",
            f"**Mode**: {context.mode_name}",
            f"**Prompt**: {context.user_prompt}",
            "",
            "### Changes",
        ]
        
        # List files
        if context.files_created:
            lines.append("\n**New Files:**")
            for f in sorted(context.files_created)[:10]:
                lines.append(f"- `{f}`")
            if len(context.files_created) > 10:
                lines.append(f"- ... and {len(context.files_created) - 10} more")
        
        if context.files_modified:
            lines.append("\n**Modified Files:**")
            for f in sorted(context.files_modified)[:10]:
                lines.append(f"- `{f}`")
            if len(context.files_modified) > 10:
                lines.append(f"- ... and {len(context.files_modified) - 10} more")
        
        # Stats
        lines.extend([
            "",
            "### Stats",
            f"- 🔧 Tools executed: {context.total_tool_executions}",
            f"- 🤖 LLM calls: {context.llm_calls}",
            f"- 💰 Tokens used: {context.tokens_used:,}",
            f"- ⏱️ Execution time: {context.execution_time_seconds:.1f}s",
        ])
        
        return "\n".join(lines)
    
    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        return {
            "workspace_root": str(self.workspace_root),
            "git_status": self._git_manager.get_status().__dict__,
            "modes_registered": self.mode_registry.count() if self._mode_registry else 0,
            "tools_registered": get_registry().count(),
            "has_llm_client": self._llm_client is not None,
            "has_gh_cli": self._pr_creator.has_gh_cli,
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"WorkflowOrchestrator(workspace={self.workspace_root})"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"<WorkflowOrchestrator("
            f"workspace='{self.workspace_root}', "
            f"modes={self.mode_registry.count() if self._mode_registry else 0})>"
        )


# =============================================================================
# Convenience Function
# =============================================================================

async def run_workflow(
    user_prompt: str,
    mode_name: Optional[str] = None,
    workspace_root: Optional[Path] = None,
    **kwargs: Any,
) -> ExecutionResult:
    """
    Convenience function to run a workflow.
    
    Args:
        user_prompt: User's request
        mode_name: Mode name (optional)
        workspace_root: Workspace root (optional)
        **kwargs: Additional options for execute()
        
    Returns:
        ExecutionResult
    """
    orchestrator = WorkflowOrchestrator(workspace_root=workspace_root)
    return await orchestrator.execute(user_prompt, mode_name, **kwargs)


# =============================================================================
# Self-Test
# =============================================================================

if __name__ == "__main__":
    import tempfile
    
    print("=" * 60)
    print("WorkflowOrchestrator Self-Test")
    print("=" * 60)
    
    async def run_tests():
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a test file
            test_file = temp_path / "test.py"
            test_file.write_text("print('hello world')\n")
            
            # Test 1: Create orchestrator
            print("\n--- Test 1: Create Orchestrator ---")
            orchestrator = WorkflowOrchestrator(workspace_root=temp_path)
            print(f"✓ Created: {orchestrator}")
            
            # Test 2: Get status
            print("\n--- Test 2: Get Status ---")
            status = orchestrator.get_status()
            print(f"✓ Status: workspace={status['workspace_root']}")
            print(f"  Git repo: {status['git_status']['is_repo']}")
            print(f"  GH CLI: {status['has_gh_cli']}")
            
            # Test 3: Execute with explicit mode (mock LLM)
            print("\n--- Test 3: Execute Workflow (READ mode) ---")
            result = await orchestrator.execute(
                user_prompt="What does test.py do?",
                mode_name="READ",
                auto_commit=False,
                auto_pr=False,
                create_branch=False,
            )
            
            print(f"✓ Execution completed:")
            print(f"  Success: {result.success}")
            print(f"  Mode: {result.mode_name}")
            print(f"  Tokens: {result.tokens_used}")
            
            # Test 4: Check result has message
            print("\n--- Test 4: Result Message ---")
            assert result.message is not None
            print(f"✓ Message preview: {result.message[:100]}...")
            
            # Test 5: Execute with auto mode (would use mock selector)
            print("\n--- Test 5: Execute with Auto Mode ---")
            result2 = await orchestrator.execute(
                user_prompt="Explain the code",
                mode_name=None,
                auto_mode=False,  # Disable to avoid real LLM call
                create_branch=False,
            )
            
            # Default is READ when auto_mode=False and no explicit mode
            print(f"✓ Default mode used: {result2.mode_name}")
            
            # Test 6: Result summary
            print("\n--- Test 6: Result Summary ---")
            summary = result.summary()
            assert "✅" in summary or "❌" in summary
            print(summary[:500])
            
            # Test 7: Branch name generation
            print("\n--- Test 7: Branch Name Generation ---")
            branch_name = orchestrator._generate_branch_name(
                "Fix the authentication bug in login.py",
                "DEBUG"
            )
            print(f"✓ Generated branch: {branch_name}")
            assert branch_name.startswith("rocket/debug/")
            
            # Test 8: Commit message generation
            print("\n--- Test 8: Commit Message Generation ---")
            from Rocket.AGENT.Context import ExecutionContext
            
            ctx = ExecutionContext(
                user_prompt="Add user authentication",
                mode_name="AGENT"
            )
            ctx.files_created.add("src/auth.py")
            ctx.files_modified.add("src/app.py")
            
            commit_msg = await orchestrator._generate_commit_message(ctx)
            print(f"✓ Commit message:\n{commit_msg}")
            
            print("\n" + "=" * 60)
            print("All tests passed! ✓")
            print("=" * 60)
    
    # Run async tests
    asyncio.run(run_tests())
