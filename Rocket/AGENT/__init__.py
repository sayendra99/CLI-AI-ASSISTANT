"""
Rocket Agent Package.

Provides execution context, tool executor, and workflow orchestration
for the Rocket AI Coding Assistant.
"""

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    """Lazy load modules to avoid circular imports."""
    if name == "ExecutionContext":
        from Rocket.AGENT.Context import ExecutionContext
        return ExecutionContext
    elif name == "ExecutionResult":
        from Rocket.AGENT.Context import ExecutionResult
        return ExecutionResult
    elif name == "ExecutionStatus":
        from Rocket.AGENT.Context import ExecutionStatus
        return ExecutionStatus
    elif name == "ToolExecution":
        from Rocket.AGENT.Context import ToolExecution
        return ToolExecution
    elif name == "LLMUsage":
        from Rocket.AGENT.Context import LLMUsage
        return LLMUsage
    elif name == "ToolExecutor":
        from Rocket.AGENT.Executor import ToolExecutor
        return ToolExecutor
    elif name == "ToolNotAllowedError":
        from Rocket.AGENT.Executor import ToolNotAllowedError
        return ToolNotAllowedError
    elif name == "ToolExecutionError":
        from Rocket.AGENT.Executor import ToolExecutionError
        return ToolExecutionError
    elif name == "WorkflowOrchestrator":
        from Rocket.AGENT.Workflow import WorkflowOrchestrator
        return WorkflowOrchestrator
    elif name == "WorkflowError":
        from Rocket.AGENT.Workflow import WorkflowError
        return WorkflowError
    elif name == "WorkflowCancelledError":
        from Rocket.AGENT.Workflow import WorkflowCancelledError
        return WorkflowCancelledError
    elif name == "WorkflowConfig":
        from Rocket.AGENT.Workflow import WorkflowConfig
        return WorkflowConfig
    elif name == "run_workflow":
        from Rocket.AGENT.Workflow import run_workflow
        return run_workflow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Context
    "ExecutionContext",
    "ExecutionResult",
    "ExecutionStatus",
    "ToolExecution",
    "LLMUsage",
    # Executor
    "ToolExecutor",
    "ToolNotAllowedError",
    "ToolExecutionError",
    # Workflow
    "WorkflowOrchestrator",
    "WorkflowError",
    "WorkflowCancelledError",
    "WorkflowConfig",
    "run_workflow",
]
