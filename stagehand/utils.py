import logging
from typing import Any

# Setup logging
logger = logging.getLogger(__name__)
# Only add handler if there isn't one already to avoid duplicate logs
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)
    # Don't propagate to root logger to avoid duplicate logs
    logger.propagate = False


def configure_logging(
    level=logging.INFO, 
    format_str="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    quiet_dependencies=True,
    utils_level=None
):
    """
    Configure logging for Stagehand with sensible defaults.
    
    Args:
        level: The logging level for Stagehand loggers (default: INFO)
        format_str: The format string for log messages
        datefmt: The date format string for log timestamps
        quiet_dependencies: If True, sets httpx, httpcore, and other noisy dependencies to WARNING level
        utils_level: Optional specific level for stagehand.utils logger (default: None, uses the main level)
        
    Example:
        ```python
        from stagehand.utils import configure_logging
        import logging
        
        # Set up logging with custom level
        configure_logging(level=logging.DEBUG)
        
        # Set stagehand logs to DEBUG but utils to WARNING
        configure_logging(level=logging.DEBUG, utils_level=logging.WARNING)
        ```
    """
    # Configure root logger
    logging.basicConfig(
        level=level,
        format=format_str,
        datefmt=datefmt,
    )
    
    # Configure Stagehand logger to use the specified level
    logging.getLogger("stagehand").setLevel(level)
    
    # Set specific level for utils logger if specified
    if utils_level is not None:
        logging.getLogger("stagehand.utils").setLevel(utils_level)
    
    # Set higher log levels for noisy dependencies
    if quiet_dependencies:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)


async def default_log_handler(log_data: dict[str, Any]) -> None:
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
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def convert_dict_keys_to_camel_case(data: dict[str, Any]) -> dict[str, Any]:
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
            value = [
                (
                    convert_dict_keys_to_camel_case(item)
                    if isinstance(item, dict)
                    else item
                )
                for item in value
            ]

        # Convert snake_case key to camelCase
        camel_key = snake_to_camel(key)
        result[camel_key] = value

    return result
