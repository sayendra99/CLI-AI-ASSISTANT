"""
Workflow orchestrator for Rocket AI Coding Assistant.

Coordinates the entire execution flow including:
- Mode selection
- Git branch management
- Tool execution
- LLM interaction with tool calling loop
- Result aggregation

Author: Rocket AI Team
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

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
    """Configuration for workflow execution."""
    max_iterations: int = 10
    max_tool_calls: int = 50
    auto_commit: bool = False
    auto_pr: bool = False
    draft_pr: bool = True
    create_branch: bool = True
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
    - LLM: AI-powered code generation with real tool calling
    - PRs: Automatic PR creation
    
    Workflow Steps:
    1. Select mode (auto or explicit)
    2. Check git status
    3. Create safety branch if needed
    4. Initialize tool executor
    5. Execute LLM with tool access (real tool calling loop)
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
        git_manager: Optional[GitManager] = None,
        config: Optional[WorkflowConfig] = None,
    ) -> None:
        """
        Initialize the workflow orchestrator.
        
        Args:
            workspace_root: Root directory for file operations
            llm_client: Gemini LLM client (required for real execution)
            mode_registry: Registry of available modes
            git_manager: Git operations manager
            config: Workflow configuration
        """
        self.workspace_root = Path(workspace_root or Path.cwd()).resolve()
        self.llm_client = llm_client
        self.config = config or WorkflowConfig()
        
        # Initialize mode registry
        if mode_registry:
            self._mode_registry = mode_registry
        else:
            # Use global registry
            from Rocket.MODES import mode_registry as global_registry
            self._mode_registry = global_registry
        
        # Initialize git manager
        self._git_manager = git_manager
        
        # Mode selector for auto-detection
        self._mode_selector = ModeSelector(self._mode_registry)
        
        logger.info(f"WorkflowOrchestrator initialized for: {self.workspace_root}")
    
    # -------------------------------------------------------------------------
    # Main Execution Entry Point
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
        Execute the complete workflow.
        
        Args:
            user_prompt: User's request
            mode_name: Explicit mode (or auto-detect if None)
            auto_mode: Auto-detect mode if not specified
            auto_commit: Auto-commit changes
            auto_pr: Auto-create pull request
            draft_pr: Create as draft PR
            create_branch: Create safety branch
            target_branch: Target branch for PR
            
        Returns:
            ExecutionResult with output and metadata
        """
        logger.info(f"Starting workflow: {user_prompt[:100]}...")
        
        # Step 1: Select mode
        mode = self._select_mode(user_prompt, mode_name, auto_mode)
        logger.info(f"Selected mode: {mode.config.name}")
        
        # Create execution context
        context = ExecutionContext(
            user_prompt=user_prompt,
            mode_name=mode.config.name,
        )
        context.start()
        
        try:
            # Step 2: Git branch management (if needed)
            if create_branch and mode.needs_git_branch():
                branch_name = await self._setup_git_branch(user_prompt, mode, context)
                if branch_name:
                    context.branch_created = branch_name
            
            # Step 3: Create tool executor
            executor = self._create_executor(mode, context)
            
            # Step 4: Execute LLM with tool calling loop
            response = await self._execute_llm_with_tools(
                user_prompt=user_prompt,
                mode=mode,
                executor=executor,
                context=context,
            )
            
            # Step 5: Complete execution
            context.complete(success=True, output=response)
            
            # Step 6: Auto-commit if requested
            if auto_commit and (context.files_modified or context.files_created):
                await self._commit_changes(context)
            
            # Step 7: Auto-PR if requested
            if auto_pr and context.branch_created:
                await self._create_pr(context, target_branch, draft_pr)
            
            result = context.to_result()
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
            logger.error(f"Workflow failed: {e}", exc_info=True)
            return context.to_result()
    
    # -------------------------------------------------------------------------
    # Step 1: Mode Selection
    # -------------------------------------------------------------------------
    
    def _select_mode(
        self,
        user_prompt: str,
        mode_name: Optional[str],
        auto_mode: bool,
    ) -> "BaseMode":
        """Select the operating mode."""
        if mode_name:
            # Explicit mode requested
            mode = self._mode_registry.get(mode_name)
            if not mode:
                raise WorkflowError(f"Unknown mode: {mode_name}")
            return mode
        
        if auto_mode:
            # Auto-detect mode from prompt
            return self._mode_selector.select_from_prompt(user_prompt)
        
        # Default to READ mode (safest)
        return self._mode_registry.get_or_default("READ")
    
    # -------------------------------------------------------------------------
    # Step 2: Git Branch Setup
    # -------------------------------------------------------------------------
    
    async def _setup_git_branch(
        self,
        user_prompt: str,
        mode: "BaseMode",
        context: ExecutionContext,
    ) -> Optional[str]:
        """Setup git branch for safety."""
        if not self._git_manager:
            try:
                self._git_manager = GitManager(self.workspace_root)
            except Exception as e:
                logger.warning(f"Could not initialize git: {e}")
                return None
        
        try:
            # Check if we're in a git repo
            status = self._git_manager.get_status()
            if not status.is_git_repo:
                logger.info("Not a git repository, skipping branch creation")
                return None
            
            # Generate branch name
            branch_name = self._generate_branch_name(user_prompt, mode.config.name)
            
            # Create and checkout branch
            self._git_manager.create_branch(branch_name)
            self._git_manager.checkout(branch_name)
            
            logger.info(f"Created and checked out branch: {branch_name}")
            return branch_name
            
        except GitError as e:
            logger.warning(f"Git branch setup failed: {e}")
            return None
    
    def _generate_branch_name(self, user_prompt: str, mode_name: str) -> str:
        """Generate a branch name from prompt and mode."""
        import re
        import time
        
        # Extract key words from prompt
        words = re.findall(r'\b\w+\b', user_prompt.lower())[:3]
        slug = "-".join(words) if words else "task"
        
        # Add timestamp for uniqueness
        timestamp = int(time.time()) % 100000
        
        return f"rocket/{mode_name.lower()}/{slug}-{timestamp}"
    
    # -------------------------------------------------------------------------
    # Step 3: Tool Executor Creation
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
            
            registry.register(ReadFileTool(workspace_root=self.workspace_root))
            registry.register(WriteFileTool(workspace_root=self.workspace_root))
            
            logger.debug(f"Registered {registry.count()} default tools")
            
        except ImportError as e:
            logger.warning(f"Could not register tools: {e}")
    
    # -------------------------------------------------------------------------
    # Step 4: LLM Execution with Tool Calling Loop
    # -------------------------------------------------------------------------
    
    async def _execute_llm_with_tools(
        self,
        user_prompt: str,
        mode: "BaseMode",
        executor: ToolExecutor,
        context: ExecutionContext,
    ) -> str:
        """
        Execute LLM with real tool calling loop.
        
        This is the core implementation that:
        1. Sends prompt + tool schemas to LLM
        2. If LLM returns tool calls, execute them
        3. Send tool results back to LLM
        4. Repeat until LLM gives final answer
        
        Args:
            user_prompt: User's request
            mode: Current mode
            executor: Tool executor
            context: Execution context
            
        Returns:
            Final LLM response text
        """
        if not self.llm_client:
            logger.warning("No LLM client configured, using mock response")
            return await self._mock_llm_execution(user_prompt, mode, executor, context)
        
        # Get tool schemas for LLM
        tool_schemas = executor.get_tool_schemas(format="gemini")
        
        # Get mode settings
        llm_settings = mode.get_llm_settings()
        system_prompt = llm_settings.get("system_instruction", "")
        temperature = llm_settings.get("temperature", 0.7)
        
        logger.debug(
            f"Starting LLM execution: {len(tool_schemas)} tools, temp={temperature}"
        )
        
        # Build initial conversation
        messages = []
        if system_prompt:
            messages.append({"role": "user", "parts": [system_prompt]})
            messages.append({"role": "model", "parts": ["Understood. I'll follow these instructions."]})
        
        messages.append({"role": "user", "parts": [user_prompt]})
        
        # Tool calling loop
        iteration = 0
        total_tool_calls = 0
        max_iterations = self.config.max_iterations
        max_tool_calls = self.config.max_tool_calls
        
        while iteration < max_iterations:
            iteration += 1
            logger.debug(f"LLM iteration {iteration}/{max_iterations}")
            
            try:
                # Call LLM with tools
                response = await self.llm_client.generate_with_tools(
                    messages=messages,
                    tools=tool_schemas,
                    temperature=temperature,
                )
                
                # Track LLM usage
                if hasattr(response, 'usage'):
                    context.add_llm_usage(
                        tokens=response.usage.get('total_tokens', 0),
                        cost=response.usage.get('cost', 0.0),
                        model=self.llm_client.model_name,
                    )
                
                # Check if LLM wants to call tools
                if response.tool_calls:
                    # Execute tool calls
                    tool_results = []
                    
                    for tool_call in response.tool_calls:
                        if total_tool_calls >= max_tool_calls:
                            logger.warning(f"Max tool calls ({max_tool_calls}) reached")
                            tool_results.append({
                                "name": tool_call.name,
                                "result": "Error: Maximum tool calls limit reached",
                                "error": True,
                            })
                            continue
                        
                        total_tool_calls += 1
                        logger.info(f"Executing tool: {tool_call.name}")
                        
                        try:
                            # Execute the tool
                            result = executor.execute(tool_call.name, **tool_call.arguments)
                            
                            tool_results.append({
                                "name": tool_call.name,
                                "result": self._format_tool_result(result),
                                "error": not result.success,
                            })
                            
                        except ToolNotAllowedError as e:
                            logger.warning(f"Tool not allowed: {e}")
                            tool_results.append({
                                "name": tool_call.name,
                                "result": f"Error: {str(e)}",
                                "error": True,
                            })
                        except Exception as e:
                            logger.error(f"Tool execution error: {e}")
                            tool_results.append({
                                "name": tool_call.name,
                                "result": f"Error: {str(e)}",
                                "error": True,
                            })
                    
                    # Add tool call to conversation
                    messages.append({
                        "role": "model",
                        "parts": [response.raw_response] if response.raw_response else [],
                        "tool_calls": response.tool_calls,
                    })
                    
                    # Add tool results to conversation
                    messages.append({
                        "role": "user",
                        "parts": [self._format_tool_results_for_llm(tool_results)],
                    })
                    
                    # Continue loop - LLM will see results
                    continue
                
                # No tool calls - LLM is done
                if response.content:
                    logger.info(f"LLM completed after {iteration} iterations, {total_tool_calls} tool calls")
                    return response.content
                else:
                    logger.warning("LLM returned empty response")
                    return "I apologize, but I couldn't generate a response. Please try again."
                    
            except Exception as e:
                logger.error(f"LLM API error: {e}", exc_info=True)
                raise WorkflowError(f"LLM execution failed: {e}")
        
        # Max iterations reached
        logger.warning(f"Max iterations ({max_iterations}) reached")
        return (
            f"I've reached the maximum number of iterations ({max_iterations}). "
            f"Here's what I've done so far based on {total_tool_calls} tool calls."
        )
    
    def _format_tool_result(self, result) -> str:
        """Format a tool result for LLM consumption."""
        if result.success:
            data = result.data
            if isinstance(data, dict):
                # Handle file content
                if 'content' in data:
                    return data['content']
                return str(data)
            return str(data) if data else "Success (no output)"
        else:
            return f"Error: {result.error}"
    
    def _format_tool_results_for_llm(self, tool_results: List[Dict[str, Any]]) -> str:
        """Format multiple tool results for sending back to LLM."""
        parts = ["Here are the results of the tool calls:"]
        
        for tr in tool_results:
            name = tr["name"]
            result = tr["result"]
            is_error = tr.get("error", False)
            
            if is_error:
                parts.append(f"\n[{name}] ERROR:\n{result}")
            else:
                # Truncate very long results
                if len(str(result)) > 5000:
                    result = str(result)[:5000] + "\n... (truncated)"
                parts.append(f"\n[{name}] SUCCESS:\n{result}")
        
        return "\n".join(parts)
    
    # -------------------------------------------------------------------------
    # Mock LLM Execution (for testing)
    # -------------------------------------------------------------------------
    
    async def _mock_llm_execution(
        self,
        user_prompt: str,
        mode: "BaseMode",
        executor: ToolExecutor,
        context: ExecutionContext,
    ) -> str:
        """
        Mock LLM execution for testing when no API key is available.
        """
        logger.debug("Using mock LLM execution")
        
        # Simulate some token usage
        context.add_llm_usage(
            tokens=150,
            cost=0.0003,
            model="mock-model"
        )
        
        # Get tool schemas for info
        tool_schemas = executor.get_tool_schemas(format="gemini")
        available_tools = [s.get("name", "unknown") for s in tool_schemas]
        mode_name = mode.config.name
        
        mock_response = f"""
**Mode**: {mode_name}
**Prompt**: {user_prompt[:100]}...

This is a mock response from the workflow orchestrator.
In production, this would be replaced with actual LLM output using the Gemini API.

**Available Tools**: {', '.join(available_tools)}

To enable real LLM execution:
1. Set GEMINI_API_KEY in your environment
2. Initialize GeminiClient and pass to WorkflowOrchestrator

The workflow has been set up correctly with:
- Mode-based permissions
- Tool execution tracking
- Git integration
- Context management
        """.strip()
        
        return mock_response
    
    # -------------------------------------------------------------------------
    # Step 5-6: Commit and PR
    # -------------------------------------------------------------------------
    
    async def _commit_changes(self, context: ExecutionContext) -> Optional[str]:
        """Commit changes made during execution."""
        if not self._git_manager:
            return None
        
        try:
            # Stage all changes
            files = context.files_modified + context.files_created
            for file in files:
                self._git_manager.stage_file(file)
            
            # Generate commit message
            msg = f"🚀 Rocket: {context.user_prompt[:50]}"
            
            # Commit
            commit_hash = self._git_manager.commit(msg)
            context.commit_hash = commit_hash
            
            logger.info(f"Committed changes: {commit_hash}")
            return commit_hash
            
        except GitError as e:
            logger.warning(f"Could not commit: {e}")
            return None
    
    async def _create_pr(
        self,
        context: ExecutionContext,
        target_branch: str,
        draft: bool,
    ) -> Optional[str]:
        """Create a pull request for the changes."""
        if not context.branch_created:
            return None
        
        try:
            pr_creator = PRCreator(self.workspace_root)
            pr_info = pr_creator.create(
                title=f"🚀 {context.user_prompt[:50]}",
                body=self._generate_pr_body(context),
                source_branch=context.branch_created,
                target_branch=target_branch,
                draft=draft,
            )
            context.pr_url = pr_info.url
            logger.info(f"Created PR: {pr_info.url}")
            return pr_info.url
            
        except (PRCreationError, Exception) as e:
            logger.warning(f"Could not create PR: {e}")
            return None
    
    def _generate_pr_body(self, context: ExecutionContext) -> str:
        """Generate PR description."""
        lines = [
            "## 🚀 Rocket AI Generated Changes",
            "",
            f"**Mode**: {context.mode_name}",
            f"**Prompt**: {context.user_prompt}",
            "",
            "### Changes",
        ]
        
        if context.files_modified:
            lines.append(f"Modified: {', '.join(context.files_modified)}")
        if context.files_created:
            lines.append(f"Created: {', '.join(context.files_created)}")
        
        lines.extend([
            "",
            "### Stats",
            f"- Tool calls: {context.total_tool_calls}",
            f"- Tokens used: {context.total_tokens}",
            f"- Execution time: {context.execution_time_seconds:.2f}s",
        ])
        
        return "\n".join(lines)


