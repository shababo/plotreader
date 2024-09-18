from typing import List
from pydantic import BaseModel, Field







class Experiment(BaseModel):
    independant_variables: List[str]
    dependant_variables: List[str]

class IndependantVariable(BaseModel):
    name: str
    values: list = Field(default_factory=list)
    unit: str = Field(default = "None")

class DependantVariable(BaseModel):
    name: str
    statistics: list[str] = Field(default_factory=list)
    unit: str = Field(default = "None")






