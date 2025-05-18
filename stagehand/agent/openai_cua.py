import os
import base64
import json # For formatting tool feedback if necessary
from typing import Any, Tuple, Optional
from dotenv import load_dotenv
from openai import OpenAI as OpenAISDK # Renamed to avoid conflict with a potential class name
from pydantic import BaseModel # Ensure BaseModel is imported for isinstance check

from ..types.agent import AgentConfig, AgentAction, AgentActionType, AgentExecuteOptions, AgentResult, ActionExecutionResult
from .client import AgentClient
from ..handlers.cua_handler import CUAHandler

load_dotenv()

# CUA_KEY_TO_PLAYWRIGHT_KEY can be defined here if OpenAI CUA has specific key names
# that need mapping before creating an AgentAction that CUAHandler would consume.
# For now, assuming CUAHandler._convert_key_name is sufficient.
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

class OpenAICUAClient(AgentClient):
    def __init__(
        self,
        model: str = "computer-use-preview",
        instructions: Optional[str] = None, # System prompt
        config: Optional[AgentConfig] = None,
        logger: Optional[Any] = None,
        handler: Optional[CUAHandler] = None,
        **kwargs, # Allow for other OpenAI specific options if any
    ):
        super().__init__(model, instructions, config, logger, handler) # type: ignore
        self.openai_sdk_client = OpenAISDK(api_key=os.getenv("OPENAI_API_KEY"))
        
        dimensions = [1024, 768] # Default or from self.config if specified
        if self.config and hasattr(self.config, 'display_width') and hasattr(self.config, 'display_height'):
            dimensions = [self.config.display_width, self.config.display_height] # type: ignore
            
        self.tools = [
            {
                "type": "computer_use_preview",
                "display_width": dimensions[0],
                "display_height": dimensions[1],
                "environment": "browser", # Or from config if variable
            },
        ]
        self.max_steps = self.config.max_steps if self.config and self.config.max_steps is not None else 20
        self.last_openai_tool_calls: Optional[list[Any]] = None # To store tool_calls from assistant response

    def format_screenshot(self, screenshot_base64: str) -> dict:
        """Formats a screenshot for the OpenAI CUA model."""
        return {
            "type": "input_image",
            "image_url": f"data:image/png;base64,{screenshot_base64}",
        }

    def _format_initial_messages(self, instruction: str, screenshot_base64: Optional[str]) -> list[Any]:
        messages: list[Any] = []
        if self.instructions: # System prompt from AgentConfig.instructions
            messages.append({"role": "system", "content": self.instructions})
        
        user_content: list[Any] = [{"type": "input_text", "text": instruction}]
        if screenshot_base64:
            user_content.append(self.format_screenshot(screenshot_base64))
        messages.append({"role": "user", "content": user_content})
        return messages

    def _process_provider_response(self, response: Any) -> Tuple[Optional[AgentAction], Optional[str], bool, Optional[str]]:
        """Processes the raw response from OpenAI CUA, expecting openai.types.beta.assistant_response.AssistantResponse object"""
        # This method now needs to handle the new structure where `response` is the direct SDK object.
        # We are interested in assistant messages that contain `tool_calls` (for actions) or final text content.

        # Assuming response is the object returned by openai_sdk_client.chat.completions.create with tool_choice
        # or similar that yields tool_calls.
        # For CUA, the `openai.responses.create` is different. Let's adapt from the old `create_response`

        # This was the old logic from the user's initial openai_cua.py for `response.output`
        # It needs to be adapted if `response` object structure from `openai_sdk_client.responses.create` is different.
        # Let's assume `response` here IS the `openai_sdk_client.responses.create(...)` raw response object.

        if not response.output: # `response.output` was from the older version
            self.logger.error("No output from OpenAI model in response object", category="agent")
            return None, "Error: No output from model", True, "Error: No output from model"

        output_items = response.output # This is a list of ResponseItem objects
        
        computer_call_items = [item for item in output_items if item.type == "computer_call"]
        reasoning_items = [item for item in output_items if item.type == "reasoning"]
        message_items = [item for item in output_items if item.type == "message"]

        reasoning_text = None
        if reasoning_items and reasoning_items[0].summary and isinstance(reasoning_items[0].summary, list) and len(reasoning_items[0].summary) > 0:
            # Assuming summary is a list of objects with a 'text' attribute
            reasoning_text = reasoning_items[0].summary[0].text

        final_model_message = None
        if message_items and message_items[0].content and isinstance(message_items[0].content, list):
            final_model_message_parts = [content_item.text for content_item in message_items[0].content if hasattr(content_item, 'text') and content_item.type == 'output_text']
            if final_model_message_parts:
                final_model_message = " ".join(final_model_message_parts)

        if not computer_call_items:
            task_complete_reason = final_model_message if final_model_message else "No further actions from model."
            self.logger.info(f"OpenAI CUA: Task appears complete. Reason: {task_complete_reason}", category="agent")
            self.last_openai_tool_calls = None # Clear any stored tool calls
            return None, reasoning_text, True, final_model_message

        # Handle the first computer_call for now
        computer_call = computer_call_items[0]
        self.last_openai_tool_calls = [computer_call] # Store the call for feedback, specifically its `call_id`
        
        # Defensive check for computer_call.action type
        if not hasattr(computer_call, 'action') or not isinstance(computer_call.action, BaseModel):
            self.logger.error(f"OpenAI computer_call.action is not a Pydantic model or is missing. Type: {type(computer_call.action if hasattr(computer_call, 'action') else None)}. Content: {computer_call.action if hasattr(computer_call, 'action') else 'N/A'}", category="agent")
            # Return an error state or raise an exception to be caught by run_task
            return None, reasoning_text, True, f"Error: Invalid action structure from OpenAI for computer_call: {computer_call.id if hasattr(computer_call, 'id') else 'Unknown ID'}"

        action_payload = AgentActionType(**computer_call.action.model_dump())
        agent_action = AgentAction(
            action_type=computer_call.action.type,
            action=action_payload,
            reasoning=reasoning_text,
            status=computer_call.status,
            step=[item.model_dump() for item in output_items],
        )
        return agent_action, reasoning_text, False, final_model_message

    def _format_action_feedback(self, action_result: ActionExecutionResult, new_screenshot_base64: str) -> list[Any]:
        """Formats the feedback for OpenAI CUA after an action is performed."""
        if not self.last_openai_tool_calls or not self.last_openai_tool_calls[0].call_id:
            self.logger.error("Missing last_openai_tool_calls or call_id for formatting action feedback.", category="agent")
            # Fallback if call_id is missing (this is problematic for OpenAI)
            return [{
                "role": "user", 
                "content": [{"type": "output_text", "text": "Error: Could not associate action feedback with a tool call."}]
            }]

        call_id = self.last_openai_tool_calls[0].call_id
        
        # Structure for computer_call_output according to OpenAI CUA
        output_content: dict[str, Any]
        if action_result["success"]:
            output_content = self.format_screenshot(new_screenshot_base64) # This is already a dict {type: input_image, ...}
        else:
            output_content = {
                "type": "output_text", # Check if error should be output_text or error object
                "text": f"Action failed: {action_result.get('error', 'Unknown error')}"
            }
        
        # The input for the next `responses.create` call needs to be a list of messages.
        # The feedback for a computer_call is provided as a `computer_call_output` item within the `input` list.
        # This is distinct from Chat Completions API's `role: tool` messages.
        # Refer to OpenAI CUA `responses.create` API for exact structure.
        # It should be an item in the `input` list, not a message itself.
        # Example: { "type": "computer_call_output", "call_id": call_id, "output": output_content }
        # This item is then part of the *next* `input` array for `responses.create()`.

        # This method returns items to be *added* to the ongoing message/input list for the *next* API call.
        # The `run_task` loop will append these to its `current_input_items` list.
        return [
            {
                "type": "computer_call_output",
                "call_id": call_id,
                "output": output_content
            }
        ]

    async def run_task(self, instruction: str, options: Optional[AgentExecuteOptions] = None) -> AgentResult:
        self.logger.info(f"OpenAI CUA starting task: '{instruction}'", category="agent")
        
        if not self.handler: # Should be caught by Agent init, but good check
            self.logger.error("CUAHandler not available for OpenAIClient.", category="agent")
            return AgentResult(success=False, message="Internal error: Handler not set.", completed=True, actions=[], usage={}) # type: ignore

        await self.handler.inject_cursor()
        current_screenshot_b64 = await self.handler.get_screenshot_base64()
        
        # `current_input_items` will be the list passed to `openai_sdk_client.responses.create(input=...)`
        current_input_items: list[Any] = self._format_initial_messages(instruction, current_screenshot_b64)
        
        actions_taken: list[AgentAction] = []
        total_input_tokens = 0 # Placeholder, OpenAI CUA Python SDK might not expose this directly per call
        total_output_tokens = 0 # Placeholder

        for step_count in range(self.max_steps):
            self.logger.info(f"OpenAI CUA - Step {step_count + 1}/{self.max_steps}", category="agent", auxiliary={'current_input_items_count': len(current_input_items)})
            
            try:
                # `previous_response_id` can be added if the API supports it and we track `response.id`
                # For now, we rebuild the input list each time.
                response = self.openai_sdk_client.responses.create(
                    model=self.model,
                    input=current_input_items,
                    tools=self.tools, # This specifies the CUA tool capabilities
                    reasoning={"summary": "concise"}, # Example, adjust as needed
                    truncation="auto",
                    # previous_response_id=self.last_response_id if hasattr(self, 'last_response_id') else None
                )
                # self.last_response_id = response.id # If tracking for pagination/context
                self.logger.info(f"{response}")
            except Exception as e:
                self.logger.error(f"OpenAI API call failed: {e}", exc_info=True, category="agent")
                return AgentResult(success=False, actions=actions_taken, message=f"OpenAI API error: {e}", completed=True, usage={}) # type: ignore

            # Usage from OpenAI CUA response (if available, structure may vary)
            # if hasattr(response, 'usage') and response.usage:
            #     total_input_tokens += response.usage.input_tokens
            #     total_output_tokens += response.usage.output_tokens

            agent_action, reasoning_text, task_completed, final_model_message = self._process_provider_response(response)
            
            # Append assistant's response (reasoning/message) to input for next turn
            # The structure of assistant's response in `input` list needs to be according to OpenAI CUA spec
            # This is NOT like role="assistant" in Chat Completions. `response.output` becomes part of the input.
            # Essentially, `response.output` (which contains reasoning, messages, computer_calls) IS the assistant's turn.
            # So, we add these `response.output` items to `current_input_items` for the next iteration if needed.
            # The `_format_action_feedback` already returns items to be added to this list.
            
            # Add the raw items from the assistant's last turn (output_items from _process_provider_response)
            # This ensures the model has context of its own previous reasoning and computer_calls.
            current_input_items.extend(response.output) # output is list[ResponseItem]

            if reasoning_text:
                self.logger.info(f"Model reasoning: {reasoning_text}", category="agent")
                # Reasoning is already part of `response.output` which was added above.

            if agent_action:
                self.logger.info(
                    f"Executing action: {agent_action.action_type}", 
                    category="agent", 
                    auxiliary=agent_action.action.model_dump() if agent_action.action else None
                )
                actions_taken.append(agent_action)
                
                action_result: ActionExecutionResult = await self.handler.perform_action(agent_action)
                current_screenshot_b64 = await self.handler.get_screenshot_base64() # Get new state
                
                feedback_items = self._format_action_feedback(action_result, current_screenshot_b64)
                current_input_items.extend(feedback_items) # Add feedback for the action to the input list
            
            if task_completed:
                self.logger.info(f"Task marked complete by model. Final message: {final_model_message}", category="agent")
                return AgentResult(
                    success=True, 
                    actions=actions_taken, 
                    message=final_model_message or "Task completed.", 
                    completed=True, 
                    usage={"input_tokens": total_input_tokens, "output_tokens": total_output_tokens} # type: ignore
                )

            if not agent_action and not task_completed:
                # Model did not request an action but didn't explicitly complete. Could be an error or loop.
                self.logger.warning("Model did not request an action and task not marked complete. Ending task to prevent loop.", category="agent")
                return AgentResult(
                    success=False, 
                    actions=actions_taken, 
                    message="Model did not provide further actions.", 
                    completed=False, # Or True, depending on desired outcome
                    usage={"input_tokens": total_input_tokens, "output_tokens": total_output_tokens} # type: ignore
                )

        self.logger.warning("Max steps reached for OpenAI CUA task.", category="agent")
        return AgentResult(
            success=False, 
            actions=actions_taken, 
            message="Max steps reached.", 
            completed=False, 
            usage={"input_tokens": total_input_tokens, "output_tokens": total_output_tokens} # type: ignore
        )

    def key_to_playwright(self, key: str) -> str:
        """Converts a key name if OpenAI CUA uses specific names not covered by CUAHandler."""
        # For now, assume CUAHandler._convert_key_name is sufficient.
        return CUA_KEY_TO_PLAYWRIGHT_KEY.get(key, key)