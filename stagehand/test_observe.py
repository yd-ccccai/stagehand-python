"""Test script for the local observe implementation."""
import asyncio
import logging
import os

from stagehand import Stagehand
from stagehand.config import StagehandConfig
from stagehand.schemas import ObserveOptions


async def test_local_observe():
    """Test the local observe implementation."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("stagehand-test")
    
    # Make sure we have an API key for the model
    assert os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY environment variable must be set"
    
    # Create a Stagehand instance with LOCAL environment
    config = StagehandConfig(
        env="LOCAL",
        headless=False,  # Show the browser
        model_name="gpt-4o",  # Use GPT-4o
        model_client_options={"apiKey": os.getenv("OPENAI_API_KEY")},
        dom_settle_timeout_ms=5000,
    )
    
    stagehand = Stagehand(config=config, verbose=2)
    
    try:
        # Initialize Stagehand
        logger.info("Initializing Stagehand")
        await stagehand.init()
        
        # Navigate to a test page
        logger.info("Navigating to test page")
        await stagehand.page.goto("https://www.example.com")
        
        # Call observe
        logger.info("Calling observe")
        results = await stagehand.page.observe(
            ObserveOptions(
                instruction="Find all clickable elements on the page",
                draw_overlay=True,
            )
        )
        
        # Print the results
        logger.info(f"Found {len(results)} elements")
        for i, result in enumerate(results):
            logger.info(f"Element {i+1}: {result.description} - {result.selector}")
        
        # Wait a bit to see the overlay
        logger.info("Waiting 5 seconds to view the overlay")
        await asyncio.sleep(5)
        
    finally:
        # Clean up
        logger.info("Closing Stagehand")
        await stagehand.close()


if __name__ == "__main__":
    asyncio.run(test_local_observe()) 