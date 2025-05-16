from .client import AgentClient
from ..types import AgentConfig
from typing import Callable
from pprint import pprint as pp
import json
import litellm

BLOCKED_DOMAINS = [
    "maliciousbook.com",
    "evilvideos.com",
    "darkwebforum.com",
    "shadytok.com",
    "suspiciouspins.com",
    "ilanbigio.com",
]

class OpenAICUAClient(AgentClient):
    def __init__(
        self,
        model="computer-use-preview",
        acknowledge_safety_check_callback: Callable = lambda: False,
        config: AgentConfig = None,
    ):
        self.model = model
        self.print_steps = True
        self.debug = False
        self.show_images = False
        self.acknowledge_safety_check_callback = acknowledge_safety_check_callback

        dimensions = config.get("dimensions", [1024, 768])
        self.tools += [
            {
                "type": "computer-preview",
                "display_width": dimensions[0],
                "display_height": dimensions[1],
                "environment": "browser",
            },
        ]

    def debug_print(self, *args):
        if self.debug:
            pp(*args)

    def handle_item(self, item):
        """Handle each item; may cause a computer action + screenshot."""
        if item["type"] == "message":
            if self.print_steps:
                print(item["content"][0]["text"])

        if item["type"] == "computer_call":
            action = item["action"]
            action_type = action["type"]
            action_args = {k: v for k, v in action.items() if k != "type"}
            if self.print_steps:
                print(f"{action_type}({action_args})")

            method = getattr(self.computer, action_type)
            method(**action_args)

            screenshot_base64 = self.computer.screenshot()

            # if user doesn't ack all safety checks exit with error
            pending_checks = item.get("pending_safety_checks", [])
            for check in pending_checks:
                message = check["message"]
                if not self.acknowledge_safety_check_callback(message):
                    raise ValueError(
                        f"Safety check failed: {message}. Cannot continue with unacknowledged safety checks."
                    )

            call_output = {
                "type": "computer_call_output",
                "call_id": item["call_id"],
                "acknowledged_safety_checks": pending_checks,
                "output": {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{screenshot_base64}",
                },
            }

            # additional URL safety checks for browser environments
            if self.computer.get_environment() == "browser":
                current_url = self.computer.get_current_url()
                check_blocklisted_url(current_url)
                call_output["output"]["current_url"] = current_url

            return [call_output]
        return []

    def run_full_turn(
        self, input_items, print_steps=True, debug=False, show_images=False
    ):
        self.print_steps = print_steps
        self.debug = debug
        self.show_images = show_images
        new_items = []

        # keep looping until we get a final response
        while new_items[-1].get("role") != "assistant" if new_items else True:
            self.debug_print([self.sanitize_message(msg) for msg in input_items + new_items])

            response = litellm.responses(
                model=self.model,
                input=input_items + new_items,
                tools=self.tools,
                reasoning={
                    "summary":"concise",
                },
                truncation="auto",
            )
            self.debug_print(response)

            if "output" not in response and self.debug:
                print(response)
                raise ValueError("No output from model")
            else:
                new_items += response["output"]
                for item in response["output"]:
                    new_items += self.handle_item(item)

        return new_items
    
    def sanitize_message(msg: dict) -> dict:
      """Return a copy of the message with image_url omitted for computer_call_output messages."""
      if msg.get("type") == "computer_call_output":
          output = msg.get("output", {})
          if isinstance(output, dict):
              sanitized = msg.copy()
              sanitized["output"] = {**output, "image_url": "[omitted]"}
              return sanitized
      return msg

