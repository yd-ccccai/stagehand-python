"""Inference module for calling LLMs to perform various tasks."""

import json
import time
from typing import Any, Callable, Optional

from stagehand.llm.prompts import (
    build_observe_system_prompt,
    build_observe_user_message,
)
from stagehand.types import (
    ObserveInferenceSchema,
)


# TODO: kwargs
def observe(
    instruction: str,
    tree_elements: str,
    llm_client: Any,
    request_id: str,
    user_provided_instructions: Optional[str] = None,
    logger: Optional[Callable] = None,
    log_inference_to_file: bool = False,
    from_act: bool = False,
) -> dict[str, Any]:
    """
    Call LLM to find elements in the DOM/accessibility tree based on an instruction.

    Args:
        instruction: The instruction to follow when finding elements
        tree_elements: String representation of DOM/accessibility tree elements
        llm_client: Client for calling LLM
        request_id: Unique ID for this request
        user_provided_instructions: Optional custom system instructions
        logger: Optional logger function
        log_inference_to_file: Whether to log inference to file
        from_act: Whether this observe call is part of an act operation

    Returns:
        dict containing elements found and token usage information
    """

    # Build the prompts
    system_prompt = build_observe_system_prompt(
        user_provided_instructions=user_provided_instructions,
    )

    user_prompt = build_observe_user_message(
        instruction=instruction,
        tree_elements=tree_elements,
    )

    messages = [
        system_prompt,
        user_prompt,
    ]

    start_time = time.time()

    try:
        # Call the LLM
        logger.info("Calling LLM")
        response = llm_client.create_response(
            model=llm_client.default_model,
            messages=messages,
            response_format=ObserveInferenceSchema,
            temperature=0.1,
            request_id=request_id,
        )
        inference_time_ms = int((time.time() - start_time) * 1000)

        # Extract token counts
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens

        # Parse the response
        content = response.choices[0].message.content
        logger.info(f"LLM Response: {content}")
        if isinstance(content, str):
            try:
                parsed_response = json.loads(content)
            except json.JSONDecodeError:
                if logger:
                    logger.error(f"Failed to parse JSON response: {content}")
                parsed_response = {"elements": []}
        else:
            parsed_response = content

        elements = parsed_response.get("elements", [])

        return {
            "elements": elements,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "inference_time_ms": inference_time_ms,
        }

    except Exception as e:
        if logger:
            logger.error(f"Error in observe inference: {str(e)}")

        # Return empty response on error
        return {
            "elements": [],
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "inference_time_ms": int((time.time() - start_time) * 1000),
        }
