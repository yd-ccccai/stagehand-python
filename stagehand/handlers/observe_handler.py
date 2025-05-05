"""Observe handler for performing observations of page elements using LLMs."""

from typing import Any

from stagehand.a11y.utils import get_accessibility_tree, get_xpath_by_resolved_object_id
from stagehand.schemas import ObserveOptions, ObserveResult
from stagehand.utils import draw_observe_overlay


class ObserveHandler:
    """Handler for processing observe operations locally."""

    def __init__(
        self, stagehand_page, stagehand_client, user_provided_instructions=None
    ):
        """
        Initialize the ObserveHandler.

        Args:
            stagehand_page: StagehandPage instance
            stagehand_client: Stagehand client instance
            user_provided_instructions: Optional custom system instructions
        """
        self.stagehand_page = stagehand_page
        self.stagehand = stagehand_client
        self.logger = stagehand_client.logger
        self.user_provided_instructions = user_provided_instructions

    async def observe(
        self,
        options: ObserveOptions,
        request_id: str,
    ) -> list[ObserveResult]:
        """
        Execute an observation operation locally.

        Args:
            options: ObserveOptions containing the instruction and other parameters
            request_id: Unique identifier for the request

        Returns:
            list of ObserveResult instances
        """
        instruction = options.instruction
        if not instruction:
            instruction = (
                "Find elements that can be used for any future actions in the page. "
                "These may be navigation links, related pages, section/subsection links, "
                "buttons, or other interactive elements. Be comprehensive: if there are "
                "multiple elements that may be relevant for future actions, return all of them."
            )

        self.logger.info("Starting observation", auxiliary={"instruction": instruction})

        # Determine if we should use accessibility tree or standard DOM processing
        use_accessibility_tree = not options.only_visible

        # Get DOM representation
        selector_map = {}
        output_string = ""
        iframes = []

        if use_accessibility_tree:
            await self.stagehand_page._wait_for_settled_dom()
            # Get accessibility tree data using our utility function
            tree = await get_accessibility_tree(self.stagehand_page, self.logger)
            self.logger.info("Getting accessibility tree data")
            output_string = tree["simplified"]
            iframes = tree.get("iframes", [])
        else:
            # Process standard DOM representation
            eval_result = await self.stagehand_page._page.evaluate(
                """() => {
                    return window.processAllOfDom().then(result => result);
                }"""
            )
            output_string = eval_result.get("outputString", "")
            selector_map = eval_result.get("selectorMap", {})

        # Call LLM to process the DOM and find elements
        from stagehand.llm.inference import observe as observe_inference

        observation_response = await observe_inference(
            instruction=instruction,
            tree_elements=output_string,
            llm_client=self.stagehand.llm_client,
            request_id=request_id,
            user_provided_instructions=self.user_provided_instructions,
            logger=self.logger,
            return_action=options.return_action,
            log_inference_to_file=False,  # TODO: Implement logging to file if needed
            from_act=False,
        )

        # TODO: Update metrics for token usage
        # prompt_tokens = observation_response.get("prompt_tokens", 0)
        # completion_tokens = observation_response.get("completion_tokens", 0)
        # inference_time_ms = observation_response.get("inference_time_ms", 0)

        # Add iframes to the response if any
        elements = observation_response.get("elements", [])
        for iframe in iframes:
            elements.append(
                {
                    "elementId": int(iframe.get("nodeId", 0)),
                    "description": "an iframe",
                    "method": "not-supported",
                    "arguments": [],
                }
            )

        # Generate selectors for all elements
        elements_with_selectors = await self._add_selectors_to_elements(
            elements, selector_map, use_accessibility_tree
        )

        self.logger.info(
            "Found elements", auxiliary={"elements": elements_with_selectors}
        )

        # Draw overlay if requested
        if options.draw_overlay:
            await draw_observe_overlay(self.stagehand_page, elements_with_selectors)

        return elements_with_selectors

    async def _add_selectors_to_elements(
        self,
        elements: list[dict[str, Any]],
        selector_map: dict[str, list[str]],
        use_accessibility_tree: bool,
    ) -> list[ObserveResult]:
        """
        Add selectors to elements based on their element IDs.

        Args:
            elements: list of elements from LLM response
            selector_map: Mapping of element IDs to selectors
            use_accessibility_tree: Whether using accessibility tree

        Returns:
            list of elements with selectors added
        """
        result = []

        for element in elements:
            element_id = element.get("elementId")
            rest = {k: v for k, v in element.items() if k != "elementId"}

            if use_accessibility_tree:
                # Generate xpath for element using CDP
                self.logger.info(
                    "Getting xpath for element",
                    auxiliary={"elementId": str(element_id)},
                )

                args = {"backendNodeId": element_id}
                response = await self.stagehand_page.send_cdp("DOM.resolveNode", args)
                object_id = response.get("object", {}).get("objectId")

                if not object_id:
                    self.logger.info(
                        f"Invalid object ID returned for element: {element_id}"
                    )
                    continue

                # Use our utility function to get the XPath
                cdp_client = await self.stagehand_page.get_cdp_client()
                xpath = await get_xpath_by_resolved_object_id(cdp_client, object_id)

                if not xpath:
                    self.logger.info(f"Empty xpath returned for element: {element_id}")
                    continue

                result.append(ObserveResult(**{**rest, "selector": f"xpath={xpath}"}))
            else:
                if str(element_id) in selector_map and selector_map[str(element_id)]:
                    result.append(
                        ObserveResult(
                            **{
                                **rest,
                                "selector": f"xpath={selector_map[str(element_id)][0]}",
                            }
                        )
                    )

        return result
