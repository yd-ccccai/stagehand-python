import os
from typing import Any, Callable, Literal, Optional, Union

from browserbase.types import SessionCreateParams as BrowserbaseSessionCreateParams
from pydantic import BaseModel, ConfigDict, Field, field_validator

from stagehand.schemas import AvailableModel


class StagehandConfig(BaseModel):
    """
    Configuration for the Stagehand client.

    Attributes:
        env (str): Environment type. 'BROWSERBASE' for remote usage
        api_key (Optional[str]): BrowserbaseAPI key for authentication.
        project_id (Optional[str]): Browserbase Project identifier.
        api_url (Optional[str]): Stagehand API URL.
        browserbase_session_create_params (Optional[BrowserbaseSessionCreateParams]): Browserbase session create params.
        browserbase_session_id (Optional[str]): Session ID for resuming Browserbase sessions.
        model_name (Optional[str]): Name of the model to use.
        model_api_key (Optional[str]): Model API key.
        model_client_options (Optional[dict[str, Any]]): Options for the model client.
        logger (Optional[Callable[[Any], None]]): Custom logging function.
        verbose (Optional[int]): Verbosity level for logs (1=minimal, 2=medium, 3=detailed).
        use_rich_logging (bool): Whether to use Rich for colorized logging.
        dom_settle_timeout_ms (Optional[int]): Timeout for DOM to settle (in milliseconds).
        enable_caching (Optional[bool]): Enable caching functionality.
        self_heal (Optional[bool]): Enable self-healing functionality.
        wait_for_captcha_solves (Optional[bool]): Whether to wait for CAPTCHA to be solved.
        act_timeout_ms (Optional[int]): Timeout for act commands (in milliseconds).
        headless (bool): Run browser in headless mode
        system_prompt (Optional[str]): System prompt to use for LLM interactions.
        local_browser_launch_options (Optional[dict[str, Any]]): Local browser launch options.
        use_api (bool): Whether to use API mode.
        experimental (bool): Enable experimental features.
    """

    env: Literal["BROWSERBASE", "LOCAL"] = "BROWSERBASE"
    api_key: Optional[str] = Field(
        None, alias="apiKey", description="Browserbase API key for authentication"
    )
    project_id: Optional[str] = Field(
        None, alias="projectId", description="Browserbase project ID"
    )
    api_url: Optional[str] = Field(
        os.environ.get("STAGEHAND_API_URL",
                       "https://api.stagehand.browserbase.com/v1"),
        alias="apiUrl",
        description="Stagehand API URL",
    )
    model_api_key: Optional[str] = Field(
        None, alias="modelApiKey", description="Model API key"
    )
    model_client_options: Optional[dict[str, Any]] = Field(
        None,
        alias="modelClientOptions",
        description="Configuration options for the language model client (i.e. api_base)",
    )
    verbose: Optional[int] = Field(
        1,
        description="Verbosity level for logs: 0=minimal (ERROR), 1=medium (INFO), 2=detailed (DEBUG)",
    )
    logger: Optional[Callable[[Any], None]] = Field(
        None, description="Custom logging function"
    )
    use_rich_logging: Optional[bool] = Field(
        True, description="Whether to use Rich for colorized logging"
    )
    dom_settle_timeout_ms: Optional[int] = Field(
        3000,
        alias="domSettleTimeoutMs",
        description="Timeout for DOM to settle (in ms)",
    )
    browserbase_session_create_params: Optional[
        Union[BrowserbaseSessionCreateParams, dict[str, Any]]
    ] = Field(
        None,
        alias="browserbaseSessionCreateParams",
        description="Browserbase session create params",
    )
    enable_caching: Optional[bool] = Field(
        False, alias="enableCaching", description="Enable caching functionality"
    )
    browserbase_session_id: Optional[str] = Field(
        None,
        alias="browserbaseSessionID",
        description="Session ID for resuming Browserbase sessions",
    )
    model_name: Optional[str] = Field(
        AvailableModel.GPT_4O, alias="modelName", description="Name of the model to use"
    )
    self_heal: Optional[bool] = Field(
        True, alias="selfHeal", description="Enable self-healing functionality"
    )
    wait_for_captcha_solves: Optional[bool] = Field(
        False,
        alias="waitForCaptchaSolves",
        description="Whether to wait for CAPTCHA to be solved",
    )
    system_prompt: Optional[str] = Field(
        None,
        alias="systemPrompt",
        description="System prompt to use for LLM interactions",
    )
    local_browser_launch_options: Optional[dict[str, Any]] = Field(
        {},
        alias="localBrowserLaunchOptions",
        description="Local browser launch options",
    )
    use_api: Optional[bool] = Field(
        True,
        alias=None,
        description="Whether to use the Stagehand API",
    )
    experimental: Optional[bool] = Field(
        False,
        alias=None,
        description="Whether to use experimental features",
    )

    # --- Native Agent Initial A11y Context Injection (Python parity with TS) ---
    agent_initial_a11y_context_mode: Optional[Literal["none", "text", "json", "both"]] = Field(
        "none",
        alias="agentInitialA11yContextMode",
        description=(
            "Controls whether to inject accessibility context into the initial LLM request "
            "for the Native Agent. Options: 'none', 'text', 'json', 'both'."
        ),
    )
    agent_a11y_text_max_chars: Optional[int] = Field(
        None,
        alias="agentA11yTextMaxChars",
        description="Maximum characters for simplified text A11y context (no hardcoded model limits).",
    )
    agent_a11y_json_max_chars: Optional[int] = Field(
        None,
        alias="agentA11yJsonMaxChars",
        description="Maximum characters for JSON A11y context after pruning (no hardcoded model limits).",
    )
    agent_a11y_json_max_depth: Optional[int] = Field(
        None,
        alias="agentA11yJsonMaxDepth",
        description="Maximum depth when pruning the JSON A11y tree before injection.",
    )
    agent_a11y_json_max_children: Optional[int] = Field(
        None,
        alias="agentA11yJsonMaxChildren",
        description="Maximum children per node when pruning the JSON A11y tree before injection.",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("browserbase_session_create_params", mode="before")
    @classmethod
    def validate_browserbase_params(cls, v, info):
        """Validate and convert browserbase session create params."""
        if isinstance(v, dict) and "project_id" not in v:
            values = info.data
            project_id = values.get("project_id") or values.get("projectId")
            if project_id:
                v = {**v, "project_id": project_id}
        return v

    def with_overrides(self, **overrides) -> "StagehandConfig":
        """
        Create a new config instance with the specified overrides.

        Args:
            **overrides: Key-value pairs to override in the config

        Returns:
            StagehandConfig: New config instance with overrides applied
        """
        config_dict = self.model_dump()
        config_dict.update(overrides)
        return StagehandConfig(**config_dict)


# Default configuration instance
default_config = StagehandConfig()
