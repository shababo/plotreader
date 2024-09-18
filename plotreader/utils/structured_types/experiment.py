from typing import List, Dict
from pydantic import BaseModel, Field


























# OPSIN SPECIFIC CLASSES

class OpsinVariant(BaseModel):
    aliases: List[str] = Field(default_factory=list)
    # signifiers: List[str] = Field(default_factory=list)

class OpsinSet(BaseModel):
    opsin_variants: List[OpsinVariant]