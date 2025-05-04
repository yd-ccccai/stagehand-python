import asyncio

from evals.init_stagehand import init_stagehand
from evals.utils import ensure_stagehand_config
from stagehand.schemas import ObserveOptions


async def observe_amazon_add_to_cart(model_name: str, logger) -> dict:
    """
    This function evaluates observing Add to Cart elements on Amazon by:
    
    1. Initializing Stagehand with the provided model name and logger.
    2. Navigating to an Amazon product page.
    3. Using observe to find Add to Cart buttons.
    4. Checking if the observe API correctly identifies the Add to Cart buttons.
    
    Returns a dictionary containing:
      - _success (bool): True if the Add to Cart elements are correctly observed.
      - observations (list): The raw observations returned from the observe command.
      - debugUrl (str): Debug URL from the Stagehand initialization.
      - sessionUrl (str): Session URL from the Stagehand initialization.
      - logs (list): Logs collected via the provided logger.
    """
    try:
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

        # Navigate to an Amazon product page
        logger.info("Navigating to Amazon product page...")
        await stagehand.page.goto("https://www.amazon.com/Amazon-Basics-High-Speed-Cable-Latest/dp/B014I8SSD0/")
        
        # Use observe to find Add to Cart buttons
        logger.info("Running observe operation...")
        observations = await stagehand.page.observe(
            ObserveOptions(
                instruction="Find the Add to Cart button"
            )
        )
        
        # If no observations were returned, mark eval as unsuccessful
        if not observations:
            logger.error("No observations returned")
            await stagehand.close()
            return {
                "_success": False,
                "observations": observations,
                "debugUrl": debug_url,
                "sessionUrl": session_url,
                "logs": logger.get_logs() if hasattr(logger, "get_logs") else [],
            }
        
        # Look for "add to cart" or similar text in the observed elements
        found_add_to_cart = False
        cart_related_texts = ["add to cart", "add to basket", "buy now"]
        
        for observation in observations:
            # Try to get the inner text of the observed element
            try:
                element_text = await stagehand.page.locator(observation["selector"]).first.inner_text()
                element_text = element_text.strip().lower()
                
                # Check if any cart-related text is in the element text
                if any(cart_text in element_text for cart_text in cart_related_texts):
                    found_add_to_cart = True
                    logger.info(f"Found Add to Cart element with text: {element_text}")
                    break
            except Exception as e:
                logger.error(f"Failed to check text for element with selector {observation.get('selector')}: {str(e)}")
                continue
        
        # Clean up and close the Stagehand client
        await stagehand.close()
        
        # Return the evaluation results
        return {
            "_success": found_add_to_cart,
            "observations": observations,
            "debugUrl": debug_url,
            "sessionUrl": session_url,
            "logs": logger.get_logs() if hasattr(logger, "get_logs") else [],
        }
    except Exception as e:
        logger.error(f"Error in observe_amazon_add_to_cart: {str(e)}")
        return {
            "_success": False,
            "error": str(e),
            "debugUrl": None,
            "sessionUrl": None,
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