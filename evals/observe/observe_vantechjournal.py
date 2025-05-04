import asyncio

from evals.init_stagehand import init_stagehand
from stagehand.schemas import ObserveOptions


async def observe_vantechjournal(model_name: str, logger) -> dict:
    """
    This function evaluates finding a pagination button on the VanTech Journal by:
    
    1. Initializing Stagehand with the provided model name and logger.
    2. Navigating to the VanTech Journal archive page.
    3. Using observe to find the button that navigates to the 11th page.
    4. Checking if the observed element matches the expected target element.
    
    Returns a dictionary containing:
      - _success (bool): True if a matching pagination button is found.
      - expected: The expected element (this will be a Playwright locator).
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

    # Navigate to the VanTech Journal archive page
    await stagehand.page.goto("https://vantechjournal.com/archive?page=8")
    
    # Wait for the page to load
    await stagehand.page.wait_for_timeout(1000)
    
    # Use observe to find the pagination button for page 11
    observations = await stagehand.page.observe(
        ObserveOptions(
            instruction="find the button that takes us to the 11th page"
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
    
    # Define the expected locator for the pagination button
    expected_locator = "a.rounded-lg:nth-child(8)"
    
    # Get the expected element
    expected_result = stagehand.page.locator(expected_locator)
    
    # Check if any observation matches the expected element
    found_match = False
    
    for observation in observations:
        try:
            # Get the first element matching the observation's selector
            observation_locator = stagehand.page.locator(observation["selector"]).first
            observation_handle = await observation_locator.element_handle()
            expected_handle = await expected_result.element_handle()
            
            if not observation_handle or not expected_handle:
                # Couldn't get handles, skip
                continue
            
            # Compare this observation's element with the expected element
            is_same_node = await observation_handle.evaluate(
                "(node, otherNode) => node === otherNode",
                expected_handle
            )
            
            if is_same_node:
                found_match = True
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
        "expected": expected_result,
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
        result = await observe_vantechjournal("gpt-4o-mini", logger)
        print("Result:", result)
    
    asyncio.run(main()) 