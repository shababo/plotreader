from typing import Union
import os
from pathlib import Path

from llama_index.core import Settings
from llama_index.llms.anthropic import Anthropic
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.tools.code_interpreter.base import CodeInterpreterToolSpec
from llama_index.core.agent import StructuredPlannerAgent, FunctionCallingAgentWorker

from plotreader.util import parse_matplotlib_galleries

class PlotGenerator():

    _PROMPT = (
        "Use Python to generate some data and then use Matplotlib to generate a plot from it. " +
        "When you are asked to save files, make sure they are in a unique directory in {output_dir}. " +
        "First, you want to make up some scenario and data that is represented in the plot. " +
        "Here is some text that could help you think of the type of data and plot create: {data_scenario}. " + 
        "Next, save the data into a CSV. " +
        "Then you want to plot this data using Matplotlib, but don't put quantitative labels on the plot if they are already available visually. " +
        "The plots should have the same amount of labeling you'd expect in an academic paper. Save the figure as a PNG. " +
        "Lastly, write three quantitative questions that could only be answered if the responder was able to know the values in the JSON " +
        "object but only had access to the plot. Save these questions and answers in a CSV file where the columns are `question` and `answer`. " +
        "Don't forget that the files are in a unique drectory in `./storage/plotgen_output`."
    )

    def __init__(
        self,
        vector_store_path: str = None,
    ):
        
        self._vector_store_path = vector_store_path
        self._is_spawn = False
        self._vec_index = None
        self._agent = None

    def spawn(self):

        if not self._is_spawn:
            self._vec_index = parse_matplotlib_galleries(self._vector_store_path)

        vector_query_engine = self._vec_index.as_query_engine(llm=Settings.llm, similarity_top_k=10)
        tools = [
            QueryEngineTool(
                query_engine=vector_query_engine,
                metadata=ToolMetadata(
                    name="vector_tool",
                    description="This tool can query the matplotlib gallery examples.",
                ),
            ),
        ] + CodeInterpreterToolSpec().to_tool_list()

        # build agent
        function_llm = Anthropic(model="claude-3-5-sonnet-20240620", max_tokens=2048)
        tool_agent_worker = FunctionCallingAgentWorker.from_tools(
            tools,
            llm=function_llm,
            verbose=True
        )

        self._agent = StructuredPlannerAgent(
            tool_agent_worker, tools=tools, verbose=True
        )

    
    def run(self, output_dir: str, data_scenario: str = None):
        
        data_scenario = data_scenario or "Make up whatever you want!"
        response = self._agent.query(self._PROMPT.format(output_dir=output_dir, data_scenario=data_scenario))
            



