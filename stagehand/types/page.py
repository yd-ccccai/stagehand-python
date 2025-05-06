from pydantic import BaseModel


class ObserveElementSchema(BaseModel):
    element_id: int
    description: str
    method: str
    arguments: list[str]


class ObserveInferenceSchema(BaseModel):
    elements: list[ObserveElementSchema]
