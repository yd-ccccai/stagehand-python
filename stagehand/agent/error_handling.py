from __future__ import annotations


class NativeAgentError(Exception):
    """Base exception for Native Agent errors."""


class ToolExecutionError(NativeAgentError):
    """Raised when a tool fails irrecoverably."""


__all__ = [
    "NativeAgentError",
    "ToolExecutionError",
]
