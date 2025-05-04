"""Functions for building prompts for different Stagehand operations."""
from typing import Optional


def build_observe_system_prompt(
    user_provided_instructions: Optional[str] = None,
    is_using_accessibility_tree: bool = False,
) -> str:
    """
    Build the system prompt for the observe inference.
    
    Args:
        user_provided_instructions: Optional custom system instructions
        is_using_accessibility_tree: Whether using accessibility tree
        
    Returns:
        The system prompt string
    """
    if user_provided_instructions:
        return user_provided_instructions
        
    if is_using_accessibility_tree:
        return """You are an AI assistant tasked with finding elements on a webpage that match specific requirements or instructions. 
Your goal is to identify the most relevant elements based on the user's instruction.

The user will provide:
1. A description of what they're looking for (e.g., "find the search box", "find the login button").
2. A simplified representation of the page's accessibility tree, which describes the accessible elements on the page.

You should respond with a list of elements that match the user's request, including each element's ID and a description.

For EACH element you identify, provide:
1. The element ID (number)
2. A brief description of what the element is and why it's relevant to the user's request
3. If requested, a suggested method for interacting with the element (e.g., "click", "fill", "hover"), and any required arguments

Only include elements that are relevant to the user's request. If you can't find any matching elements, return an empty list.

Be precise and specific in your descriptions, and make sure to include all relevant elements."""
    else:
        return """You are an AI assistant tasked with finding elements on a webpage that match specific requirements or instructions. 
Your goal is to identify the most relevant elements based on the user's instruction.

The user will provide:
1. A description of what they're looking for (e.g., "find the search box", "find the login button").
2. A simplified HTML representation of the webpage.

You should respond with a list of elements that match the user's request, including each element's ID and a description.

For EACH element you identify, provide:
1. The element ID (number)
2. A brief description of what the element is and why it's relevant to the user's request
3. If requested, a suggested method for interacting with the element (e.g., "click", "fill", "hover"), and any required arguments

Only include elements that are relevant to the user's request. If you can't find any matching elements, return an empty list.

Be precise and specific in your descriptions, and make sure to include all relevant elements."""


def build_observe_user_prompt(
    instruction: str,
    dom_elements: str,
    is_using_accessibility_tree: bool = False,
) -> str:
    """
    Build the user prompt for the observe inference.
    
    Args:
        instruction: The instruction to follow when finding elements
        dom_elements: String representation of DOM elements
        is_using_accessibility_tree: Whether using accessibility tree
        
    Returns:
        The user prompt string
    """
    if is_using_accessibility_tree:
        return f"""Instruction: {instruction}

Here is the simplified accessibility tree of the page:

{dom_elements}

Please identify all elements that match the instruction. For each element, provide the element ID, a description, 
and if needed, a suggested method and arguments for interaction."""
    else:
        return f"""Instruction: {instruction}

Here is the simplified HTML representation of the page:

{dom_elements}

Please identify all elements that match the instruction. For each element, provide the element ID, a description, 
and if needed, a suggested method and arguments for interaction.""" 