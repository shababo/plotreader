from typing import List
from pydantic import BaseModel, Field







class Experiment(BaseModel):
    independent_variables: List[str]
    dependent_variables: List[str]

class IndependentVariable(BaseModel):
    name: str
    values: list = Field(default_factory=list)
    unit: str = Field(default = "None")

class DependentVariable(BaseModel):
    name: str
    statistics: list[str] = Field(default_factory=list)
    unit: str = Field(default = "None")






