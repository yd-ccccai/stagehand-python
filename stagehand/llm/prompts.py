import json
from typing import Any, Optional

from stagehand.handlers.act_handler_utils import method_handler_map
from stagehand.types.llm import ChatMessage


def build_user_instructions_string(
    user_provided_instructions: Optional[str] = None,
) -> str:
    if not user_provided_instructions:
        return ""

    return f"""

# Custom Instructions Provided by the User

Please keep the user's instructions in mind when performing actions. If the user's instructions are not relevant to the current task, ignore them.

User Instructions:
{user_provided_instructions}"""


# extract
def build_extract_system_prompt(
    is_using_print_extracted_data_tool: bool = False,
    use_text_extract: bool = False,
    user_provided_instructions: Optional[str] = None,
) -> ChatMessage:
    base_content = """You are extracting content on behalf of a user.
If a user asks you to extract a 'list' of information, or 'all' information,
YOU MUST EXTRACT ALL OF THE INFORMATION THAT THE USER REQUESTS.

You will be given:
1. An instruction
2. """

    content_detail = (
        "A text representation of a webpage to extract information from."
        if use_text_extract
        else "A list of DOM elements to extract from."
    )

    instructions = (
        f"Print the exact text from the {'text-rendered webpage' if use_text_extract else 'DOM elements'} "
        f"with all symbols, characters, and endlines as is.\n"
        f"Print null or an empty string if no new information is found."
    ).strip()

    tool_instructions = (
        ("ONLY print the content using the print_extracted_data tool provided.").strip()
        if is_using_print_extracted_data_tool
        else ""
    )

    additional_instructions = (
        """Once you are given the text-rendered webpage,
you must thoroughly and meticulously analyze it. Be very careful to ensure that you
do not miss any important information."""
        if use_text_extract
        else (
            "If a user is attempting to extract links or URLs, you MUST respond with ONLY the IDs of the link elements.\n"
            "Do not attempt to extract links directly from the text unless absolutely necessary. "
        )
    )

    user_instructions = build_user_instructions_string(
        user_provided_instructions,
    )

    content_parts = [
        f"{base_content}{content_detail}",
        instructions,
        tool_instructions,
    ]
    if additional_instructions:
        content_parts.append(additional_instructions)
    if user_instructions:
        content_parts.append(user_instructions)

    # Join parts with newlines, filter empty strings, then replace multiple spaces
    full_content = "\n\n".join(filter(None, content_parts))
    content = " ".join(full_content.split())

    return ChatMessage(role="system", content=content)


def build_extract_user_prompt(
    instruction: str,
    dom_elements: str,
    is_using_print_extracted_data_tool: bool = False,
) -> ChatMessage:
    content = f"""Instruction: {instruction}
DOM: {dom_elements}"""

    if is_using_print_extracted_data_tool:
        content += (
            "\n\nONLY print the content using the print_extracted_data tool provided."
        )

    return ChatMessage(role="user", content=content)


refine_system_prompt = """You are tasked with refining and filtering information for the final output based on newly extracted and previously extracted content. Your responsibilities are:
1. Remove exact duplicates for elements in arrays and objects.
2. For text fields, append or update relevant text if the new content is an extension, replacement, or continuation.
3. For non-text fields (e.g., numbers, booleans), update with new values if they differ.
4. Add any completely new fields or objects ONLY IF they correspond to the provided schema.

Return the updated content that includes both the previous content and the new, non-duplicate, or extended information."""


def build_refine_system_prompt() -> ChatMessage:
    return ChatMessage(role="system", content=refine_system_prompt)


def build_refine_user_prompt(
    instruction: str,
    previously_extracted_content: dict[str, Any],
    newly_extracted_content: dict[str, Any],
) -> ChatMessage:
    return ChatMessage(
        role="user",
        content=f"""Instruction: {instruction}
Previously extracted content: {json.dumps(previously_extracted_content, indent=2)}
Newly extracted content: {json.dumps(newly_extracted_content, indent=2)}
Refined content:""",
    )


