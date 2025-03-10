from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, field_serializer

# Default extraction schema that matches the TypeScript version
DEFAULT_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {"extraction": {"type": "string"}},
    "required": ["extraction"],
}


class AvailableModel(str, Enum):
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    CLAUDE_3_5_SONNET_LATEST = "claude-3-5-sonnet-latest"
    CLAUDE_3_7_SONNET_LATEST = "claude-3-7-sonnet-latest"


class StagehandBaseModel(BaseModel):
    """Base model for all Stagehand models with camelCase conversion support"""
    
    class Config:
        populate_by_name = True  # Allow accessing fields by their Python name
        alias_generator = lambda field_name: ''.join(
            [field_name.split('_')[0]] + 
            [word.capitalize() for word in field_name.split('_')[1:]]
        )  # snake_case to camelCase


class ActOptions(StagehandBaseModel):
    """
    Options for the 'act' command.

    Attributes:
        action (str): The action command to be executed by the AI.
        variables: Optional[Dict[str, str]] = None
        model_name: Optional[AvailableModel] = None
        slow_dom_based_act: Optional[bool] = None
    """

    action: str = Field(..., description="The action command to be executed by the AI.")
    variables: Optional[Dict[str, str]] = None
    model_name: Optional[AvailableModel] = None
    slow_dom_based_act: Optional[bool] = None


class ActResult(StagehandBaseModel):
    """
    Result of the 'act' command.

    Attributes:
        success (bool): Whether the action was successful.
        message (str): Message from the AI about the action.
        action (str): The action command that was executed.
    """

    success: bool = Field(..., description="Whether the action was successful.")
    message: str = Field(..., description="Message from the AI about the action.")
    action: str = Field(..., description="The action command that was executed.")


class ExtractOptions(StagehandBaseModel):
    """
    Options for the 'extract' command.

    Attributes:
        instruction (str): Instruction specifying what data to extract using AI.
        model_name: Optional[AvailableModel] = None
        selector: Optional[str] = None
        schema_definition (Union[Dict[str, Any], Type[BaseModel]]): A JSON schema or Pydantic model that defines the structure of the expected data.
            Note: If passing a Pydantic model, invoke its .model_json_schema() method to ensure the schema is JSON serializable.
        use_text_extract: Optional[bool] = None
    """

    instruction: str = Field(
        ..., description="Instruction specifying what data to extract using AI."
    )
    model_name: Optional[AvailableModel] = None
    selector: Optional[str] = None
    # IMPORTANT: If using a Pydantic model for schema_definition, please call its .model_json_schema() method
    # to convert it to a JSON serializable dictionary before sending it with the extract command.
    schema_definition: Union[Dict[str, Any], Type[BaseModel]] = Field(
        default=DEFAULT_EXTRACT_SCHEMA,
        description="A JSON schema or Pydantic model that defines the structure of the expected data.",
    )
    use_text_extract: Optional[bool] = True

    @field_serializer('schema_definition')
    def serialize_schema_definition(self, schema_definition: Union[Dict[str, Any], Type[BaseModel]]) -> Dict[str, Any]:
        """Serialize schema_definition to a JSON schema if it's a Pydantic model"""
        if isinstance(schema_definition, type) and issubclass(schema_definition, BaseModel):
            return schema_definition.model_json_schema()
        return schema_definition

    class Config:
        arbitrary_types_allowed = True


class ExtractResult(StagehandBaseModel):
    """
    Result of the 'extract' command.

    This is a generic model to hold extraction results of different types.
    The actual fields will depend on the schema provided in ExtractOptions.
    """

    # This class is intentionally left without fields so it can accept
    # any fields from the extraction result based on the schema

    class Config:
        extra = "allow"  # Allow any extra fields

    def __getitem__(self, key):
        """
        Enable dictionary-style access to attributes.
        This allows usage like result["selector"] in addition to result.selector
        """
        return getattr(self, key)


class ObserveOptions(StagehandBaseModel):
    """
    Options for the 'observe' command.

    Attributes:
        instruction (str): Instruction detailing what the AI should observe.
        model_name: Optional[AvailableModel] = None
        only_visible: Optional[bool] = None
        return_action: Optional[bool] = None
        draw_overlay: Optional[bool] = None
    """

    instruction: str = Field(
        ..., description="Instruction detailing what the AI should observe."
    )
    only_visible: Optional[bool] = False
    model_name: Optional[AvailableModel] = None
    return_action: Optional[bool] = None
    draw_overlay: Optional[bool] = None


class ObserveResult(StagehandBaseModel):
    """
    Result of the 'observe' command.
    """

    selector: str = Field(..., description="The selector of the observed element.")
    description: str = Field(
        ..., description="The description of the observed element."
    )
    backend_node_id: Optional[int] = None
    method: Optional[str] = None
    arguments: Optional[List[str]] = None

    def __getitem__(self, key):
        """
        Enable dictionary-style access to attributes.
        This allows usage like result["selector"] in addition to result.selector
        """
        return getattr(self, key)
