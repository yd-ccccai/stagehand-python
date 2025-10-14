from __future__ import annotations

import json
from typing import Any, Optional

from stagehand.llm.client import LLMClient
from stagehand.schemas import AgentExecuteOptions
from stagehand.types.agent import AgentConfig, AgentResult, AgentUsage

from .client import AgentClient
from .native_tools import tool_dispatch
from .tool_schema import build_openai_tools_schemas


def _safe_parse_json(text: Optional[str]) -> dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        return {}


def _usage_from_response(resp: Any) -> AgentUsage:
    prompt = getattr(getattr(resp, "usage", object()), "prompt_tokens", 0)
    completion = getattr(getattr(resp, "usage", object()),
                         "completion_tokens", 0)
    # If the client exposes hidden usage (e.g., mocks)
    if prompt == 0 and hasattr(resp, "_hidden_params"):
        usage = resp._hidden_params.get("usage", {})
        prompt = usage.get("prompt_tokens", 0)
        completion = usage.get("completion_tokens", 0)
    return AgentUsage(
        input_tokens=int(prompt or 0),
        output_tokens=int(completion or 0),
        inference_time_ms=0,
    )


class NativeAgentClient(AgentClient):
    def __init__(
        self,
        model: str,
        instructions: Optional[str],
        config: Optional[AgentConfig],
        logger: Any,
        handler: Any,  # Unused for NativeAgent
        viewport: Optional[dict[str, int]] = None,
        experimental: bool = False,
    ):
        super().__init__(model, instructions, config,
                         logger, handler)  # type: ignore[arg-type]
        # The Native agent uses the Stagehand's LLM client directly (LOCAL mode)
        # type: ignore[assignment]
        self.llm: LLMClient = handler.stagehand.llm if handler else None
        self.stagehand = handler.stagehand if handler else None
        self.viewport = viewport
        self.experimental = experimental

    def format_screenshot(self, screenshot_base64: str) -> Any:  # pragma: no cover - unused for Native
        return {"type": "image", "data": screenshot_base64}

    def _format_initial_messages(self, instruction: str, screenshot_base64: Optional[str]):  # pragma: no cover - unused for Native
        return []

    def _process_provider_response(self, response: Any):  # pragma: no cover - not using provider
        return None

    def _format_action_feedback(self, action, action_result, new_screenshot_base64):  # pragma: no cover - unused
        return []

    def key_to_playwright(self, key: str) -> str:  # pragma: no cover - unused in Native
        return key

    async def run_task(
        self,
        instruction: str,
        max_steps: int = 20,
        options: Optional[AgentExecuteOptions] = None,
    ) -> AgentResult:
        if not self.stagehand or not self.stagehand.page:
            return AgentResult(
                message="Stagehand page not initialized.",
                completed=True,
                actions=[],
                usage=AgentUsage(
                    input_tokens=0, output_tokens=0, inference_time_ms=0),
            )

        messages: list[dict[str, Any]] = []
        if self.instructions:
            messages.append({"role": "system", "content": self.instructions})
        messages.append({"role": "user", "content": instruction})

        tools = build_openai_tools_schemas()

        for _ in range(max_steps or 10):
            try:
                resp = await self.llm.create_response(  # type: ignore[union-attr]
                    model=self.config.model or self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.2,
                    function_name="AGENT",
                )
            except Exception as e:
                self.logger.error(
                    f"LLM error in NativeAgent: {e}", category="agent")
                return AgentResult(
                    message=f"Error: {e}",
                    completed=True,
                    actions=[],
                    usage=AgentUsage(
                        input_tokens=0, output_tokens=0, inference_time_ms=0),
                )

            usage = _usage_from_response(resp)
            msg = resp.choices[0].message

            # OpenAI-style tool calls on message.tool_calls
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": getattr(msg, "content", None) or "",
                        "tool_calls": tool_calls,
                    }
                )
                for tc in tool_calls:
                    name = getattr(
                        getattr(tc, "function", object()), "name", None)
                    args_text = getattr(
                        getattr(tc, "function", object()), "arguments", None)
                    if not name:
                        invalid = {
                            "success": False, "error": "Invalid tool call: missing function name"}
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": getattr(tc, "id", None),
                                "content": json.dumps(invalid),
                            }
                        )
                        continue
                    args = _safe_parse_json(args_text)
                    result = await tool_dispatch(self.stagehand, name, args)

                    # If tool is close and completed, exit
                    if name == "close" and result.get("completed"):
                        return AgentResult(
                            message=result.get("message"),
                            completed=True,
                            actions=[],
                            usage=usage,
                        )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": getattr(tc, "id", None),
                            "content": json.dumps(result),
                        }
                    )
                # Continue loop for next step
                continue

            # No tool calls → treat as final answer
            final_text = getattr(msg, "content", None) or ""
            return AgentResult(message=str(final_text), completed=True, actions=[], usage=usage)

        return AgentResult(
            message="Reached maxSteps without close",
            completed=False,
            actions=[],
            usage=AgentUsage(input_tokens=0, output_tokens=0,
                             inference_time_ms=0),
        )
