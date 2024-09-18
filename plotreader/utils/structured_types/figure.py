from typing import List
from pydantic import BaseModel, Field

from plotreader.utils.structured_types.experiment import Experiment


class Plot(BaseModel):
    name: str
    experiments: List[Experiment]

class Panel(BaseModel):
    name: str
    plots: list[Plot]

class Figure(BaseModel):
    panels: List[Panel]
    # statistics: List[str]
