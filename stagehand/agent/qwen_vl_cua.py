"""
Qwen3-VL CUA (Computer Use Agent) Client for Stagehand.

This module provides support for Qwen3-VL models through the DashScope API
(compatible with OpenAI SDK format). The model returns coordinates normalized
to [0, 999] which are converted to actual pixel coordinates.
"""

import asyncio
import json
import os
import re
from typing import Any, Optional

from dotenv import load_dotenv
from openai import OpenAI as OpenAISDK
from pydantic import TypeAdapter

from ..handlers.cua_handler import CUAHandler, StagehandFunctionName
from ..types.agent import (
    ActionExecutionResult,
    AgentAction,
    AgentActionType,
    AgentConfig,
    AgentExecuteOptions,
    AgentResult,
    AgentUsage,
    FunctionArguments,
)
from .client import AgentClient

load_dotenv()

# Default DashScope API endpoint
DEFAULT_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# System prompt to guide the model to return structured actions
QWEN_VL_SYSTEM_PROMPT = """You are a browser automation assistant that helps users interact with web pages.
When given a screenshot of a web page and an instruction, analyze the page and determine what action to take.

You must respond in JSON format with one of the following action types:

1. Click action - click on a specific point:
{
    "action": "click",
    "point_2d": [x, y],
    "label": "description of what you're clicking"
}

2. Type action - type text (optionally at a specific point):
{
    "action": "type",
    "text": "text to type",
    "point_2d": [x, y],  // optional, if clicking before typing
    "label": "description of where you're typing"
}

3. Scroll action - scroll the page:
{
    "action": "scroll",
    "direction": "up" | "down" | "left" | "right",
    "point_2d": [x, y],  // optional, scroll position
    "label": "description of scroll action"
}

4. Keypress action - press keyboard keys:
{
    "action": "keypress",
    "keys": ["key1", "key2"],  // e.g., ["Enter"], ["Control", "a"]
    "label": "description of key action"
}

5. Navigate action - go to a URL:
{
    "action": "goto",
    "url": "https://example.com",
    "label": "description of navigation"
}

6. Wait action - wait for page to load:
{
    "action": "wait",
    "milliseconds": 1000,
    "label": "waiting for page"
}

7. Done action - task is complete:
{
    "action": "done",
    "message": "description of what was accomplished",
    "label": "task complete"
}

IMPORTANT:
- Coordinates (point_2d) are normalized to [0, 999] range where (0,0) is top-left and (999,999) is bottom-right
- Always analyze the screenshot carefully before deciding on an action
- If you cannot find the target element, describe what you see and suggest next steps
- If the task is complete, use the "done" action
- Always include a "label" field describing your action
- Respond ONLY with valid JSON, no additional text"""


