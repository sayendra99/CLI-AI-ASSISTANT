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
    elif name == "ToolExecution":
        from Rocket.AGENT.Context import ToolExecution
        return ToolExecution
    elif name == "ToolExecutor":
        from Rocket.AGENT.Executor import ToolExecutor
        return ToolExecutor
    elif name == "ToolNotAllowedError":
        from Rocket.AGENT.Executor import ToolNotAllowedError
        return ToolNotAllowedError
    elif name == "WorkflowOrchestrator":
        from Rocket.AGENT.Workflow import WorkflowOrchestrator
        return WorkflowOrchestrator
    elif name == "WorkflowError":
        from Rocket.AGENT.Workflow import WorkflowError
        return WorkflowError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Context
    "ExecutionContext",
    "ExecutionResult",
    "ToolExecution",
    # Executor
    "ToolExecutor",
    "ToolNotAllowedError",
    # Workflow
    "WorkflowOrchestrator",
    "WorkflowError",
]
