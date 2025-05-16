from typing import Union

from ..types.agent import AgentConfig, AgentExecuteOptions, AgentResult
from ..schemas import AgentProvider
from .client import AgentClient
from .openai_cua import OpenAICUAClient
from .anthropic_cua import AnthropicCUAClient
from ..handlers.cua_handler import CUAHandler

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
        # TODO: init handler
        self.handler = CUAHandler(stagehand=self.stagehand, client=self.client)
    
    # Currently only supporting CUA models
    def _get_client(self) -> AgentClient:
        provider = MODEL_TO_PROVIDER_MAP.get(self.model)
        if not provider:
            raise ValueError(f"Unsupported model: {self.model}")
        if provider == AgentProvider.OPENAI:
            return OpenAICUAClient(
                model=self.model, 
                instructions=self.instructions, 
                config=self.config
              )
        elif provider == AgentProvider.ANTHROPIC:
            return AnthropicCUAClient(
                model=self.model, 
                instructions=self.instructions, 
                config=self.config
              )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def execute(self, options_or_instruction: Union[AgentExecuteOptions, str]) -> AgentResult:
        """
        Execute a task based on the provided options or instruction string.

        Args:
            instruction (str): The instruction to execute.
            options (AgentExecuteOptions): The options for the execution.

        Returns:
            AgentResult: The result of the execution.
        """
        if isinstance(options_or_instruction, str):
            instruction = options_or_instruction
            options: AgentExecuteOptions = {"instruction": instruction} # type: ignore
        else:
            options = options_or_instruction
            instruction = options["instruction"]

        self.stagehand.logger.info(f"StagehandAgent executing instruction: {instruction}")
        
        agent_response = await self.handler.execute(instruction)
        self.stagehand.logger.info(f"Agent response: {agent_response}")

        # For now, let's assume agent_response is already in AgentResult format or adaptable
        # In reality, this would involve parsing the client's response, extracting actions, etc.
        if isinstance(agent_response, dict) and "actions" in agent_response: # very basic check
             return agent_response # type: ignore
        
        # Fallback for a stub implementation
        return {
            "actions": [],
            "result": f"Task '{instruction}' processed (stub response).",
            "usage": {"input_tokens": 0, "output_tokens": 0, "inference_time_ms": 0}
        } 