metadata_system_prompt = """You are an AI assistant tasked with evaluating the progress and completion status of an extraction task.
Analyze the extraction response and determine if the task is completed or if more information is needed.
Strictly abide by the following criteria:
1. Once the instruction has been satisfied by the current extraction response, ALWAYS set completion status to true and stop processing, regardless of remaining chunks.
2. Only set completion status to false if BOTH of these conditions are true:
   - The instruction has not been satisfied yet
   - There are still chunks left to process (chunksTotal > chunksSeen)"""


# TODO: remove these as no longer used
def build_metadata_system_prompt() -> ChatMessage:
    return ChatMessage(role="system", content=metadata_system_prompt)


def build_metadata_prompt(
    instruction: str,
    extraction_response: dict[str, Any],
    chunks_seen: int,
    chunks_total: int,
) -> ChatMessage:
    return ChatMessage(
        role="user",
        content=f"""Instruction: {instruction}
Extracted content: {json.dumps(extraction_response, indent=2)}
chunksSeen: {chunks_seen}
chunksTotal: {chunks_total}""",
    )


# observe
def build_observe_system_prompt(
    user_provided_instructions: Optional[str] = None,
) -> ChatMessage:
    tree_type_desc = "a hierarchical accessibility tree showing the semantic structure of the page. The tree is a hybrid of the DOM and the accessibility tree."

    observe_system_prompt_base = f"""
You are helping the user automate the browser by finding elements based on what the user wants to observe in the page.

You will be given:
1. an instruction of elements to observe
2. {tree_type_desc}

Return an array of elements that match the instruction if they exist, otherwise return an empty array. Whenever suggesting actions, use supported playwright locator methods or preferably one of the following supported actions:
{', '.join(method_handler_map.keys())}"""

    content = " ".join(observe_system_prompt_base.split())
    user_instructions_str = build_user_instructions_string(user_provided_instructions)

    final_content = content
    if user_instructions_str:
        final_content += "\n\n" + user_instructions_str

    return ChatMessage(
        role="system",
        content=final_content,
    )


def build_observe_user_message(
    instruction: str,
    tree_elements: str,
) -> ChatMessage:
    tree_or_dom = "Accessibility Tree"
    return ChatMessage(
        role="user",
        content=f"""instruction: {instruction}
{tree_or_dom}: {tree_elements}""",
    )


def build_act_observe_prompt(
    action: str,
    supported_actions: list[str],
    variables: Optional[dict[str, str]] = None,
) -> str:
    """
    Builds the instruction for the observeAct method to find the most relevant element for an action
    """
    instruction = f"""Find the most relevant element to perform an action on given the following action: {action}.
Provide an action for this element such as {', '.join(supported_actions)}, or any other playwright locator method. Remember that to users, buttons and links look the same in most cases.
If the action is completely unrelated to a potential action to be taken on the page, return an empty array.
ONLY return one action. If multiple actions are relevant, return the most relevant one.
If the user is asking to scroll to a position on the page, e.g., 'halfway' or 0.75, etc, you must return the argument formatted as the correct percentage, e.g., '50%' or '75%', etc.
If the user is asking to scroll to the next chunk/previous chunk, choose the nextChunk/prevChunk method. No arguments are required here.
If the action implies a key press, e.g., 'press enter', 'press a', 'press space', etc., always choose the press method with the appropriate key as argument — e.g. 'a', 'Enter', 'Space'. Do not choose a click action on an on-screen keyboard. Capitalize the first character like 'Enter', 'Tab', 'Escape' only for special keys."""

    if variables and len(variables) > 0:
        variables_prompt = f"The following variables are available to use in the action: {', '.join(variables.keys())}. Fill the argument variables with the variable name."
        instruction += f" {variables_prompt}"

    return instruction


def build_operator_system_prompt(goal: str) -> ChatMessage:
    return ChatMessage(
        role="system",
        content=f"""You are a general-purpose agent whose job is to accomplish the user's goal across multiple model calls by running actions on the page.

You will be given a goal and a list of steps that have been taken so far. Your job is to determine if either the user's goal has been completed or if there are still steps that need to be taken.

# Your current goal
{goal}

# Important guidelines
1. Break down complex actions into individual atomic steps
2. For `act` commands, use only one action at a time, such as:
   - Single click on a specific element
   - Type into a single input field
   - Select a single option
3. Avoid combining multiple actions in one instruction
4. If multiple actions are needed, they should be separate steps""",
    )
