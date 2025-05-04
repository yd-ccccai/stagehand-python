import asyncio

from evals.init_stagehand import init_stagehand
from stagehand.schemas import ObserveOptions, ActionOptions


async def observe_amazon_add_to_cart(model_name: str, logger) -> dict:
    """
    This function evaluates adding a product to cart on Amazon by:
    
    1. Initializing Stagehand with the provided model name and logger.
    2. Navigating to a mock Amazon product page.
    3. Using observe to find and click the "Add to Cart" button.
    4. Using observe to find and click the "Proceed to checkout" button.
    5. Verifying if the navigation reached the sign-in page.
    
    Returns a dictionary containing:
      - _success (bool): True if the checkout flow successfully reaches the sign-in page.
      - currentUrl (str): The URL after completing the navigation steps.
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

    # Navigate to the mock Amazon product page
    await stagehand.page.goto(
        "https://browserbase.github.io/stagehand-eval-sites/sites/amazon/"
    )
    
    # Wait for the page to load
    await stagehand.page.wait_for_timeout(5000)
    
    # Use observe to find the "Add to Cart" button
    observations1 = await stagehand.page.observe(
        ObserveOptions(
            instruction="Find and click the 'Add to Cart' button",
            only_visible=False,
            return_action=True
        )
    )
    
    print(observations1)
    
    # Perform the click action if a button was found
    if observations1:
        action1 = observations1[0]
        await stagehand.page.act(action1)
    
    # Wait for the action to complete
    await stagehand.page.wait_for_timeout(2000)
    
    # Use observe to find the "Proceed to checkout" button
    observations2 = await stagehand.page.observe(
        ObserveOptions(
            instruction="Find and click the 'Proceed to checkout' button"
        )
    )
    
    # Perform the click action if a button was found
    if observations2:
        action2 = observations2[0]
        await stagehand.page.act(action2)
    
    # Wait for the action to complete
    await stagehand.page.wait_for_timeout(2000)
    
    # Get the current URL and check if it matches the expected URL
    current_url = stagehand.page.url()
    expected_url_prefix = "https://browserbase.github.io/stagehand-eval-sites/sites/amazon/sign-in.html"
    
    # Clean up and close the Stagehand client
    await stagehand.close()
    
    # Return the evaluation results
    return {
        "_success": current_url.startswith(expected_url_prefix),
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
        result = await observe_amazon_add_to_cart("gpt-4o-mini", logger)
        print("Result:", result)
    
    asyncio.run(main()) 