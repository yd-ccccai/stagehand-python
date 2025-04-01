import asyncio
import logging
import os
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
import json
from dotenv import load_dotenv

from stagehand import Stagehand, StagehandConfig
from stagehand.utils import configure_logging

# Configure logging to use cleaner format
configure_logging(
    level=logging.INFO,
    remove_logger_name=True,  # Don't show stagehand.client prefix
    quiet_dependencies=True   # Suppress httpx and other noisy logs
)

# Create a custom theme for console output
custom_theme = Theme(
    {
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red bold",
        "highlight": "magenta",
        "url": "blue underline",
    }
)

# Create a Rich console instance with our theme
console = Console(theme=custom_theme)

# Load environment variables
load_dotenv()

# Print logging info panel
console.print(
    Panel.fit(
        "[yellow]Logging Levels:[/]\n"
        "[white]- Set [bold]verbose=0[/] for errors only (ERROR)[/]\n"
        "[white]- Set [bold]verbose=1[/] for standard logs (INFO)[/]\n"
        "[white]- Set [bold]verbose=2[/] for detailed logs (WARNING)[/]\n"
        "[white]- Set [bold]verbose=3[/] for debug logs (DEBUG)[/]",
        title="Verbosity Options",
        border_style="blue",
    )
)

def format_extraction(data):
    """Format extraction data for cleaner display"""
    if not data:
        return "No data extracted"
    
    # Try to get the model_dump_json if it's a Pydantic model
    if hasattr(data, "model_dump_json"):
        try:
            data_dict = json.loads(data.model_dump_json())
        except:
            data_dict = data
    else:
        data_dict = data
    
    # Check for extraction field
    if isinstance(data_dict, dict) and "extraction" in data_dict:
        extraction = data_dict["extraction"]
        
        # Handle dict extractions
        if isinstance(extraction, dict):
            return json.dumps(extraction, indent=2)
        # Handle string extractions (make them stand out)
        elif isinstance(extraction, str):
            if "\n" in extraction:
                return f"Extracted text:\n{extraction}"
            else:
                return f"Extracted: {extraction}"
    
    # Fall back to pretty-printed JSON
    return json.dumps(data_dict, indent=2)

async def main():
    # Build a unified configuration object for Stagehand
    config = StagehandConfig(
        env="BROWSERBASE",
        api_key=os.getenv("BROWSERBASE_API_KEY"),
        project_id=os.getenv("BROWSERBASE_PROJECT_ID"),
        headless=False,
        dom_settle_timeout_ms=3000,
        model_name="gpt-4o",
        self_heal=True,
        wait_for_captcha_solves=True,
        system_prompt="You are a browser automation assistant that helps users navigate websites effectively.",
        model_client_options={"apiKey": os.getenv("MODEL_API_KEY")},
        # Use verbose=1 for basic logs, 2 for more detailed, 3 for debug
        verbose=1,
    )

    # Create a Stagehand client using the configuration object.
    # Change verbose level to control log verbosity:
    # 0 = only errors, 1 = basic logs, 2 = medium logs, 3 = detailed logs
    stagehand = Stagehand(
        config=config, server_url=os.getenv("STAGEHAND_SERVER_URL")
    )

    # Initialize - this creates a new session automatically.
    console.print("\n🚀 [info]Initializing Stagehand...[/]")
    await stagehand.init()
    page = stagehand.page
    console.print(f"\n[yellow]Created new session:[/] {stagehand.session_id}")
    console.print(
        f"🌐 [white]View your live browser:[/] [url]https://www.browserbase.com/sessions/{stagehand.session_id}[/]"
    )

    await asyncio.sleep(2)

    console.print("\n▶️ [highlight] Navigating[/] to Google")
    await page.goto("https://google.com/")
    console.print("✅ [success]Navigated to Google[/]")

    console.print("\n▶️ [highlight] Clicking[/] on About link")
    # Click on the "About" link using Playwright
    await page.get_by_role("link", name="About", exact=True).click()
    console.print("✅ [success]Clicked on About link[/]")

    await asyncio.sleep(2)
    console.print("\n▶️ [highlight] Navigating[/] back to Google")
    await page.goto("https://google.com/")
    console.print("✅ [success]Navigated back to Google[/]")

    console.print("\n▶️ [highlight] Performing action:[/] search for openai")
    await page.act("search for openai")
    await page.keyboard.press("Enter")
    console.print("✅ [success]Performing Action:[/] Action completed successfully")

    console.print("\n▶️ [highlight] Observing page[/] for news button")
    observed = await page.observe("find the news button on the page")
    if len(observed) > 0:
        element = observed[0]
        console.print("✅ [success]Found element:[/] News button")
        console.print("\n▶️ [highlight] Performing action on observed element")
        await page.act(element)
        console.print("✅ [success]Performing Action:[/] Action completed successfully")

    else:
        console.print("❌ [error]No element found[/]")

    console.print("\n▶️ [highlight] Extracting[/] first search result")
    data = await page.extract("extract the first result from the search")
    console.print("📊 [info]Extracted data:[/]")
    console.print(format_extraction(data))

    # Close the session
    console.print("\n⏹️ [warning]Closing session...[/]")
    await stagehand.close()
    console.print("✅ [success]Session closed successfully![/]")
    console.rule("[bold]End of Example[/]")


if __name__ == "__main__":
    # Add a fancy header
    console.print(
        "\n",
        Panel.fit(
            "[light_gray]Stagehand 🤘 Python Example[/]",
            border_style="green",
            padding=(1, 10),
        ),
    )
    asyncio.run(main())
