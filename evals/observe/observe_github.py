import asyncio

from evals.init_stagehand import init_stagehand
from stagehand.schemas import ObserveOptions


async def observe_github(model_name: str, logger) -> dict:
    """
    This function evaluates finding the file tree in GitHub by:
    
    1. Initializing Stagehand with the provided model name and logger.
    2. Navigating to the NumPy GitHub repository.
    3. Using observe to find the scrollable element that holds the repository file tree.
    4. Checking if the observed element matches any of the expected locators.
    
    Returns a dictionary containing:
      - _success (bool): True if a matching file tree element is found.
      - matchedLocator (Optional[str]): The candidate locator string that matched.
      - observations (list): The raw observations returned from the observe command.
      - debugUrl (str): Debug URL from the Stagehand initialization.
      - sessionUrl (str): Session URL from the Stagehand initialization.
      - logs (list): Logs collected via the provided logger.
    """
    # Initialize Stagehand and extract URLs from the initialization response
    stagehand, init_response = await init_stagehand(model_name, logger)
    debug_url = (
        init_response.get("debugUrl", {}).get("value")
        if isinstance(init_response.get("debugUrl"), dict)
        else init_response.get("debugUrl")
    )
    session_url = (
        init_response.get("sessionUrl", {}).get("value")
        if isinstance(init_response.get("sessionUrl"), dict)
        else init_response.get("sessionUrl")
    )

    # Navigate to the NumPy GitHub repository
    await stagehand.page.goto("https://github.com/numpy/numpy/tree/main/numpy")
    
    # Use observe to find the file tree element
    observations = await stagehand.page.observe(
        ObserveOptions(
            instruction="find the scrollable element that holds the repos file tree."
        )
    )
    
    # If no observations were returned, mark eval as unsuccessful and return early
    if not observations:
        await stagehand.close()
        return {
            "_success": False,
            "observations": observations,
            "debugUrl": debug_url,
            "sessionUrl": session_url,
            "logs": logger.get_logs() if hasattr(logger, "get_logs") else [],
        }
    
    # Define candidate locators for the file tree element
    possible_locators = [
        "#repos-file-tree > div.Box-sc-g0xbh4-0.jbQqON > div > div > div > nav > ul",
        "#repos-file-tree > div.Box-sc-g0xbh4-0.jbQqON > div > div > div > nav",
        "#repos-file-tree > div.Box-sc-g0xbh4-0.jbQqON",
    ]
    
    # Get handles for possible locators
    possible_handles = []
    for locator_str in possible_locators:
        locator = stagehand.page.locator(locator_str)
        handle = await locator.element_handle()
        if handle:
            possible_handles.append((locator_str, handle))
    
    # Check if any observation matches a candidate locator
    found_match = False
    matched_locator = None
    
    for observation in observations:
        try:
            # Get the first element matching the observation's selector
            observation_locator = stagehand.page.locator(observation["selector"]).first
            observation_handle = await observation_locator.element_handle()
            if not observation_handle:
                continue
            
            # Compare this observation's element with candidate handles
            for locator_str, candidate_handle in possible_handles:
                is_same_node = await observation_handle.evaluate(
                    "(node, otherNode) => node === otherNode", candidate_handle
                )
                if is_same_node:
                    found_match = True
                    matched_locator = locator_str
                    break
            
            if found_match:
                break
        except Exception as e:
            print(
                f"Warning: Failed to check observation with selector {observation.get('selector')}: {str(e)}"
            )
            continue
    
    # Clean up and close the Stagehand client
    await stagehand.close()
    
    # Return the evaluation results
    return {
        "_success": found_match,
        "matchedLocator": matched_locator,
        "observations": observations,
        "debugUrl": debug_url,
        "sessionUrl": session_url,
        "logs": logger.get_logs() if hasattr(logger, "get_logs") else [],
    }


# For quick local testing
if __name__ == "__main__":
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    class SimpleLogger:
        def __init__(self):
            self._logs = []
            
        def info(self, message):
            self._logs.append(message)
            print("INFO:", message)
            
        def error(self, message):
            self._logs.append(message)
            print("ERROR:", message)
            
        def get_logs(self):
            return self._logs
    
    async def main():
        logger = SimpleLogger()
        result = await observe_github("gpt-4o-mini", logger)
        print("Result:", result)
    
    asyncio.run(main()) 