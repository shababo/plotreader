from typing import List, Dict
from pydantic import BaseModel, Field


class ExperimentVariable(BaseModel):
    aliases: List[str]
    unit: str

class IndependantVariable(ExperimentVariable):
    values: List[str | float]

class DependantVariableStatistic(ExperimentVariable):
    pass

class Experiment(BaseModel):
    independant_vars: List[ExperimentVariable]
    depdendant_vars: List[ExperimentVariable]

class Panel(BaseModel):
    experiment: Experiment
    signifiers: Dict[str]

class Signifier(BaseModel):
    name: str
    value_map: Dict[str, ExperimentVariable]


class OpsinVariant(BaseModel):
    aliases: List[str] = Field(default_factory=list)
    colors: List[str] = Field(default_factory=list)

class OpsinSet(BaseModel):
    opsin_variants: List[OpsinVariant]