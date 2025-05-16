from typing import Union

from ..types import AgentConfig, AgentExecuteOptions, AgentResult, AgentProvider
from .client import AgentClient
from .openai_cua import OpenAICUAClient
from .anthropic_cua import AnthropicCUAClient

MODEL_TO_PROVIDER_MAP: dict[str, AgentProvider] = {
    "computer-use-preview": AgentProvider.OPENAI,
    "claude-3-5-sonnet-20240620": AgentProvider.ANTHROPIC,
    "claude-3-7-sonnet-20250219": AgentProvider.ANTHROPIC,
}

class Agent:
    
    def __init__(self, stagehand_client, **kwargs):
        self.stagehand = stagehand_client
        self.config = AgentConfig(**kwargs)
        self.model = self.config.model
        self.instructions = self.config.instructions
        # Provisioning for non-cua
        self.client = self._get_client() if self.stagehand.env == "LOCAL" else None
        self.handler = None
    
    # Currently only supporting CUA models
    def _get_client(self) -> AgentClient:
        provider = MODEL_TO_PROVIDER_MAP.get(self.model)
        if not provider:
            raise ValueError(f"Unsupported model: {self.model}")
        if provider == AgentProvider.OPENAI:
            return OpenAICUAClient(self.config)
        elif provider == AgentProvider.ANTHROPIC:
            return AnthropicCUAClient(self.config)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def execute(self, options_or_instruction: Union[AgentExecuteOptions, str]) -> AgentResult:
        """Execute a task based on the provided options or instruction string."""
        if isinstance(options_or_instruction, str):
            instruction = options_or_instruction
            options: AgentExecuteOptions = {"instruction": instruction} # type: ignore
        else:
            options = options_or_instruction
            instruction = options["instruction"]

        self.logger.info(f"StagehandAgent executing instruction: {instruction}")
        
        # This will eventually call self.client.execute_task and process its result
        # For now, return a placeholder result
        # Actual agent logic to interact with the client (e.g., OpenAI, Anthropic) will go here.
        
        # Placeholder, assuming the client.execute_task would return something compatible
        # with AgentResult or that this method would transform it.
        agent_response = await self.client.execute_task(instruction, options=options) # type: ignore

        # For now, let's assume agent_response is already in AgentResult format or adaptable
        # In reality, this would involve parsing the client's response, extracting actions, etc.
        if isinstance(agent_response, dict) and "actions" in agent_response: # very basic check
             return agent_response # type: ignore
        
        # Fallback for a stub implementation
        self.logger.warning("StagehandAgent.execute is using a stub implementation.")
        return {
            "actions": [],
            "result": f"Task '{instruction}' processed (stub response).",
            "usage": {"input_tokens": 0, "output_tokens": 0, "inference_time_ms": 0}
        } 