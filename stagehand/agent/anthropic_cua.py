from .client import AgentClient
from ..types import AgentConfig

class AnthropicCUAClient(AgentClient):
    def __init__(self, config: AgentConfig):
        self.config = config
