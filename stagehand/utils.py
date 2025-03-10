import asyncio
import logging
from typing import Any, Dict

# Setup logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

async def default_log_handler(log_data: Dict[str, Any]) -> None:
    """Default handler for log messages from the Stagehand server."""
    level = log_data.get("level", "info").lower()
    message = log_data.get("message", "")

    log_method = getattr(logger, level, logger.info)
    log_method(message)


def snake_to_camel(snake_str: str) -> str:
    """
    Convert a snake_case string to camelCase.
    
    Args:
        snake_str: The snake_case string to convert
        
    Returns:
        The converted camelCase string
    """
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def convert_dict_keys_to_camel_case(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert all keys in a dictionary from snake_case to camelCase.
    Works recursively for nested dictionaries.
    
    Args:
        data: Dictionary with snake_case keys
        
    Returns:
        Dictionary with camelCase keys
    """
    result = {}
    
    for key, value in data.items():
        if isinstance(value, dict):
            value = convert_dict_keys_to_camel_case(value)
        elif isinstance(value, list):
            value = [convert_dict_keys_to_camel_case(item) if isinstance(item, dict) else item for item in value]
            
        # Convert snake_case key to camelCase
        camel_key = snake_to_camel(key)
        result[camel_key] = value
        
    return result
