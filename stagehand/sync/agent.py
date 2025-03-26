from typing import Optional

from ..schemas import (
    AgentConfig,
    AgentExecuteOptions,
    AgentExecuteResult,
)


class SyncAgent:
    """
    Synchronous class to handle agent functionality in Stagehand
    """

    def __init__(self, stagehand_client):
        """
        Initialize a SyncAgent instance.

        Args:
            stagehand_client: The sync client used to interface with the Stagehand server.
        """
        self._stagehand = stagehand_client

    def execute(
        self, agent_config: AgentConfig, execute_options: AgentExecuteOptions
    ) -> AgentExecuteResult:
        """
        Execute a task using an autonomous agent via the Stagehand server synchronously.
        
        Args:
            agent_config (AgentConfig): Configuration for the agent, including provider and model.
            execute_options (AgentExecuteOptions): Options for execution, including the instruction.
            
        Returns:
            AgentExecuteResult: The result of the agent execution.
        """
        payload = {
            "agentConfig": agent_config.model_dump(exclude_none=True, by_alias=True),
            "executeOptions": execute_options.model_dump(exclude_none=True, by_alias=True),
        }
        
        result = self._stagehand._execute("agentExecute", payload)
        
        if isinstance(result, dict):
            return AgentExecuteResult(**result)
        return result 