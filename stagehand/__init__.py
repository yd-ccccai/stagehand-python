from .agent import Agent
from .client import Stagehand
from .config import StagehandConfig
from .page import StagehandPage
from .schemas import (
    ActOptions,
    ActResult,
    AgentConfig,
    AgentExecuteOptions,
    AgentExecuteResult,
    AgentProvider,
    AvailableModel,
    ExtractOptions,
    ExtractResult,
    ObserveOptions,
    ObserveResult,
)
from .utils import configure_logging
from .handlers.observe_handler import ObserveHandler
from .inference import observe

__version__ = "0.3.5"

__all__ = [
    "Stagehand",
    "StagehandConfig",
    "StagehandPage",
    "Agent",
    "configure_logging",
    "ActOptions",
    "ActResult",
    "AvailableModel",
    "ExtractOptions",
    "ExtractResult",
    "ObserveOptions",
    "ObserveResult",
    "AgentConfig",
    "AgentExecuteOptions",
    "AgentExecuteResult",
    "AgentProvider",
    "ObserveHandler",
    "observe",
]
