from stagehand.llm.prompts import build_act_observe_prompt
from stagehand.types import ActOptions, ActResult, ObserveOptions, ObserveResult


class ActHandler:
    """Handler for processing observe operations locally."""

    def __init__(
        self, stagehand_page, stagehand_client, user_provided_instructions=None
    ):
        """
        Initialize the ActHandler.

        Args:
            stagehand_page: StagehandPage instance
            stagehand_client: Stagehand client instance
            user_provided_instructions: Optional custom system instructions
        """
        self.stagehand_page = stagehand_page
        self.stagehand = stagehand_client
        self.logger = stagehand_client.logger
        self.user_provided_instructions = user_provided_instructions

    async def act(self, options: ActOptions) -> ActResult:
        """
        Perform an act based on an instruction.
        This method will observe the page and then perform the act on the first element returned.
        """
        action_task = options.get("action")
        self.logger.info(
            f"Starting action for task: '{action_task}'",
            category="act",
        )
        prompt = build_act_observe_prompt(
            action=action_task,
            supported_actions=["click", "fill", "type", "press"],
            variables=options.get("variables"),
        )
        # Wrap around observe options object
        observe_options = ObserveOptions(instruction=prompt)
        observe_result = await self.stagehand_page._observe_handler.observe(
            observe_options, from_act=True
        )
        if len(observe_result) == 0:
            return ActResult(
                success=False, message="No observe results found", action=action_task
            )
        else:
            return self._act_from_observe_result(observe_result[0])

    def _act_from_observe_result(self, observe_result: ObserveResult) -> ActResult:
        self.logger.info(
            "observe result",
            category="act",
            auxiliary={"observe_result": observe_result},
        )
        pass