class QwenVLCUAClient(AgentClient):
    """
    Computer Use Agent client for Qwen3-VL models via DashScope API.

    Supports Qwen3-VL series models which return coordinates normalized to [0, 999].
    Uses OpenAI-compatible API format through DashScope.
    """

    def __init__(
        self,
        model: str = "qwen3-vl-max",
        instructions: Optional[str] = None,
        config: Optional[AgentConfig] = None,
        logger: Optional[Any] = None,
        handler: Optional[CUAHandler] = None,
        viewport: Optional[dict[str, int]] = None,
        **kwargs,
    ):
        super().__init__(model, instructions, config, logger, handler)

        # Get API key from config options or environment
        api_key = None
        base_url = DEFAULT_DASHSCOPE_BASE_URL

        if config and config.options:
            api_key = config.options.get("apiKey")
            if config.options.get("baseUrl"):
                base_url = config.options.get("baseUrl")

        if not api_key:
            api_key = os.getenv("DASHSCOPE_API_KEY")

        if not api_key:
            raise ValueError(
                "DASHSCOPE_API_KEY environment variable not set and not provided in config options."
            )

        # Initialize OpenAI SDK with DashScope endpoint
        self.openai_sdk_client = OpenAISDK(
            api_key=api_key,
            base_url=base_url,
        )

        # Set display dimensions from viewport
        self.display_width = viewport["width"] if viewport else 1288
        self.display_height = viewport["height"] if viewport else 711

        if self.config:
            if hasattr(self.config, "display_width") and self.config.display_width:
                self.display_width = self.config.display_width
            if hasattr(self.config, "display_height") and self.config.display_height:
                self.display_height = self.config.display_height

        # Combine system prompt with custom instructions
        self.system_prompt = QWEN_VL_SYSTEM_PROMPT
        if instructions:
            self.system_prompt = f"{QWEN_VL_SYSTEM_PROMPT}\n\nAdditional instructions:\n{instructions}"

        self.conversation_history: list[dict[str, Any]] = []

        self.logger.info(
            f"QwenVLCUAClient initialized for model: {model}, dimensions: {self.display_width}x{self.display_height}",
            category=StagehandFunctionName.AGENT,
        )

    def _normalize_coordinates(self, x: int, y: int) -> tuple[int, int]:
        """
        Convert normalized coordinates [0, 999] to actual pixel coordinates.

        Args:
            x: Normalized x coordinate (0-999)
            y: Normalized y coordinate (0-999)

        Returns:
            Tuple of (pixel_x, pixel_y)
        """
        pixel_x = int(x / 1000 * self.display_width)
        pixel_y = int(y / 1000 * self.display_height)
        return pixel_x, pixel_y

    def format_screenshot(self, screenshot_base64: str) -> dict[str, Any]:
        """Format a screenshot for the Qwen VL model."""
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"},
        }

    def _format_initial_messages(
        self, instruction: str, screenshot_base64: Optional[str]
    ) -> list[dict[str, Any]]:
        """Prepare the initial messages for the Qwen VL model."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt}
        ]

        user_content: list[dict[str, Any]] = []
        if screenshot_base64:
            user_content.append(self.format_screenshot(screenshot_base64))
        user_content.append({"type": "text", "text": instruction})

        messages.append({"role": "user", "content": user_content})
        self.conversation_history = messages.copy()
        return messages

    def _parse_json_response(self, text: str) -> Optional[dict[str, Any]]:
        """
        Parse JSON response from model output, handling markdown code blocks.

        Args:
            text: Raw text response from the model

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in text:
                match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
                if match:
                    text = match.group(1)
            elif "```" in text:
                match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
                if match:
                    text = match.group(1)

            # Try to find JSON object in text
            text = text.strip()
            if not text.startswith("{"):
                # Try to find JSON object anywhere in text
                match = re.search(r"\{.*\}", text, re.DOTALL)
                if match:
                    text = match.group(0)

            return json.loads(text)
        except json.JSONDecodeError as e:
            self.logger.error(
                f"Failed to parse JSON response: {e}. Raw text: {text[:200]}",
                category=StagehandFunctionName.AGENT,
            )
            return None

    def _process_provider_response(
        self, response: Any
    ) -> tuple[Optional[AgentAction], Optional[str], bool, Optional[str]]:
        """
        Parse the response from Qwen VL model.

        Returns:
            - AgentAction (if an action is to be performed)
            - Reasoning text (label/description from model)
            - Boolean indicating if the task is complete
            - Message from the model (if any)
        """
        if not response.choices or not response.choices[0].message:
            self.logger.error(
                "No response content from Qwen VL model",
                category=StagehandFunctionName.AGENT,
            )
            return None, "Error: No response from model", True, "Error: No response from model"

        message_content = response.choices[0].message.content
        if not message_content:
            return None, None, True, "No content in model response"

        # Parse the JSON response
        parsed = self._parse_json_response(message_content)
        if not parsed:
            return None, message_content, True, f"Failed to parse model response: {message_content[:200]}"

        action_type = parsed.get("action", "").lower()
        label = parsed.get("label", "")

        # Check if task is done
        if action_type == "done":
            return None, label, True, parsed.get("message", "Task completed")

        agent_action: Optional[AgentAction] = None
        action_payload_dict: Optional[dict[str, Any]] = None

        try:
            if action_type == "click":
                point_2d = parsed.get("point_2d", [])
                if len(point_2d) >= 2:
                    x, y = self._normalize_coordinates(
                        point_2d[0], point_2d[1])
                    action_payload_dict = {
                        "type": "click",
                        "x": x,
                        "y": y,
                        "button": parsed.get("button", "left"),
                    }
                else:
                    return None, label, True, "Click action missing coordinates"

            elif action_type == "double_click":
                point_2d = parsed.get("point_2d", [])
                if len(point_2d) >= 2:
                    x, y = self._normalize_coordinates(
                        point_2d[0], point_2d[1])
                    action_payload_dict = {
                        "type": "double_click",
                        "x": x,
                        "y": y,
                    }
                else:
                    return None, label, True, "Double click action missing coordinates"

            elif action_type == "type":
                text = parsed.get("text", "")
                point_2d = parsed.get("point_2d")

                if point_2d and len(point_2d) >= 2:
                    x, y = self._normalize_coordinates(
                        point_2d[0], point_2d[1])
                    action_payload_dict = {
                        "type": "type",
                        "text": text,
                        "x": x,
                        "y": y,
                        "press_enter_after": parsed.get("press_enter_after", False),
                    }
                else:
                    action_payload_dict = {
                        "type": "type",
                        "text": text,
                        "press_enter_after": parsed.get("press_enter_after", False),
                    }

            elif action_type == "scroll":
                direction = parsed.get("direction", "down").lower()
                # Default to center
                point_2d = parsed.get("point_2d", [500, 500])
                x, y = self._normalize_coordinates(point_2d[0], point_2d[1])

                scroll_amount = parsed.get("amount", 300)
                scroll_x = 0
                scroll_y = 0

                if direction == "down":
                    scroll_y = scroll_amount
                elif direction == "up":
                    scroll_y = -scroll_amount
                elif direction == "right":
                    scroll_x = scroll_amount
                elif direction == "left":
                    scroll_x = -scroll_amount

                action_payload_dict = {
                    "type": "scroll",
                    "x": x,
                    "y": y,
                    "scroll_x": scroll_x,
                    "scroll_y": scroll_y,
                }

            elif action_type == "keypress":
                keys = parsed.get("keys", [])
                if keys:
                    playwright_keys = [self.key_to_playwright(k) for k in keys]
                    action_payload_dict = {
                        "type": "keypress",
                        "keys": playwright_keys,
                    }
                else:
                    return None, label, True, "Keypress action missing keys"

            elif action_type == "goto":
                url = parsed.get("url", "")
                if url:
                    action_payload_dict = {
                        "type": "function",
                        "name": "goto",
                        "arguments": FunctionArguments(url=url),
                    }
                    action_type = "function"
                else:
                    return None, label, True, "Goto action missing URL"

            elif action_type == "navigate_back":
                action_payload_dict = {
                    "type": "function",
                    "name": "navigate_back",
                    "arguments": FunctionArguments(url=""),
                }
                action_type = "function"

            elif action_type == "wait":
                milliseconds = parsed.get("milliseconds", 1000)
                action_payload_dict = {
                    "type": "wait",
                    "miliseconds": milliseconds,
                }

            elif action_type == "move":
                point_2d = parsed.get("point_2d", [])
                if len(point_2d) >= 2:
                    x, y = self._normalize_coordinates(
                        point_2d[0], point_2d[1])
                    action_payload_dict = {
                        "type": "move",
                        "x": x,
                        "y": y,
                    }
                else:
                    return None, label, True, "Move action missing coordinates"

            elif action_type == "screenshot":
                action_payload_dict = {"type": "screenshot"}

            else:
                self.logger.error(
                    f"Unsupported action type from Qwen VL: {action_type}",
                    category=StagehandFunctionName.AGENT,
                )
                return None, label, True, f"Unsupported action type: {action_type}"

            if action_payload_dict:
                action_model_payload = TypeAdapter(AgentActionType).validate_python(
                    action_payload_dict
                )
                agent_action = AgentAction(
                    action_type=action_type,
                    action=action_model_payload,
                    reasoning=label,
                )

        except Exception as e:
            self.logger.error(
                f"Error processing Qwen VL action '{action_type}': {e}",
                category=StagehandFunctionName.AGENT,
            )
            return None, label, True, f"Error processing action: {e}"

        return agent_action, label, False, None

    def _format_action_feedback(
        self,
        action: AgentAction,
        action_result: ActionExecutionResult,
        new_screenshot_base64: str,
        current_url: Optional[str] = None,
    ) -> list[Any]:
        """Format the feedback message after an action is performed."""
        content: list[dict[str, Any]] = []

        # Add screenshot
        if new_screenshot_base64:
            content.append(self.format_screenshot(new_screenshot_base64))

        # Add result text
        if action_result.get("success"):
            result_text = f"Action '{action.action_type}' completed successfully."
            if action.reasoning:
                result_text += f" ({action.reasoning})"
        else:
            error = action_result.get("error", "Unknown error")
            result_text = f"Action '{action.action_type}' failed: {error}"

        if current_url:
            result_text += f"\nCurrent URL: {current_url}"

        result_text += "\n\nWhat should I do next? Continue with the task or respond with a 'done' action if complete."

        content.append({"type": "text", "text": result_text})

        return {"role": "user", "content": content}

    async def run_task(
        self,
        instruction: str,
        max_steps: int = 20,
        options: Optional[AgentExecuteOptions] = None,
    ) -> AgentResult:
        """
        Run a task using the Qwen VL model.

        Args:
            instruction: The task instruction
            max_steps: Maximum number of steps to take
            options: Additional execution options

        Returns:
            AgentResult with actions taken and completion status
        """
        if self.config and self.config.max_steps is not None:
            max_steps = self.config.max_steps

        self.logger.debug(
            f"Qwen VL CUA starting task: '{instruction}' with max_steps: {max_steps}",
            category=StagehandFunctionName.AGENT,
        )

        if not self.handler:
            self.logger.error(
                "CUAHandler not available for QwenVLCUAClient.",
                category=StagehandFunctionName.AGENT,
            )
            return AgentResult(
                completed=False,
                actions=[],
                message="Internal error: Handler not set.",
                usage=AgentUsage(
                    input_tokens=0, output_tokens=0, inference_time_ms=0),
            )

        await self.handler.inject_cursor()
        current_screenshot_b64 = await self.handler.get_screenshot_base64()

        # Initialize conversation
        messages = self._format_initial_messages(
            instruction, current_screenshot_b64)

        actions_taken: list[AgentAction] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_inference_time_ms = 0
        final_model_message: Optional[str] = None

        for step_count in range(max_steps):
            self.logger.info(
                f"Qwen VL CUA - Step {step_count + 1}/{max_steps}",
                category=StagehandFunctionName.AGENT,
            )

            start_time = asyncio.get_event_loop().time()
            try:
                # Use asyncio.to_thread to avoid blocking the event loop
                response = await asyncio.to_thread(
                    self.openai_sdk_client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    max_tokens=1024,
                )
                end_time = asyncio.get_event_loop().time()
                total_inference_time_ms += int((end_time - start_time) * 1000)

                # Track token usage
                if hasattr(response, "usage") and response.usage:
                    total_input_tokens += response.usage.prompt_tokens or 0
                    total_output_tokens += response.usage.completion_tokens or 0

            except Exception as e:
                self.logger.error(
                    f"Qwen VL API call failed: {e}",
                    category=StagehandFunctionName.AGENT,
                )
                return AgentResult(
                    actions=[act.action for act in actions_taken if act.action],
                    message=f"Qwen VL API error: {e}",
                    completed=False,
                    usage=AgentUsage(
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                        inference_time_ms=total_inference_time_ms,
                    ),
                )

            # Process the response
            agent_action, reasoning_text, task_completed, model_message = (
                self._process_provider_response(response)
            )

            # Add assistant response to history
            if response.choices and response.choices[0].message:
                messages.append({
                    "role": "assistant",
                    "content": response.choices[0].message.content or "",
                })

            if reasoning_text:
                self.logger.info(
                    f"Model reasoning: {reasoning_text}",
                    category=StagehandFunctionName.AGENT,
                )

            if model_message:
                final_model_message = model_message

            if agent_action:
                actions_taken.append(agent_action)

                # Execute the action
                action_result: ActionExecutionResult = await self.handler.perform_action(
                    agent_action
                )

                # Get new screenshot
                current_screenshot_b64 = await self.handler.get_screenshot_base64()
                current_url = self.handler.page.url if self.handler.page else None

                # Add feedback to conversation
                feedback = self._format_action_feedback(
                    action=agent_action,
                    action_result=action_result,
                    new_screenshot_base64=current_screenshot_b64,
                    current_url=current_url,
                )
                messages.append(feedback)

            if task_completed:
                self.logger.info(
                    f"Task marked complete by model. Final message: {final_model_message}",
                    category=StagehandFunctionName.AGENT,
                )
                break

            if not agent_action and not task_completed:
                self.logger.info(
                    "Model did not request an action and task not marked complete. Ending task.",
                    category=StagehandFunctionName.AGENT,
                )
                final_model_message = "Model did not provide further actions."
                break

        usage_obj = AgentUsage(
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            inference_time_ms=total_inference_time_ms,
        )

        return AgentResult(
            actions=[act.action for act in actions_taken if act.action],
            message=final_model_message or "Max steps reached or task ended.",
            completed=task_completed if "task_completed" in locals() else False,
            usage=usage_obj,
        )

    def key_to_playwright(self, key: str) -> str:
        """Convert key names to Playwright-compatible key names."""
        key_map = {
            "enter": "Enter",
            "return": "Enter",
            "escape": "Escape",
            "esc": "Escape",
            "tab": "Tab",
            "backspace": "Backspace",
            "delete": "Delete",
            "space": " ",
            "arrowup": "ArrowUp",
            "arrowdown": "ArrowDown",
            "arrowleft": "ArrowLeft",
            "arrowright": "ArrowRight",
            "up": "ArrowUp",
            "down": "ArrowDown",
            "left": "ArrowLeft",
            "right": "ArrowRight",
            "shift": "Shift",
            "control": "Control",
            "ctrl": "Control",
            "alt": "Alt",
            "meta": "Meta",
            "command": "Meta",
            "cmd": "Meta",
            "home": "Home",
            "end": "End",
            "pageup": "PageUp",
            "pagedown": "PageDown",
        }
        return key_map.get(key.lower(), key)