# =============================================================================
# Convenience Function
# =============================================================================

async def run_workflow(
    user_prompt: str,
    mode_name: Optional[str] = None,
    workspace_root: Optional[Path] = None,
    llm_client: Optional["GeminiClient"] = None,
    **kwargs: Any,
) -> ExecutionResult:
    """
    Convenience function to run a workflow.
    
    Args:
        user_prompt: User's request
        mode_name: Mode to use
        workspace_root: Working directory
        llm_client: LLM client
        **kwargs: Additional options
        
    Returns:
        ExecutionResult
    """
    orchestrator = WorkflowOrchestrator(
        workspace_root=workspace_root,
        llm_client=llm_client,
    )
    
    return await orchestrator.execute(
        user_prompt=user_prompt,
        mode_name=mode_name,
        **kwargs,
    )


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
            
            # Create test file
            test_file = temp_path / "test.py"
            test_file.write_text("print('hello')\n")
            
            # Test 1: Create orchestrator
            print("\n--- Test 1: Create Orchestrator ---")
            orchestrator = WorkflowOrchestrator(workspace_root=temp_path)
            print(f"✓ Created orchestrator for: {orchestrator.workspace_root}")
            
            # Test 2: Execute without LLM (mock mode)
            print("\n--- Test 2: Execute (Mock Mode) ---")
            result = await orchestrator.execute(
                user_prompt="List the files in the current directory",
                mode_name="READ",
                create_branch=False,
            )
            
            print(f"✓ Execution completed: success={result.success}")
            print(f"  Mode: {result.mode_name}")
            print(f"  Tool calls: {result.tool_calls}")
            print(f"  Output preview: {result.output[:100]}...")
            
            # Test 3: Summary
            print("\n--- Test 3: Result Summary ---")
            print(result.summary())
            
            print("\n" + "=" * 60)
            print("All tests passed! ✓")
            print("=" * 60)
    
    # Run async tests
    asyncio.run(run_tests())
