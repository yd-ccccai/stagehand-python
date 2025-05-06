import asyncio
import logging
import os
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
import json
from pydantic import BaseModel
from dotenv import load_dotenv
from pprint import pprint
import base64

import time
from stagehand import StagehandConfig
from stagehand.sync import Stagehand
# from stagehand.sync import Stagehand
from stagehand.utils import configure_logging
from stagehand.schemas import ObserveOptions, ActOptions, ExtractOptions
from stagehand.sync.a11y.utils import get_accessibility_tree, get_xpath_by_resolved_object_id

# # Configure logging with cleaner format
# configure_logging(
#     level=logging.INFO,
#     remove_logger_name=True,  # Remove the redundant stagehand.client prefix
#     quiet_dependencies=True,   # Suppress httpx and other noisy logs
# )

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

console.print(
    Panel.fit(
        "[yellow]Logging Levels:[/]\n"
        "[white]- Set [bold]verbose=0[/] for errors (ERROR)[/]\n"
        "[white]- Set [bold]verbose=1[/] for minimal logs (INFO)[/]\n"
        "[white]- Set [bold]verbose=2[/] for medium logs (WARNING)[/]\n"
        "[white]- Set [bold]verbose=3[/] for detailed logs (DEBUG)[/]",
        title="Verbosity Options",
        border_style="blue",
    )
)
    
class Joke(BaseModel):
    joke: str
    explanation: str
    setup: str
    punchline: str

class Jokes(BaseModel):
    jokes: list[Joke]

class Action(BaseModel):
    action: str
    id: int
    arguments: list[str]

# def main():
#     # Build a unified configuration object for Stagehand
#     config = StagehandConfig(
#         env="LOCAL",
#         api_key=os.getenv("BROWSERBASE_API_KEY"),
#         project_id=os.getenv("BROWSERBASE_PROJECT_ID"),
#         model_name="gemini/gemini-2.5-flash-preview-04-17",
#         model_client_options={"apiKey": os.getenv("MODEL_API_KEY")},
#         # Use verbose=2 for medium-detail logs (1=minimal, 3=debug)
#         verbose=2,
#     )

#     stagehand = SyncStagehand(
#         config=config, 
#         env="LOCAL",
#         server_url=os.getenv("STAGEHAND_API_URL"),
#     )
#     stagehand.init()
#     stagehand.page.page.goto("https://www.google.com")
#     time.sleep(100)
#     stagehand.close()
def main():
    # Build a unified configuration object for Stagehand
    config = StagehandConfig(
        env="LOCAL",
        api_key=os.getenv("BROWSERBASE_API_KEY"),
        project_id=os.getenv("BROWSERBASE_PROJECT_ID"),
        model_name="gemini/gemini-2.5-flash-preview-04-17",
        model_client_options={"apiKey": os.getenv("MODEL_API_KEY")},
        # Use verbose=2 for medium-detail logs (1=minimal, 3=debug)
        verbose=3,
    )

    stagehand = Stagehand(
        config=config, 
        env="LOCAL",
        server_url=os.getenv("STAGEHAND_SERVER_URL"),
    )
    stagehand.init()
    page = stagehand.page
    # await stagehand.page.page.goto("https://www.elon.edu/u/imagining/about/kidzone/jokes-laughs/")
    page.goto("https://www.aigrant.com")
    # await stagehand.page.page.goto("https://iframetester.com/?url=https://browserbase.com")
    time.sleep(2)
    # await stagehand.page.page.mouse.wheel(0, 500)
    tree = get_accessibility_tree(stagehand.page, stagehand.logger)
    with open("../tree_sync.txt", "w") as f:
        f.write(tree.get("simplified"))

    print(tree.get("idToUrl"))
    print(tree.get("iframes"))
    page.act("click the button with text 'Get Started'")
    page.observe("the button with text 'Get Started'")
    page.extract("the text 'Get Started'")
    page.locator("xpath=/html/body/div/ul[2]/li[2]/a").click()
    page.wait_for_load_state('networkidle')
    new_page = stagehand.context.new_page()
    new_page.goto("https://www.google.com")
    tree = get_accessibility_tree(new_page, stagehand.logger)
    with open("../tree_sync.txt", "w") as f:
        f.write(tree.get("simplified"))
    new_page.act("click the button with text 'Get Started'")
    # screenshot = await stagehand.page.page.screenshot()
    response = stagehand.llm.create_response(
        messages=[
            {
                "role": "system",
                "content": "Based on the provided accessibility tree of the page, find the element and the action the user is expecting to perform. The tree consists of an enhanced a11y tree from a website with unique identifiers prepended to each element's role, and name. The actions you can take are playwright compatible locator actions."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"fill the search bar with the text 'Hello'\nPage Tree:\n{tree.get('simplified')}"
                    },
    #                 {
    #                     "type": "image_url",
    #                     "image_url": {
    # #                     "url": f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
    # #                 }
    #             }
                ]
            }
        ],
        model="gemini/gemini-2.5-flash-preview-04-17",
        # model="openai/gpt-4o-mini",
        response_format=Action,
    )
    print(response.choices[0].message.content)
    action = Action.model_validate_json(response.choices[0].message.content)
    args = { "backendNodeId": action.id }
    # Correctly call send_cdp in Python and extract the 'object' key
    result = new_page.send_cdp("DOM.resolveNode", args)
    object_info = result.get("object") # Use .get for safer access
    print(object_info)
    xpath = get_xpath_by_resolved_object_id(new_page.get_cdp_client(), object_info["objectId"])
    print(xpath)
    if xpath:
        new_page.locator(f"xpath={xpath}").click()
        new_page.locator(f"xpath={xpath}").fill(action.arguments[0])
    else:
        print("No xpath found")

    new_page.keyboard.press("Enter")
    time.sleep(3)

    new_page.observe("find the first result")
    new_page.observe("find the second result")
    page.observe("find the page header")
    time.sleep(100)
    # print("Received={}".format(response.choices[0].message.content))
    # pprint(json.loads(response.choices[0].message.content))
    # print(response.choices[0].message.parsed)
    # response = stagehand.llm.create_response(
    #     messages=[{"role": "user", "content": "Hello, how are you? can you tell me a few jokes?"}],
    #     model="gemini/gemini-2.0-flash",
    #     response_format=Jokes,
    # )
    # response_content = response.choices[0].message.content
    # response_cost = response._hidden_params["response_cost"]
    # print(f"Received={response_content}")
    # print(f"Cost={response_cost}")
    # print(Jokes.model_validate(json.loads(response.choices[0].message.content)))


    stagehand.close()


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
    main()