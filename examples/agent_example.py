import asyncio
import logging
import os

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme

from stagehand.client import Stagehand
from stagehand.config import StagehandConfig
from stagehand.schemas import AgentConfig, AgentExecuteOptions, AgentProvider

# Create a custom theme for consistent styling
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

load_dotenv()

# Configure logging with Rich handler
logging.basicConfig(
    level=logging.WARNING,  # Feel free to change this to INFO or DEBUG to see more logs
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


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
        act_timeout_ms=60000,  # 60 seconds timeout for actions
        system_prompt="You are a browser automation assistant that helps users navigate websites effectively.",
        model_client_options={"apiKey": os.getenv("MODEL_API_KEY")},
    )

    # Create a Stagehand client using the configuration object.
    stagehand = Stagehand(
        config=config, server_url=os.getenv("STAGEHAND_SERVER_URL"), verbose=2
    )

    # Initialize - this creates a new session automatically.
    console.print("\n🚀 [info]Initializing Stagehand...[/]")
    await stagehand.init()
    console.print(f"\n[yellow]Created new session:[/] {stagehand.session_id}")
    console.print(
        f"🌐 [white]View your live browser:[/] [url]https://www.browserbase.com/sessions/{stagehand.session_id}[/]"
    )

    # Demonstrate the agent functionality
    console.print("\n▶️ [highlight] Using Agent to perform a task[/]")
    
    # Configure the agent
    agent_config = AgentConfig(
        provider=AgentProvider.OPENAI,
        model="gpt-4o",
        instructions="You are a helpful web navigation assistant that helps users find information.",
    )
    
    # Define the task for the agent
    execute_options = AgentExecuteOptions(
        instruction="Navigate to wikipedia.org and search for 'artificial intelligence', then extract the first paragraph of the article.",
        max_steps=10,
        auto_screenshot=True,
    )
    
    # Execute the agent task using the new agent interface
    agent_result = await stagehand.agent.execute(agent_config, execute_options)
    
    console.print("📊 [info]Agent execution result:[/]")
    console.print_json(f"{agent_result.model_dump_json()}")

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
            "[light_gray]Stagehand 🤘 Async Agent Example[/]",
            border_style="green",
            padding=(1, 10),
        ),
    )
    asyncio.run(main()) 