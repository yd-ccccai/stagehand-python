from __future__ import annotations

from typing import Any, Dict, List


def build_openai_tools_schemas() -> List[Dict[str, Any]]:
    """
    Return the OpenAI-style tool schema list used by the Native Agent.

    Shapes follow the Responses API tools format:
    {"type": "function", "function": {"name": str, "description": str, "parameters": JSONSchema}}
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "goto",
                "description": "Navigate the browser to a specific absolute URL.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Absolute URL including protocol, e.g. https://example.com",
                            "format": "uri",
                        }
                    },
                    "required": ["url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "navback",
                "description": "Navigate back to the previous page in history.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reasoning": {"type": "string", "description": "Why navigate back"}
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "act",
                "description": "Perform a high-level action described in natural language (click, type, etc).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "Action command, e.g. 'click the Login button' or 'type %value% into email input'",
                        },
                        "variables": {
                            "type": "object",
                            "additionalProperties": {"type": ["string", "number", "boolean"]},
                            "description": "Optional key-value variables for placeholder substitution, commonly { value: string }",
                        },
                    },
                    "required": ["action"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fillForm",
                "description": "Efficiently fill multiple inputs in a form using a list of field actions and values.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fields": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "action": {"type": "string", "description": "Action text with %value% placeholder"},
                                    "value": {"type": "string", "description": "Text to type"},
                                },
                                "required": ["action", "value"],
                            },
                            "minItems": 1,
                        }
                    },
                    "required": ["fields"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "extract",
                "description": "Extract structured data from the current page using the accessibility tree and an optional JSON schema.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "instruction": {"type": "string", "description": "What to extract"},
                        "schema": {
                            "type": ["object", "null"],
                            "description": "Optional JSON schema that defines expected structure (Pydantic schema also acceptable)",
                        },
                    },
                    "required": ["instruction"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "ariaTree",
                "description": "Return a simplified accessibility tree of the current page for context.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "screenshot",
                "description": "Capture a screenshot of the current page.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "scroll",
                "description": "Scroll the page vertically by a number of pixels.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pixels": {"type": "integer", "minimum": 1, "description": "Positive number of pixels"},
                        "direction": {"type": "string", "enum": ["up", "down"]},
                    },
                    "required": ["pixels", "direction"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "wait",
                "description": "Pause for a number of milliseconds.",
                "parameters": {
                    "type": "object",
                    "properties": {"timeMs": {"type": "integer", "minimum": 0}},
                    "required": ["timeMs"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "close",
                "description": "End the task with a success/failure and summary.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reasoning": {"type": "string"},
                        "success": {"type": "boolean"},
                    },
                    "required": ["reasoning", "success"],
                },
            },
        },
    ]


__all__ = ["build_openai_tools_schemas"]
