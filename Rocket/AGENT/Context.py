"""
Execution context for tracking workflow state.

Provides dataclasses for tracking tool executions, LLM usage,
and overall execution results.

Author: Rocket AI Team
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional
import time


class ExecutionStatus(Enum):
    """Status of workflow execution."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    
    def __str__(self) -> str:
        return self.name


@dataclass
class ToolExecution:
    """
    Record of a single tool execution.
    
    Attributes:
        tool_name: Name of the tool executed
        success: Whether execution succeeded
        parameters: Parameters passed to the tool
        result: Tool result data (if successful)
        error: Error message (if failed)
        execution_time_ms: Time taken in milliseconds
        timestamp: When the tool was executed
    """
    tool_name: str
    success: bool
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "parameters": self.parameters,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"{status} {self.tool_name} ({self.execution_time_ms:.1f}ms)"


@dataclass
class LLMUsage:
    """
    Record of LLM API usage.
    
    Attributes:
        tokens: Total tokens used
        cost: Estimated cost (USD)
        model: Model name used
        timestamp: When the call was made
    """
    tokens: int = 0
    cost: float = 0.0
    model: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "tokens": self.tokens,
            "cost": self.cost,
            "model": self.model,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ExecutionContext:
    """
    Execution context for tracking workflow state.
    
    Tracks:
    - User prompt and mode
    - Tool executions (what tools were called, results)
    - File operations (reads, writes, creates)
    - LLM API usage (tokens, cost)
    - Timing information
    - Branch/git information
    
    Example:
        context = ExecutionContext(
            user_prompt="Fix the bug",
            mode_name="DEBUG"
        )
        context.add_tool_execution(
            tool_name="read_file",
            success=True,
            parameters={"path": "main.py"},
            result="...",
            execution_time_ms=15.3
        )
    """
    user_prompt: str
    mode_name: str
    
    # Execution tracking
    status: ExecutionStatus = ExecutionStatus.PENDING
    tool_executions: List[ToolExecution] = field(default_factory=list)
    llm_usage: List[LLMUsage] = field(default_factory=list)
    
    # File operations
    files_read: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    
    # Git information
    branch_created: Optional[str] = None
    commit_hash: Optional[str] = None
    pr_url: Optional[str] = None
    
    # Result
    output: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    
    # Timing
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    
    # -------------------------------------------------------------------------
    # Tool Execution Tracking
    # -------------------------------------------------------------------------
    
    def add_tool_execution(
        self,
        tool_name: str,
        success: bool,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        execution_time_ms: float = 0.0,
    ) -> None:
        """Add a tool execution record."""
        self.tool_executions.append(ToolExecution(
            tool_name=tool_name,
            success=success,
            parameters=parameters or {},
            result=result,
            error=error,
            execution_time_ms=execution_time_ms,
        ))
    
    def add_llm_usage(
        self,
        tokens: int,
        cost: float = 0.0,
        model: str = "",
    ) -> None:
        """Add an LLM usage record."""
        self.llm_usage.append(LLMUsage(
            tokens=tokens,
            cost=cost,
            model=model,
        ))
    
    # -------------------------------------------------------------------------
    # File Operation Tracking
    # -------------------------------------------------------------------------
    
    def track_file_read(self, path: str) -> None:
        """Track a file read operation."""
        if path not in self.files_read:
            self.files_read.append(path)
    
    def track_file_modified(self, path: str) -> None:
        """Track a file modification."""
        if path not in self.files_modified:
            self.files_modified.append(path)
    
    def track_file_created(self, path: str) -> None:
        """Track a file creation."""
        if path not in self.files_created:
            self.files_created.append(path)
    
    # -------------------------------------------------------------------------
    # Status Management
    # -------------------------------------------------------------------------
    
    def start(self) -> None:
        """Mark execution as started."""
        self.status = ExecutionStatus.RUNNING
        self.start_time = datetime.utcnow()
    
    def complete(self, success: bool = True, output: str = "", error: str = "") -> None:
        """Mark execution as completed."""
        self.status = ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED
        self.end_time = datetime.utcnow()
        self.output = output
        if error:
            self.error = error
    
    def cancel(self, reason: str = "") -> None:
        """Mark execution as cancelled."""
        self.status = ExecutionStatus.CANCELLED
        self.end_time = datetime.utcnow()
        self.error = reason or "Cancelled by user"
    
    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------
    
    @property
    def total_tool_calls(self) -> int:
        """Total number of tool calls made."""
        return len(self.tool_executions)
    
    @property
    def successful_tool_calls(self) -> int:
        """Number of successful tool calls."""
        return sum(1 for t in self.tool_executions if t.success)
    
    @property
    def failed_tool_calls(self) -> int:
        """Number of failed tool calls."""
        return sum(1 for t in self.tool_executions if not t.success)
    
    @property
    def total_tokens(self) -> int:
        """Total tokens used across all LLM calls."""
        return sum(u.tokens for u in self.llm_usage)
    
    @property
    def total_cost(self) -> float:
        """Total estimated cost across all LLM calls."""
        return sum(u.cost for u in self.llm_usage)
    
    @property
    def execution_time_seconds(self) -> float:
        """Total execution time in seconds."""
        end = self.end_time or datetime.utcnow()
        return (end - self.start_time).total_seconds()
    
    # -------------------------------------------------------------------------
    # Conversion
    # -------------------------------------------------------------------------
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary format."""
        return {
            "user_prompt": self.user_prompt,
            "mode_name": self.mode_name,
            "status": str(self.status),
            "tool_executions": [t.to_dict() for t in self.tool_executions],
            "llm_usage": [u.to_dict() for u in self.llm_usage],
            "files_read": self.files_read,
            "files_modified": self.files_modified,
            "files_created": self.files_created,
            "branch_created": self.branch_created,
            "commit_hash": self.commit_hash,
            "pr_url": self.pr_url,
            "output": self.output,
            "error": self.error,
            "error_type": self.error_type,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_tool_calls": self.total_tool_calls,
            "total_tokens": self.total_tokens,
            "execution_time_seconds": self.execution_time_seconds,
        }
    
    def to_result(self) -> "ExecutionResult":
        """Convert context to ExecutionResult."""
        return ExecutionResult(
            success=self.status == ExecutionStatus.COMPLETED,
            output=self.output or "",
            error=self.error,
            error_type=self.error_type,
            context=self,
            mode_name=self.mode_name,
            branch_name=self.branch_created,
            pr_url=self.pr_url,
            files_modified=self.files_modified.copy(),
            files_created=self.files_created.copy(),
            tool_calls=self.total_tool_calls,
            tokens_used=self.total_tokens,
            execution_time=self.execution_time_seconds,
        )
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"ExecutionContext("
            f"mode={self.mode_name}, "
            f"status={self.status}, "
            f"tools={self.total_tool_calls}, "
            f"tokens={self.total_tokens}"
            f")"
        )


@dataclass
class ExecutionResult:
    """
    Final result from workflow execution.
    
    Contains the output, any errors, and metadata about
    what happened during execution.
    
    Attributes:
        success: Whether execution succeeded
        output: Final output text
        error: Error message if failed
        error_type: Type of error
        context: Full execution context
        mode_name: Mode that was used
        branch_name: Git branch created
        pr_url: Pull request URL if created
        files_modified: List of modified files
        files_created: List of created files
        tool_calls: Number of tool calls made
        tokens_used: Total tokens consumed
        execution_time: Time taken in seconds
    """
    success: bool
    output: str = ""
    error: Optional[str] = None
    error_type: Optional[str] = None
    context: Optional[ExecutionContext] = None
    mode_name: str = ""
    branch_name: Optional[str] = None
    pr_url: Optional[str] = None
    files_modified: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    tool_calls: int = 0
    tokens_used: int = 0
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "error_type": self.error_type,
            "mode_name": self.mode_name,
            "branch_name": self.branch_name,
            "pr_url": self.pr_url,
            "files_modified": self.files_modified,
            "files_created": self.files_created,
            "tool_calls": self.tool_calls,
            "tokens_used": self.tokens_used,
            "execution_time": self.execution_time,
        }
    
    def summary(self) -> str:
        """Get human-readable summary."""
        status = "✓ Success" if self.success else "✗ Failed"
        lines = [
            f"=== Execution Result ===",
            f"Status: {status}",
            f"Mode: {self.mode_name}",
        ]
        
        if self.branch_name:
            lines.append(f"Branch: {self.branch_name}")
        if self.pr_url:
            lines.append(f"PR: {self.pr_url}")
        
        lines.extend([
            f"Tool calls: {self.tool_calls}",
            f"Tokens: {self.tokens_used}",
            f"Time: {self.execution_time:.2f}s",
        ])
        
        if self.files_modified:
            lines.append(f"Modified: {', '.join(self.files_modified)}")
        if self.files_created:
            lines.append(f"Created: {', '.join(self.files_created)}")
        
        if self.error:
            lines.append(f"Error: {self.error}")
        
        return "\n".join(lines)
    
    def __str__(self) -> str:
        status = "Success" if self.success else "Failed"
        return f"ExecutionResult({status}, tools={self.tool_calls}, tokens={self.tokens_used})"


# =============================================================================
# Self-Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("ExecutionContext Self-Test")
    print("=" * 60)
    
    # Test 1: Create context
    print("\n--- Test 1: Create Context ---")
    context = ExecutionContext(
        user_prompt="Fix the authentication bug",
        mode_name="DEBUG"
    )
    print(f"✓ Created: {context}")
    
    # Test 2: Add tool executions
    print("\n--- Test 2: Add Tool Executions ---")
    context.start()
    context.add_tool_execution(
        tool_name="read_file",
        success=True,
        parameters={"path": "auth.py"},
        result="file content...",
        execution_time_ms=15.3
    )
    context.add_tool_execution(
        tool_name="write_file",
        success=True,
        parameters={"path": "auth.py", "content": "..."},
        execution_time_ms=8.7
    )
    print(f"✓ Added {context.total_tool_calls} tool executions")
    
    # Test 3: Add LLM usage
    print("\n--- Test 3: Add LLM Usage ---")
    context.add_llm_usage(tokens=1500, cost=0.003, model="gemini-1.5-flash")
    context.add_llm_usage(tokens=800, cost=0.0016, model="gemini-1.5-flash")
    print(f"✓ Total tokens: {context.total_tokens}")
    print(f"✓ Total cost: ${context.total_cost:.4f}")
    
    # Test 4: Track file operations
    print("\n--- Test 4: Track File Operations ---")
    context.track_file_read("auth.py")
    context.track_file_modified("auth.py")
    context.track_file_created("auth_test.py")
    print(f"✓ Files read: {context.files_read}")
    print(f"✓ Files modified: {context.files_modified}")
    print(f"✓ Files created: {context.files_created}")
    
    # Test 5: Complete execution
    print("\n--- Test 5: Complete Execution ---")
    context.complete(success=True, output="Bug fixed successfully!")
    print(f"✓ Status: {context.status}")
    print(f"✓ Execution time: {context.execution_time_seconds:.2f}s")
    
    # Test 6: Convert to result
    print("\n--- Test 6: Convert to Result ---")
    result = context.to_result()
    print(f"✓ Result: {result}")
    print(f"\n{result.summary()}")
    
    # Test 7: Convert to dict
    print("\n--- Test 7: Serialization ---")
    data = context.to_dict()
    assert "user_prompt" in data
    assert "tool_executions" in data
    print(f"✓ Serialized to dict with {len(data)} keys")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
