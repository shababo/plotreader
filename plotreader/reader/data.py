from typing import List
from pydantic import BaseModel, Field

class IndependantVariable(BaseModel):
    aliases: List[str]

class Signifier(BaseModel):
    values: List[str]


class OpsinVariant(BaseModel):
    aliases: List[str] = Field(default_factory=list)
    colors: List[str] = Field(default_factory=list)

class OpsinSet(BaseModel):
    opsin_variants: List[OpsinVariant]