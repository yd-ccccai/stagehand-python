from .client import Stagehand
from .config import StagehandConfig
from .page import StagehandPage
from .schemas import (
    ActOptions,
    ActResult,
    AvailableModel,
    ExtractOptions,
    ExtractResult,
    ObserveOptions,
    ObserveResult,
)

__version__ = "0.2.2"

__all__ = [
    "Stagehand",
    "StagehandConfig",
    "StagehandPage",
    "ActOptions",
    "ActResult",
    "AvailableModel",
    "ExtractOptions",
    "ExtractResult",
    "ObserveOptions",
    "ObserveResult",
]
