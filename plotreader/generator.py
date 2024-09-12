from typing import Union, List, Any
import os
from pathlib import Path

from llama_index.core import Settings
from llama_index.llms.anthropic import Anthropic
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.tools.code_interpreter.base import CodeInterpreterToolSpec
from llama_index.core.agent import StructuredPlannerAgent, FunctionCallingAgentWorker


from plotreader.prompt import _INITIAL_PLAN_PROMPT, _PLAN_REFINE_PROMPT, _PLOTGEN_PROMPT, _DEFAULT_SCENARIO
from plotreader.document import GitHubRepoHandler, DirectoryHandler

# Get the directory this file is in
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STORAGE_DIR = os.path.join('..', 'storage')

class PlotGenerator():

    def __init__(
        self,
        llm: Any = None,
        storage_dir: str = None,
        data_scenario: str = None,
        examples_dir: str = None,
        auto_spawn: bool = False,
    ):
        
        self._llm = llm or Settings.llm
        self._storage_dir = storage_dir or DEFAULT_STORAGE_DIR
        self._default_data_scenario = data_scenario or _DEFAULT_SCENARIO
        self._examples_dir = examples_dir
        
        self._is_spawned = False
        self._vec_index = {}
        self._agent = None

        self._instantiate_plotting_repo_handlers()

        if auto_spawn:
            self.spawn()

    def set_scenario(self, data_scenario: str = None, examples_dir: str = None) -> None:

        data_scenario = data_scenario or self._default_data_scenario
        gen_output_dir = os.path.join(self._storage_dir,'output')
        
        self._query_prompt = _PLOTGEN_PROMPT.format(output_dir=gen_output_dir, data_scenario=data_scenario)

        examples_dir = examples_dir or self._examples_dir
        # self._examples_handler = DirectoryHandler()

    def _instantiate_plotting_repo_handlers(self) -> None:
 
        self._plotting_repos = {}
        self._plotting_repos['matplotlib'] = GitHubRepoHandler(
            name = 'matplotlib_galleries',
            repo = 'matplotlib',
            owner = 'matplotlib',
            desc = 'All of the code for the Matplotlib galleries.',
            storage_dir = os.path.join(self._storage_dir,'indexes'),
            include_dirs = ['galleries'],
            include_exts = ['.py'],
            language = 'python'
        )

        self._plotting_repos['seaborn'] = GitHubRepoHandler(
            name = 'seaborn_examples',
            repo = 'seaborn',
            owner = 'mwaskom',
            branch = 'master',
            desc = 'All of the code for the Seaborn examples.',
            storage_dir = os.path.join(self._storage_dir,'indexes'),
            include_dirs = ['examples'],
            include_exts = ['.py'],
            language = 'python'
        )

    def _get_plotting_repo_tools(self):

        return [handler.query_engine_tool() for handler_name, handler in self._plotting_repos.items()]
    
    def spawn(self, force_respawn: bool = False):

        if force_respawn or not self._is_spawned:

            plotting_repo_tools = self._get_plotting_repo_tools()

            code_interpreter_tools = CodeInterpreterToolSpec().to_tool_list()

            tools = plotting_repo_tools + code_interpreter_tools

            # build agent   
            tool_agent_worker = FunctionCallingAgentWorker.from_tools(
                tools,
                llm=self._llm,
                verbose=True,
                max_function_calls=5
            )

            self._agent = StructuredPlannerAgent(
                tool_agent_worker, 
                tools=tools, 
                verbose=True, 
                llm=self._llm,
                initial_plan_prompt=_INITIAL_PLAN_PROMPT,
                plan_refine_prompt=_PLAN_REFINE_PROMPT,
            )

    
    def generate(self, data_scenario: str = None, examples_dir: List[str] = None):

        if not self._is_spawned:
            self.spawn()
        
        self.set_scenario(data_scenario=data_scenario, examples_dir=examples_dir)

        response = self._agent.query(self._query_prompt)
        return response
            



