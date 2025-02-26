import asyncio
import os
import logging
from dotenv import load_dotenv
from stagehand.client import Stagehand
from stagehand.config import StagehandConfig
from pydantic import BaseModel
from stagehand.schemas import ExtractOptions

load_dotenv()

# Configure logging at the start of the script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class ExtractSchema(BaseModel):
    stars: int

async def main():
    try:
        # Build a unified configuration object for Stagehand
        config = StagehandConfig(
            env="BROWSERBASE",
            api_key=os.getenv("BROWSERBASE_API_KEY"),
            project_id=os.getenv("BROWSERBASE_PROJECT_ID"),
            headless=False,
            dom_settle_timeout_ms=3000,
            model_name="gpt-4o-mini",
            model_client_options={"apiKey": os.getenv("MODEL_API_KEY")}
        )

        # Create a Stagehand client using the configuration object.
        stagehand = Stagehand(config=config, server_url=os.getenv("STAGEHAND_SERVER_URL"), verbose=2)

        # Initialize - this creates a new session automatically.
        await stagehand.init()
        page = stagehand.page
        print(f"Created new session with ID: {stagehand.session_id}")

        print('EXAMPLE: You can navigate to any website using the local or remote Playwright.')

        await page.goto("https://news.ycombinator.com/")
        print("Navigation complete with local Playwright.")

        await page.navigate("https://www.google.com")
        print("Navigation complete with remote Playwright.")

        print("EXAMPLE: Clicking on About link using local Playwright's get_by_role")
        # Click on the "About" link using Playwright
        await page.get_by_role("link", name="About", exact=True).click()
        print("Clicked on About link")

        await asyncio.sleep(2)
        await page.navigate("https://www.google.com")
        
        # Hosted Stagehand API - ACT to do something like 'search for openai'
        print(f"EXAMPLE: Performing action")
        await page.act("search for openai")
        
        # print("EXAMPLE: Find the XPATH of the button 'News' using Stagehand API")
        observed = await page.observe("find the news button on the page")
        if len(observed) > 0:
            element = observed[0]
            # print("EXAMPLE: Click on the button 'News' using local Playwright.")
            await page.act(element)
        else:
            print("No element found")

    except Exception as e:
        print(f"An error occurred in the example: {e}")
    finally:
        await stagehand.close()

    new_stagehand = Stagehand(config=config, server_url=os.getenv("STAGEHAND_SERVER_URL"), verbose=2)
    # page = new_stagehand.page
    await new_stagehand.init()
    page = new_stagehand.page
    print(f"Created new session with ID: {new_stagehand.session_id}")

    try:
        await page.navigate("https://github.com/facebook/react")
        print("Navigation complete.")

        # Use the ExtractOptions Pydantic model to pass instruction and schema definition
        data = await page.extract("Extract the number of stars for the project")
        data = await page.extract(
            ExtractOptions(
                instruction="Extract the number of stars for the project",
                schemaDefinition=ExtractSchema.model_json_schema()
            )
        )
        print("\nExtracted stars:", data)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await new_stagehand.close()

if __name__ == "__main__":
    asyncio.run(main())