from .client import Stagehand
from .config import StagehandConfig
from .page import StagehandPage
from .agent import Agent
from .utils import configure_logging
from .schemas import (
    ActOptions,
    ActResult,
    AvailableModel,
    ExtractOptions,
    ExtractResult,
    ObserveOptions,
    ObserveResult,
    AgentConfig,
    AgentExecuteOptions,
    AgentExecuteResult,
    AgentProvider,
)

__version__ = "0.2.2"

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
]
