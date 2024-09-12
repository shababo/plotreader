from typing import Union
import os
from pathlib import Path

from llama_index.core import Settings
from llama_index.llms.anthropic import Anthropic
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.tools.code_interpreter.base import CodeInterpreterToolSpec
from llama_index.core.agent import StructuredPlannerAgent, FunctionCallingAgentWorker

from plotreader.util import parse_matplotlib_galleries, parse_seaborn_examples
from plotreader.prompt import _INITIAL_PLAN_PROMPT, _PLAN_REFINE_PROMPT, _PLOTGEN_PROMPT

def _load_example():
    pass

class PlotGenerator():

    

    def __init__(
        self,
        vector_store_path: str = None,
    ):
        
        self._vector_store_path = vector_store_path
        self._is_spawned = False
        self._vec_index = {}
        self._agent = None

    def spawn(self):

        if not self._is_spawned:
            self._vec_index['matlab'] = parse_matplotlib_galleries(os.path.join(self._vector_store_path, 'matplotlab_galleries'))
            self._vec_index['seaborn'] = parse_seaborn_examples(os.path.join(self._vector_store_path, 'seaborn_examples'))

        tools = [
            QueryEngineTool(
                query_engine=self._vec_index['matlab'].as_query_engine(similarity_top_k=5),
                metadata=ToolMetadata(
                    name="matplotlib_vector_tool",
                    description="This tool can query the matplotlib gallery examples.",
                ),
            ),
            QueryEngineTool(
                query_engine=self._vec_index['seaborn'].as_query_engine(similarity_top_k=5),
                metadata=ToolMetadata(
                    name="seaborn_vector_tool",
                    description="This tool can query the seaborn examples examples.",
                ),
            ),
        ] + CodeInterpreterToolSpec().to_tool_list()

        # build agent
        tool_agent_worker = FunctionCallingAgentWorker.from_tools(
            tools,
            # llm=Anthropic(model='claude-3-5-sonnet-20240620', max_tokens=2048, temperature=0.1),
            verbose=True,
            max_function_calls=2
        )

        self._agent = StructuredPlannerAgent(
            tool_agent_worker, 
            tools=tools, 
            verbose=True, 
            # llm=Anthropic(
            #     model='claude-3-5-sonnet-20240620', 
            #     max_tokens=2048, 
            #     temperature=0.1
            # ),
            initial_plan_prompt=_INITIAL_PLAN_PROMPT,
            plan_refine_prompt=_PLAN_REFINE_PROMPT,
            # delete_task_on_finish=True,
        )

    
    def run(self, output_dir: str, data_scenario: str = None):

        if not self._is_spawned:
            self.spawn()

        data_scenario = data_scenario or "Make up whatever you want!"
        response = self._agent.query(_PLOTGEN_PROMPT.format(output_dir=output_dir, data_scenario=data_scenario))
            



