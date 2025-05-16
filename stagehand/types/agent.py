from typing import TypedDict, Optional, Any, Literal, Union
from pydantic import BaseModel

class AgentConfig(BaseModel):
    """
    Configuration for agent execution.

    Attributes:
        model (Optional[str]): The model name to use.
        instructions (Optional[str]): Custom instructions for the agent (system prompt).
        options (Optional[dict[str, Any]]): Additional provider-specific options.
    """

    model: Optional[str] = None
    instructions: Optional[str] = None
    options: Optional[dict[str, Any]] = None

# Based on TS AgentAction
class ClickAction(TypedDict):
    type: Literal["click"]
    x: int
    y: int
    button: Optional[Literal["left", "right", "middle"]]

class DoubleClickAction(TypedDict):
    type: Literal["double_click", "doubleClick"]
    x: int
    y: int

class TypeAction(TypedDict):
    type: Literal["type"]
    text: str

class KeyPressAction(TypedDict):
    type: Literal["keypress"]
    keys: list[str] # e.g., ["CONTROL", "A"]

class ScrollAction(TypedDict):
    type: Literal["scroll"]
    x: int
    y: int
    scroll_x: Optional[int]
    scroll_y: Optional[int]

class Point(TypedDict):
    x: int
    y: int

class DragAction(TypedDict):
    type: Literal["drag"]
    path: list[Point]

class MoveAction(TypedDict):
    type: Literal["move"]
    x: int
    y: int

class WaitAction(TypedDict):
    type: Literal["wait"]
    # No specific args, implies a default wait time

class ScreenshotAction(TypedDict):
    type: Literal["screenshot"]
    # No specific args, screenshot is handled by client

class FunctionArguments(TypedDict, total=False):
    url: str
    # Add other function arguments as needed

class FunctionAction(TypedDict):
    type: Literal["function"]
    name: str
    arguments: Optional[FunctionArguments]

class KeyAction(TypedDict): # From Anthropic
    type: Literal["key"]
    text: str


AgentAction = Union[
    ClickAction,
    DoubleClickAction,
    TypeAction,
    KeyPressAction,
    ScrollAction,
    DragAction,
    MoveAction,
    WaitAction,
    ScreenshotAction,
    FunctionAction,
    KeyAction
]

class AgentUsage(TypedDict):
    input_tokens: int
    output_tokens: int
    inference_time_ms: int

class AgentResult(TypedDict):
    actions: list[AgentAction]
    result: Optional[str]
    usage: Optional[AgentUsage]

class ActionExecutionResult(TypedDict):
    success: bool
    error: Optional[str]


class AgentClientOptions(TypedDict, total=False):
    api_key: Optional[str]
    base_url: Optional[str]
    model_name: Optional[str] # For specific models like gpt-4, claude-2
    max_tokens: Optional[int]
    temperature: Optional[float]
    wait_between_actions: Optional[int] # in milliseconds
    # other client-specific options

class AgentHandlerOptions(TypedDict):
    model_name: str # e.g., "openai", "anthropic"
    client_options: Optional[AgentClientOptions]
    user_provided_instructions: Optional[str]
    # Add other handler options as needed 

class AgentExecuteOptions(TypedDict):
    """
    Agent execution parameters.

    Attributes:
        instruction (str): The instruction to execute.
        max_steps (Optional[int]): Maximum number of steps the agent can take. Defaults to 15.
        auto_screenshot (Optional[bool]): Whether to automatically capture screenshots after each action. False will let the agent choose when to capture screenshots. Defaults to False.
    """
    instruction: str
    max_steps: Optional[int] = 15
    auto_screenshot: Optional[bool] = False

CUA_KEY_TO_PLAYWRIGHT_KEY = {
    "/": "Divide",
    "\\": "Backslash",
    "alt": "Alt",
    "arrowdown": "ArrowDown",
    "arrowleft": "ArrowLeft",
    "arrowright": "ArrowRight",
    "arrowup": "ArrowUp",
    "backspace": "Backspace",
    "capslock": "CapsLock",
    "cmd": "Meta",
    "ctrl": "Control",
    "delete": "Delete",
    "end": "End",
    "enter": "Enter",
    "esc": "Escape",
    "home": "Home",
    "insert": "Insert",
    "option": "Alt",
    "pagedown": "PageDown",
    "pageup": "PageUp",
    "shift": "Shift",
    "space": " ",
    "super": "Meta",
    "tab": "Tab",
    "win": "Meta",
}