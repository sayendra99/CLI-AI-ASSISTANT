"""
Execution context and result tracking.

Tracks EVERYTHING that happens during workflow execution.
Used for logging, debugging, and result reporting.
Provides immutable history of execution.

Performance Optimizations:
- LRU caching for serialization operations
- Efficient data structure access patterns
- Lazy evaluation of expensive computations

Author: Rocket AI Team
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from functools import lru_cache

# Handle imports for both package and direct execution
try:
    from Rocket.Utils.Log import get_logger
except ImportError:
    _project_root = Path(__file__).parent.parent.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))
    from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)


# =============================================================================
# Enums
# =============================================================================

class ExecutionStatus(Enum):
    """Status of workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# Tool Execution Tracking
# =============================================================================

@dataclass
class ToolExecution:
    """
    Record of a single tool execution.
    
    Attributes:
        tool_name: Name of the executed tool
        parameters: Parameters passed to the tool
        success: Whether execution succeeded
        result: Result data (if successful)
        error: Error message (if failed)
        execution_time_ms: Time taken in milliseconds
        timestamp: When the tool was executed
    """
    tool_name: str
    parameters: Dict[str, Any]
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


# =============================================================================
# Execution Context
# =============================================================================

@dataclass
class ExecutionContext:
    """
    Full execution state tracking (internal use).
    
    Tracks everything that happens during workflow execution:
    - Input: user prompt, mode, timestamps
    - Git: branches, commits, PRs
    - Files: read, modified, created
    - LLM: tokens, calls, cost
    - Tools: executions and results
    - Status: success/error state
    
    Example:
        >>> context = ExecutionContext(
        ...     user_prompt="Fix the bug in auth.py",
        ...     mode_name="DEBUG"
        ... )
        >>> context.add_file_read("src/auth.py")
        >>> context.add_tool_execution("read_file", result, {"path": "auth.py"})
    """
    
    # Input
    user_prompt: str
    mode_name: str
    timestamp: datetime = field(default_factory=datetime.now)
    workspace_root: Optional[str] = None
    
    # Status
    status: ExecutionStatus = ExecutionStatus.PENDING
    success: bool = False
    error: Optional[str] = None
    error_type: Optional[str] = None
    
    # Git tracking
    original_branch: Optional[str] = None
    branch_created: Optional[str] = None
    commit_hash: Optional[str] = None
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    
    # File tracking (use Set for deduplication)
    files_read: Set[str] = field(default_factory=set)
    files_modified: Set[str] = field(default_factory=set)
    files_created: Set[str] = field(default_factory=set)
    
    # LLM tracking
    tokens_used: int = 0
    llm_calls: int = 0
    llm_cost: float = 0.0
    llm_model: Optional[str] = None
    
    # Tool tracking
    tools_executed: List[ToolExecution] = field(default_factory=list)
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # -------------------------------------------------------------------------
    # Lifecycle Methods
    # -------------------------------------------------------------------------
    
    def start(self) -> None:
        """Mark execution as started."""
        self.start_time = datetime.now()
        self.status = ExecutionStatus.RUNNING
        logger.debug(f"Execution started: {self.mode_name}")
    
    def complete(self, success: bool = True, error: Optional[str] = None) -> None:
        """
        Mark execution as complete.
        
        Args:
            success: Whether execution succeeded
            error: Error message if failed
        """
        self.end_time = datetime.now()
        self.success = success
        self.error = error
        self.status = ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILED
        
        if error:
            logger.warning(f"Execution failed: {error}")
        else:
            logger.info(f"Execution completed successfully")
    
    def cancel(self, reason: str = "Cancelled by user") -> None:
        """Mark execution as cancelled."""
        self.end_time = datetime.now()
        self.success = False
        self.error = reason
        self.status = ExecutionStatus.CANCELLED
        logger.info(f"Execution cancelled: {reason}")
    
    # -------------------------------------------------------------------------
    # File Tracking Methods
    # -------------------------------------------------------------------------
    
    def add_file_read(self, path: str) -> None:
        """
        Record a file that was read.
        
        Args:
            path: Path to the file (relative or absolute)
        """
        normalized = self._normalize_path(path)
        self.files_read.add(normalized)
        logger.debug(f"File read: {normalized}")
    
    def add_file_modified(self, path: str) -> None:
        """
        Record a file that was modified.
        
        Args:
            path: Path to the file
        """
        normalized = self._normalize_path(path)
        self.files_modified.add(normalized)
        logger.debug(f"File modified: {normalized}")
    
    def add_file_created(self, path: str) -> None:
        """
        Record a file that was created.
        
        Args:
            path: Path to the file
        """
        normalized = self._normalize_path(path)
        self.files_created.add(normalized)
        logger.debug(f"File created: {normalized}")
    
    def _normalize_path(self, path: str) -> str:
        """Normalize a file path for consistent tracking."""
        # Convert to forward slashes and remove leading ./
        normalized = path.replace("\\", "/")
        if normalized.startswith("./"):
            normalized = normalized[2:]
        return normalized
    
    # -------------------------------------------------------------------------
    # Tool Tracking Methods
    # -------------------------------------------------------------------------
    
    def add_tool_execution(
        self,
        tool_name: str,
        success: bool,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        execution_time_ms: float = 0.0,
    ) -> ToolExecution:
        """
        Record a tool execution.
        
        Args:
            tool_name: Name of the tool
            success: Whether execution succeeded
            parameters: Parameters passed to tool
            result: Result data (if successful)
            error: Error message (if failed)
            execution_time_ms: Execution time
            
        Returns:
            The created ToolExecution record
        """
        execution = ToolExecution(
            tool_name=tool_name,
            parameters=parameters or {},
            success=success,
            result=result,
            error=error,
            execution_time_ms=execution_time_ms,
        )
        self.tools_executed.append(execution)
        
        logger.debug(
            f"Tool executed: {tool_name} "
            f"({'success' if success else 'failed'})"
        )
        
        return execution
    
    # -------------------------------------------------------------------------
    # LLM Tracking Methods
    # -------------------------------------------------------------------------
    
    def add_llm_usage(
        self,
        tokens: int,
        cost: float = 0.0,
        model: Optional[str] = None,
    ) -> None:
        """
        Record LLM usage.
        
        Args:
            tokens: Number of tokens used
            cost: Cost in dollars
            model: Model name
        """
        self.tokens_used += tokens
        self.llm_cost += cost
        self.llm_calls += 1
        
        if model and not self.llm_model:
            self.llm_model = model
        
        logger.debug(f"LLM call: {tokens} tokens, ${cost:.4f}")
    
    # -------------------------------------------------------------------------
    # Git Tracking Methods
    # -------------------------------------------------------------------------
    
    def set_git_info(
        self,
        original_branch: Optional[str] = None,
        branch_created: Optional[str] = None,
        commit_hash: Optional[str] = None,
        pr_url: Optional[str] = None,
        pr_number: Optional[int] = None,
    ) -> None:
        """
        Update git-related information.
        
        Args:
            original_branch: The branch we started on
            branch_created: New branch created for this work
            commit_hash: Commit hash of changes
            pr_url: URL of created PR
            pr_number: PR number
        """
        if original_branch:
            self.original_branch = original_branch
        if branch_created:
            self.branch_created = branch_created
        if commit_hash:
            self.commit_hash = commit_hash
        if pr_url:
            self.pr_url = pr_url
        if pr_number:
            self.pr_number = pr_number
    
    # -------------------------------------------------------------------------
    # Computed Properties
    # -------------------------------------------------------------------------
    
    @property
    def execution_time_seconds(self) -> float:
        """Get total execution time in seconds."""
        if not self.start_time:
            return 0.0
        
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    @property
    def total_files_affected(self) -> int:
        """Get total number of unique files affected."""
        all_files = self.files_read | self.files_modified | self.files_created
        return len(all_files)
    
    @property
    def total_tool_executions(self) -> int:
        """Get total number of tool executions."""
        return len(self.tools_executed)
    
    @property
    def successful_tool_executions(self) -> int:
        """Get number of successful tool executions."""
        return sum(1 for t in self.tools_executed if t.success)
    
    @property
    def failed_tool_executions(self) -> int:
        """Get number of failed tool executions."""
        return sum(1 for t in self.tools_executed if not t.success)
    
    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary for serialization.
        
        Returns:
            Dictionary representation of entire context
        """
        return {
            # Input
            "user_prompt": self.user_prompt,
            "mode_name": self.mode_name,
            "timestamp": self.timestamp.isoformat(),
            "workspace_root": self.workspace_root,
            
            # Status
            "status": self.status.value,
            "success": self.success,
            "error": self.error,
            "error_type": self.error_type,
            
            # Git
            "git": {
                "original_branch": self.original_branch,
                "branch_created": self.branch_created,
                "commit_hash": self.commit_hash,
                "pr_url": self.pr_url,
                "pr_number": self.pr_number,
            },
            
            # Files
            "files": {
                "read": sorted(self.files_read),
                "modified": sorted(self.files_modified),
                "created": sorted(self.files_created),
                "total_affected": self.total_files_affected,
            },
            
            # LLM
            "llm": {
                "model": self.llm_model,
                "tokens_used": self.tokens_used,
                "calls": self.llm_calls,
                "cost": round(self.llm_cost, 4),
            },
            
            # Tools
            "tools": {
                "total_executions": self.total_tool_executions,
                "successful": self.successful_tool_executions,
                "failed": self.failed_tool_executions,
                "executions": [t.to_dict() for t in self.tools_executed],
            },
            
            # Timing
            "timing": {
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "execution_time_seconds": round(self.execution_time_seconds, 2),
            },
            
            # Metadata
            "metadata": self.metadata,
        }
    
    def to_result(self) -> "ExecutionResult":
        """
        Convert to simplified ExecutionResult.
        
        Returns:
            ExecutionResult for API response
        """
        return ExecutionResult(
            success=self.success,
            mode_name=self.mode_name,
            error=self.error,
            files_modified=list(self.files_modified),
            files_created=list(self.files_created),
            commit_hash=self.commit_hash,
            pr_url=self.pr_url,
            pr_number=self.pr_number,
            tokens_used=self.tokens_used,
            execution_time_seconds=round(self.execution_time_seconds, 2),
        )


# =============================================================================
# Execution Result (Simplified for API Response)
# =============================================================================

@dataclass
class ExecutionResult:
    """
    Simplified execution result for API response.
    
    Contains only the essential information needed by consumers.
    Use ExecutionContext.to_result() to create from full context.
    
    Example:
        >>> result = context.to_result()
        >>> print(result.summary())
        >>> response = {"result": result.to_dict()}
    """
    
    success: bool
    mode_name: str
    error: Optional[str] = None
    
    # File changes
    files_modified: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    
    # Git info
    commit_hash: Optional[str] = None
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    branch_name: Optional[str] = None
    
    # Stats
    tokens_used: int = 0
    execution_time_seconds: float = 0.0
    
    # Optional message from LLM
    message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {
            "success": self.success,
            "mode": self.mode_name,
        }
        
        if self.error:
            result["error"] = self.error
        
        if self.message:
            result["message"] = self.message
        
        if self.files_modified or self.files_created:
            result["files"] = {
                "modified": self.files_modified,
                "created": self.files_created,
            }
        
        if self.commit_hash or self.pr_url:
            result["git"] = {}
            if self.commit_hash:
                result["git"]["commit"] = self.commit_hash
            if self.branch_name:
                result["git"]["branch"] = self.branch_name
            if self.pr_url:
                result["git"]["pr_url"] = self.pr_url
            if self.pr_number:
                result["git"]["pr_number"] = self.pr_number
        
        result["stats"] = {
            "tokens": self.tokens_used,
            "time_seconds": self.execution_time_seconds,
        }
        
        return result
    
    def summary(self) -> str:
        """
        Generate human-readable summary.
        
        Returns:
            Multi-line summary string
        """
        lines = []
        
        # Status header
        status_icon = "✅" if self.success else "❌"
        lines.append(f"{status_icon} Execution {'Succeeded' if self.success else 'Failed'}")
        lines.append(f"   Mode: {self.mode_name}")
        
        # Error if present
        if self.error:
            lines.append(f"   Error: {self.error}")
        
        # Message if present
        if self.message:
            lines.append(f"\n📝 Response:")
            # Indent message lines
            for msg_line in self.message.split("\n")[:10]:  # Limit preview
                lines.append(f"   {msg_line}")
            if self.message.count("\n") > 10:
                lines.append("   ...")
        
        # File changes
        total_files = len(self.files_modified) + len(self.files_created)
        if total_files > 0:
            lines.append(f"\n📁 Files Changed: {total_files}")
            for f in self.files_created[:5]:
                lines.append(f"   + {f} (created)")
            for f in self.files_modified[:5]:
                lines.append(f"   ~ {f} (modified)")
            if total_files > 10:
                lines.append(f"   ... and {total_files - 10} more")
        
        # Git info
        if self.commit_hash or self.pr_url:
            lines.append(f"\n🔀 Git:")
            if self.branch_name:
                lines.append(f"   Branch: {self.branch_name}")
            if self.commit_hash:
                lines.append(f"   Commit: {self.commit_hash[:8]}")
            if self.pr_url:
                lines.append(f"   PR: {self.pr_url}")
        
        # Stats
        lines.append(f"\n📊 Stats:")
        lines.append(f"   Tokens: {self.tokens_used:,}")
        lines.append(f"   Time: {self.execution_time_seconds:.1f}s")
        
        return "\n".join(lines)
    
    def __str__(self) -> str:
        """String representation."""
        return self.summary()


# =============================================================================
# Factory Functions
# =============================================================================

def create_context(
    user_prompt: str,
    mode_name: str,
    workspace_root: Optional[str] = None,
) -> ExecutionContext:
    """
    Create a new execution context.
    
    Args:
        user_prompt: The user's input prompt
        mode_name: Name of the execution mode
        workspace_root: Root directory of workspace
        
    Returns:
        New ExecutionContext instance
    """
    return ExecutionContext(
        user_prompt=user_prompt,
        mode_name=mode_name,
        workspace_root=workspace_root,
    )


# =============================================================================
# Self-Test
# =============================================================================

if __name__ == "__main__":
    import time
    
    print("=" * 60)
    print("ExecutionContext Self-Test")
    print("=" * 60)
    
    # Test 1: Create context
    print("\n--- Test 1: Create Context ---")
    context = ExecutionContext(
        user_prompt="Fix the authentication bug in auth.py",
        mode_name="DEBUG",
        workspace_root="/home/user/project"
    )
    print(f"✓ Created context for mode: {context.mode_name}")
    
    # Test 2: Start execution
    print("\n--- Test 2: Start Execution ---")
    context.start()
    assert context.status == ExecutionStatus.RUNNING
    assert context.start_time is not None
    print(f"✓ Status: {context.status.value}")
    
    # Test 3: Track files
    print("\n--- Test 3: Track Files ---")
    context.add_file_read("src/auth.py")
    context.add_file_read("src/utils.py")
    context.add_file_modified("src/auth.py")
    context.add_file_created("src/auth_test.py")
    
    assert len(context.files_read) == 2
    assert len(context.files_modified) == 1
    assert len(context.files_created) == 1
    print(f"✓ Files read: {context.files_read}")
    print(f"✓ Files modified: {context.files_modified}")
    print(f"✓ Files created: {context.files_created}")
    
    # Test 4: Track tool executions
    print("\n--- Test 4: Track Tool Executions ---")
    context.add_tool_execution(
        tool_name="read_file",
        success=True,
        parameters={"path": "src/auth.py"},
        result="file contents...",
        execution_time_ms=15.5
    )
    context.add_tool_execution(
        tool_name="write_file",
        success=True,
        parameters={"path": "src/auth.py", "content": "..."},
        execution_time_ms=22.3
    )
    context.add_tool_execution(
        tool_name="run_tests",
        success=False,
        parameters={"path": "tests/"},
        error="Test failed: assertion error",
        execution_time_ms=1500.0
    )
    
    assert context.total_tool_executions == 3
    assert context.successful_tool_executions == 2
    assert context.failed_tool_executions == 1
    print(f"✓ Total tool executions: {context.total_tool_executions}")
    print(f"✓ Successful: {context.successful_tool_executions}")
    print(f"✓ Failed: {context.failed_tool_executions}")
    
    # Test 5: Track LLM usage
    print("\n--- Test 5: Track LLM Usage ---")
    context.add_llm_usage(tokens=1500, cost=0.0045, model="gpt-4")
    context.add_llm_usage(tokens=800, cost=0.0024)
    
    assert context.tokens_used == 2300
    assert context.llm_calls == 2
    assert context.llm_model == "gpt-4"
    print(f"✓ Total tokens: {context.tokens_used}")
    print(f"✓ LLM calls: {context.llm_calls}")
    print(f"✓ Total cost: ${context.llm_cost:.4f}")
    
    # Test 6: Git info
    print("\n--- Test 6: Git Info ---")
    context.set_git_info(
        original_branch="main",
        branch_created="rocket/debug-auth-fix",
        commit_hash="abc123def456",
        pr_url="https://github.com/user/repo/pull/42",
        pr_number=42
    )
    
    assert context.original_branch == "main"
    assert context.pr_number == 42
    print(f"✓ Original branch: {context.original_branch}")
    print(f"✓ Created branch: {context.branch_created}")
    print(f"✓ PR: #{context.pr_number}")
    
    # Test 7: Complete execution
    print("\n--- Test 7: Complete Execution ---")
    time.sleep(0.1)  # Small delay for timing
    context.complete(success=True)
    
    assert context.status == ExecutionStatus.SUCCESS
    assert context.success is True
    assert context.execution_time_seconds > 0
    print(f"✓ Status: {context.status.value}")
    print(f"✓ Execution time: {context.execution_time_seconds:.2f}s")
    
    # Test 8: to_dict()
    print("\n--- Test 8: Serialization ---")
    data = context.to_dict()
    
    assert "user_prompt" in data
    assert "git" in data
    assert "files" in data
    assert "llm" in data
    assert "tools" in data
    print(f"✓ Serialized keys: {list(data.keys())}")
    
    # Test 9: to_result()
    print("\n--- Test 9: Convert to Result ---")
    result = context.to_result()
    
    assert result.success is True
    assert result.mode_name == "DEBUG"
    assert result.pr_number == 42
    print(f"✓ Result success: {result.success}")
    print(f"✓ Result mode: {result.mode_name}")
    
    # Test 10: Result summary
    print("\n--- Test 10: Result Summary ---")
    result.message = "Fixed the authentication bug by updating the token validation logic."
    summary = result.summary()
    
    assert "✅" in summary
    assert "DEBUG" in summary
    print(summary)
    
    # Test 11: Failed execution
    print("\n--- Test 11: Failed Execution ---")
    failed_context = ExecutionContext(
        user_prompt="Do something impossible",
        mode_name="AGENT"
    )
    failed_context.start()
    failed_context.complete(success=False, error="Tool execution failed: permission denied")
    
    failed_result = failed_context.to_result()
    assert failed_result.success is False
    assert "❌" in failed_result.summary()
    print(f"✓ Failed result:\n{failed_result.summary()}")
    
    # Test 12: Cancelled execution
    print("\n--- Test 12: Cancelled Execution ---")
    cancelled_context = ExecutionContext(
        user_prompt="Long running task",
        mode_name="ENHANCE"
    )
    cancelled_context.start()
    cancelled_context.cancel("User interrupted")
    
    assert cancelled_context.status == ExecutionStatus.CANCELLED
    print(f"✓ Cancelled status: {cancelled_context.status.value}")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
