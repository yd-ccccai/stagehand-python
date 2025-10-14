import asyncio
import json

import pytest

from stagehand.main import Stagehand
from stagehand.agent.agent import Agent
from tests.mocks.mock_llm import MockLLMClient, MockLLMResponse


@pytest.mark.asyncio
async def test_native_agent_fallback(monkeypatch):
    stagehand = Stagehand(env="LOCAL", use_api=False,
                          model_name="unknown-native")
    await stagehand.init()

    # Swap in a mock LLM client
    mock_llm = MockLLMClient(default_model="unknown-native")

    # Configure the mock to simulate a tool call to close with success
    def custom_agent_response(messages, **kwargs):
        class ToolCall:
            def __init__(self):
                self.id = "call-1"

                class Fn:
                    def __init__(self):
                        self.name = "close"
                        self.arguments = json.dumps(
                            {"reasoning": "done", "success": True})

                self.function = Fn()

        class Msg:
            def __init__(self):
                self.content = ""
                self.tool_calls = [ToolCall()]

        resp = MockLLMResponse("")
        resp.choices[0].message = Msg()
        return resp

    mock_llm.set_custom_response("agent", custom_agent_response)

    stagehand.llm = mock_llm
    agent: Agent = stagehand.agent(model="unknown-native")

    result = await agent.execute("test instruction")
    assert result.completed is True
    assert (result.message or "").lower().startswith("done")


@pytest.mark.asyncio
async def test_native_agent_goto_and_extract(monkeypatch):
    stagehand = Stagehand(env="LOCAL", use_api=False,
                          model_name="unknown-native")
    await stagehand.init()

    # Mock LLM to issue goto then extract then close
    sequence = []

    def make_tool_call(name, args_dict):
        class ToolCall:
            def __init__(self):
                self.id = f"call-{len(sequence)+1}"

                class Fn:
                    def __init__(self):
                        self.name = name
                        self.arguments = json.dumps(args_dict)

                self.function = Fn()
        return ToolCall()

    class Msg:
        def __init__(self, tool_calls):
            self.content = ""
            self.tool_calls = tool_calls

    def responder(messages, **kwargs):
        if not sequence:
            sequence.append("goto")
            tc = make_tool_call("goto", {"url": "https://example.com"})
            resp = MockLLMResponse("")
            resp.choices[0].message = Msg([tc])
            return resp
        elif sequence == ["goto"]:
            sequence.append("extract")
            tc = make_tool_call(
                "extract", {"instruction": "get title", "schema": None})
            resp = MockLLMResponse("")
            resp.choices[0].message = Msg([tc])
            return resp
        else:
            tc = make_tool_call(
                "close", {"reasoning": "done", "success": True})
            resp = MockLLMResponse("")
            resp.choices[0].message = Msg([tc])
            return resp

    mock_llm = MockLLMClient(default_model="unknown-native")
    mock_llm.set_custom_response("agent", responder)
    stagehand.llm = mock_llm

    agent: Agent = stagehand.agent(model="unknown-native")
    result = await agent.execute("navigate and extract")

    assert result.completed is True
    assert result.message == "done"
