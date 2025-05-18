import base64
from typing import Union, Optional
import asyncio

from ..types.agent import (
    AgentAction,
    ActionExecutionResult,
)


class StagehandFunctionName:
    AGENT = "agent"


class CUAHandler:  # Computer Use Agent Handler
    """Handles Computer Use Agent tasks by executing actions on the page."""

    def __init__(
        self,
        stagehand,
        page,
        logger,
    ):
        self.stagehand = stagehand
        self.logger = logger
        self.page = page

    async def get_screenshot_base64(self) -> str:
        """Captures a screenshot of the current page and returns it as a base64 encoded string."""
        self.logger.debug("Capturing screenshot for CUA client", category=StagehandFunctionName.AGENT)
        screenshot_bytes = await self.page.screenshot(full_page=False, type="png")
        return base64.b64encode(screenshot_bytes).decode()

    async def perform_action(self, action: AgentAction) -> ActionExecutionResult:
        """Execute a single action on the page."""
        self.logger.info(f"Performing action: {action.action_type}", auxiliary={'action_details': action.action.model_dump_json() if action.action else None}, category=StagehandFunctionName.AGENT)
        action_type = action.action_type
        # action.action is the RootModel, action.action.root is the specific action model (e.g., ClickAction)
        specific_action_model = action.action.root if action.action else None

        if not specific_action_model:
            self.logger.error(f"No specific action model found for action type {action_type}", category=StagehandFunctionName.AGENT)
            return {"success": False, "error": f"No specific action model for {action_type}"}

        try:
            match action_type:
                case "click":
                    # specific_action_model is already an instance of ClickAction
                    x, y = specific_action_model.x, specific_action_model.y
                    button = getattr(specific_action_model, "button", "left")

                    await self._update_cursor_position(x, y)
                    await self._animate_click(x, y)
                    await asyncio.sleep(0.3) # Ensure animation is visible
                    await self.page.mouse.click(x, y, button=button)
                    # Consider new tab/page handling logic here if needed
                    return { "success": True }

                case "double_click":
                    # specific_action_model is e.g. DoubleClickAction
                    x, y = specific_action_model.x, specific_action_model.y
                    await self._update_cursor_position(x,y)
                    await self._animate_click(x,y)
                    await asyncio.sleep(0.2)
                    await self._animate_click(x,y)
                    await asyncio.sleep(0.2)
                    await self.page.mouse.dblclick(x,y)
                    return { "success": True }

                case "type":
                    # specific_action_model is TypeAction
                    await self.page.keyboard.type(specific_action_model.text) # type: ignore
                    return { "success": True }

                case "keypress":
                    # specific_action_model is KeyPressAction
                    # Ensure playwright_key is defined before loop or correctly scoped if used after
                    playwright_key = "" # Initialize
                    for key_str in specific_action_model.keys:
                        playwright_key = self._convert_key_name(key_str)
                        await self.page.keyboard.press(playwright_key) # Press each key
                    return { "success": True }

                case "scroll":
                    # specific_action_model is ScrollAction
                    x, y = specific_action_model.x, specific_action_model.y
                    scroll_x = getattr(specific_action_model, "scroll_x", 0)
                    scroll_y = getattr(specific_action_model, "scroll_y", 0)
                    await self.page.mouse.move(x, y) # type: ignore
                    await self.page.evaluate(
                        "(params) => window.scrollBy(params.scrollX, params.scrollY)",
                        {"scrollX": scroll_x, "scrollY": scroll_y}
                    )
                    return {"success": True}

                case "function":
                    # specific_action_model is FunctionAction
                    name = specific_action_model.name
                    args = getattr(specific_action_model, "arguments", {})
                    if name == "goto" and args and "url" in args:
                      await self.page.goto(args["url"]) # type: ignore
                      return {"success": True}
                    # Add other function calls like back, forward, reload if needed, similar to TS version
                    self.logger.warning(f"Unsupported function call: {name}", category=StagehandFunctionName.AGENT)
                    return {"success": False, "error": f"Unsupported function: {name}"}


                case "key": # Anthropic specific key action (can be generalized or mapped by Anthropic client)
                    # specific_action_model is KeyAction
                    text = specific_action_model.text
                    # This logic might be better if Anthropic client translates to a "keypress" AgentAction
                    # or if _convert_key_name handles these common names too.
                    if text.lower() in ["return", "enter"]:
                      await self.page.keyboard.press("Enter") # type: ignore
                    elif text.lower() == "tab":
                        await self.page.keyboard.press("Tab") # type: ignore
                    else:
                        # Use _convert_key_name for consistency if possible, or press directly
                        await self.page.keyboard.press(self._convert_key_name(text)) # type: ignore
                    return {"success": True}

                case _:
                    self.logger.warning(f"Unsupported action type: {action_type}", category=StagehandFunctionName.AGENT)
                    return {"success": False, "error": f"Unsupported action type: {action_type}"}

        except Exception as e:
            self.logger.error(f"Error executing action {action_type}: {e}", category=StagehandFunctionName.AGENT) # Removed exc_info=True for cleaner logs unless debugging
            return {"success": False, "error": str(e)}

    async def inject_cursor(self) -> None:
        """Inject a cursor element into the page for visual feedback."""
        self.logger.info("Attempting to inject cursor", category=StagehandFunctionName.AGENT)
        cursor_id = "stagehand-cursor"
        highlight_id = "stagehand-highlight"

        cursor_exists = await self.page.evaluate(
            f"!!document.getElementById('{cursor_id}')"
        )
        if cursor_exists:
            self.logger.info("Cursor already exists.", category=StagehandFunctionName.AGENT)
            return

        js_code = f"""
        (function(cursorId, highlightId) {{
          // Create cursor element
          const cursor = document.createElement('div');
          cursor.id = cursorId;
          
          // Use the provided SVG for a custom cursor
          cursor.innerHTML = `
          <svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 28 28" width="28" height="28">
            <polygon fill="#000000" points="9.2,7.3 9.2,18.5 12.2,15.6 12.6,15.5 17.4,15.5"/>
            <rect x="12.5" y="13.6" transform="matrix(0.9221 -0.3871 0.3871 0.9221 -5.7605 6.5909)" width="2" height="8" fill="#000000"/>
          </svg>
          `;
          
          // Style the cursor
          cursor.style.position = 'absolute';
          cursor.style.top = '0';
          cursor.style.left = '0';
          cursor.style.width = '28px';
          cursor.style.height = '28px';
          cursor.style.pointerEvents = 'none';
          cursor.style.zIndex = '9999999';
          cursor.style.transform = 'translate(-4px, -4px)'; // Adjust to align the pointer tip
          
          // Create highlight element for click animation
          const highlight = document.createElement('div');
          highlight.id = highlightId;
          highlight.style.position = 'absolute';
          highlight.style.width = '20px';
          highlight.style.height = '20px';
          highlight.style.borderRadius = '50%';
          highlight.style.backgroundColor = 'rgba(66, 134, 244, 0)';
          highlight.style.transform = 'translate(-50%, -50%) scale(0)';
          highlight.style.pointerEvents = 'none';
          highlight.style.zIndex = '9999998';
          highlight.style.transition = 'transform 0.3s ease-out, opacity 0.3s ease-out';
          highlight.style.opacity = '0';
          
          // Add elements to the document
          document.body.appendChild(cursor);
          document.body.appendChild(highlight);
          
          // Add a function to update cursor position
          window.__updateCursorPosition = function(x, y) {{
            if (cursor) {{
              cursor.style.transform = `translate(${{x - 4}}px, ${{y - 4}}px)`;
            }}
          }};
          
          // Add a function to animate click
          window.__animateClick = function(x, y) {{
            if (highlight) {{
              highlight.style.left = `${{x}}px`;
              highlight.style.top = `${{y}}px`;
              highlight.style.transform = 'translate(-50%, -50%) scale(1)';
              highlight.style.opacity = '1';
              
              setTimeout(() => {{
                highlight.style.transform = 'translate(-50%, -50%) scale(0)';
                highlight.style.opacity = '0';
              }}, 300);
            }}
          }};
        }})('{cursor_id}', '{highlight_id}');
        """
        try:
            await self.page.evaluate(js_code)
            self.logger.info("Cursor injected successfully.", category=StagehandFunctionName.AGENT)
        except Exception as e:
            self.logger.error(f"Failed to inject cursor: {e}", category=StagehandFunctionName.AGENT)

    async def _update_cursor_position(self, x: int, y: int) -> None:
        """Update the cursor position on the page."""
        try:
            await self.page.evaluate(
                f"window.__updateCursorPosition({x}, {y})"
            )
        except Exception as e:
            self.logger.warning(f"Failed to update cursor position: {e}", category=StagehandFunctionName.AGENT)


    async def _animate_click(self, x: int, y: int) -> None:
        """Animate a click at the given position."""
        try:
            await self.page.evaluate(f"window.__animateClick({x}, {y})")
        except Exception as e:
            self.logger.warning(f"Failed to animate click: {e}", category=StagehandFunctionName.AGENT)


    def _convert_key_name(self, key: str) -> str:
        """Convert CUA key names to Playwright key names."""
        key_map = {
            "ENTER": "Enter",
            "RETURN": "Enter", # Added for Anthropic 'key' type if used via this
            "ESCAPE": "Escape",
            "ESC": "Escape", # Added
            "BACKSPACE": "Backspace",
            "TAB": "Tab",
            "SPACE": " ", # Represent space as " "
            "ARROWUP": "ArrowUp",
            "ARROWDOWN": "ArrowDown",
            "ARROWLEFT": "ArrowLeft",
            "ARROWRIGHT": "ArrowRight",
            "UP": "ArrowUp",
            "DOWN": "ArrowDown",
            "LEFT": "ArrowLeft",
            "RIGHT": "ArrowRight",
            "SHIFT": "Shift",
            "CONTROL": "Control",
            "CTRL": "Control", # Added
            "ALT": "Alt",
            "OPTION": "Alt", # Added
            "META": "Meta",
            "COMMAND": "Meta",
            "CMD": "Meta", # Added
            "DELETE": "Delete",
            "HOME": "Home",
            "END": "End",
            "PAGEUP": "PageUp",
            "PAGEDOWN": "PageDown",
        }
        # Convert to uppercase for case-insensitive matching then check map,
        # default to original key if not found.
        return key_map.get(key.upper(), key)
