from abc import ABC, abstractmethod
from typing import Callable, Awaitable, Any, Dict

from ..types import AgentAction, ActionExecutionResult

class AgentClient(ABC):
    """Abstract base class for a Computer Use Agent client."""

    @abstractmethod
    async def execute_task(self, instruction: str, **kwargs) -> Any: # Return type will be more specific later
        """Execute a task with the given instruction."""
        pass

    @abstractmethod
    def set_viewport(self, width: int, height: int) -> None:
        """Set the viewport size known to the agent."""
        pass

    @abstractmethod
    def set_current_url(self, url: str) -> None:
        """Set the current URL known to the agent."""
        pass

    @abstractmethod
    async def capture_screenshot(self, data: Dict[str, Any]) -> Any:
        """Capture and send a screenshot to the agent."""
        # data typically includes {'base64Image': str, 'currentUrl': str}
        pass
  