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


class Section(BaseModel):
    header: str
    level: int

class PageMetadata(BaseModel):
    page_number: int
    figure_count: int
    figure_names: List[str]
    section_headers: List[str]
    contains_fig_caption: bool = Field(..., description="Does any part of a figure caption exist on this page?")
