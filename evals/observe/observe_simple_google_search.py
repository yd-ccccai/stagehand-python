import asyncio

from evals.init_stagehand import init_stagehand
from evals.utils import ensure_stagehand_config
from stagehand.schemas import ObserveOptions
from stagehand.utils import perform_playwright_method


async def observe_simple_google_search(model_name: str, logger) -> dict:
    """
    This function evaluates a simple Google search by:
    
    1. Initializing Stagehand with the provided model name and logger.
    2. Navigating to Google.com.
    3. Using observe to find the search bar and entering 'OpenAI'.
    4. Using observe to find and click the search button in the suggestions dropdown.
    5. Verifying if the URL matches the expected search URL.
    
    Returns a dictionary containing:
      - _success (bool): True if the search was successfully performed.
      - currentUrl (str): The URL after completing the search.
      - debugUrl (str): Debug URL from the Stagehand initialization.
      - sessionUrl (str): Session URL from the Stagehand initialization.
      - logs (list): Logs collected via the provided logger.
    """
    # Initialize Stagehand and extract URLs from the initialization response
    stagehand, init_response = await init_stagehand(model_name, logger)
    
    # Ensure stagehand has a config attribute
    ensure_stagehand_config(stagehand)
    
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

    # Navigate to Google
    await stagehand.page.goto("https://www.google.com")
    
    # Use observe to find the search bar and get an action to enter 'OpenAI'
    observation1 = await stagehand.page.observe(
        ObserveOptions(
            instruction="Find the search bar and enter 'OpenAI'",
            only_visible=False,
            return_action=True
        )
    )
    
    print(observation1)
    
    # Perform the search bar action if found
    if observation1:
        action1 = observation1[0]
        await perform_playwright_method(
            stagehand.page,
            logger,
            action1["method"],
            action1["arguments"],
            action1["selector"].replace("xpath=", "")
        )
    
    # Wait for suggestions to appear
    await stagehand.page.wait_for_timeout(5000)
    
    # Use observe to find and click the search button
    observation2 = await stagehand.page.observe(
        ObserveOptions(
            instruction="Click the search button in the suggestions dropdown",
            only_visible=False,
            return_action=True
        )
    )
    
    print(observation2)
    
    # Perform the search button click if found
    if observation2:
        action2 = observation2[0]
        await perform_playwright_method(
            stagehand.page,
            logger,
            action2["method"],
            action2["arguments"],
            action2["selector"].replace("xpath=", "")
        )
    
    # Wait for the search results to load
    await stagehand.page.wait_for_timeout(5000)
    
    # Get the current URL and check if it matches the expected URL
    current_url = stagehand.page.url()
    expected_url = "https://www.google.com/search?q=OpenAI"
    
    # Clean up and close the Stagehand client
    await stagehand.close()
    
    # Return the evaluation results
    return {
        "_success": current_url.startswith(expected_url),
        "currentUrl": current_url,
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
        result = await observe_simple_google_search("gpt-4o-mini", logger)
        print("Result:", result)
    
    asyncio.run(main()) 