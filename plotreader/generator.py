from typing import Union
import os
from pathlib import Path

from llama_index.core import Settings
from llama_index.llms.anthropic import Anthropic
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.tools.code_interpreter.base import CodeInterpreterToolSpec
from llama_index.core.agent import StructuredPlannerAgent, FunctionCallingAgentWorker

from plotreader.util import parse_matplotlib_galleries

def _load_example():
    pass

class PlotGenerator():

    _INITIAL_PLAN_PROMPT = """\
You will be creating a plan to generate data, plots, and questions. Think step-by-step. Given a task and a set of tools, create a comprehesive, end-to-end plan to accomplish the given task.
Keep in mind not every task needs to be decomposed into multiple sub-tasks if it is simple enough.
The plan should end with a sub-task that can achieve the overall task.

Example Plan for this task. Only change this plan if it seems absolutely necessary.:
=== Initial plan ===
generate_scenario_and_figure_idea:
Generate a scenario and describe the data and how it will be plotted in the figure. Multiple panels are okay. -> A description of the scenario and the figure.
deps: []


review_details_and_rules:
Confirm that the plan follows all of the details and rules given. -> A description of the scenario and the figure.
deps:['generate_scenario_and_figure_idea']


generate_data:
Create corresponding data. Remember there shouldn't be any extra data. Only what is used to make the plot. -> A pandas DataFrame with the generated data.
deps: ['review_details_and_rules']


create_matplotlib_plot:
Create a Matplotlib plot using the generated data -> A Matplotlib figure object
deps: ['generate_data']


generate_questions_and_answers:
Generate three quantitative questions and answers based on the data which can be answered by looking at the plot. These questions should not involve any computation that a human couldn't do fairly easily in their head while looking at the figure. There should be any easy, medium, and hard difficulty question. -> A pandas dataframe of three questions, their difficulty, and their corresponding answers
deps: ['create_matplotlib_plot']


create_directory:
Create a unique directory in ./storage/plotgen_output -> A unique directory path
deps: ['generate_questions_and_answers']


save_files:
Save the generated data to a CSV file in the unique directory. Save the generated figure to a PNG file in the same directory. Save the quetsions as a CSV in the same directory. -> Confirmation that the CSV file has been saved and the directory where they were saved.
deps: ['create_directory']


review:
Load the saved files and confirm one more time that all details and rules have been incorporated -> Confirmation of task completion.
deps: ['save_files']

The tools available are:
{tools_str}

Overall Task: {task}
"""

    _PROMPT = (
        "Use Python to generate some data and then use Matplotlib to generate a plot from it. " +
        "When you are asked to save files, make sure they are in a unique directory inside the directory {output_dir}. " +
        "The name of this directory should have the same prefix name as the saved files. " +
        "First, you want to make up some scenario related to the biological sciences and data that is represented in the plot. " +
        "Here is some text that could help you think of the type of data and plot create: {data_scenario}. " + 
        "Be sure to make up specific names for everything that are plausible. " +
        "Next, save the data into a single CSV. " +
        "Then you want to plot this data using Matplotlib, but don't put quantitative labels on the plot if they are already available visually. " +
        "The plots should have the same amount of labeling you'd expect in an academic paper. Save the figure as a PNG. " +
        "Lastly, write three quantitative questions that could only be answered if the responder was able to know the values in the data CSV " +
        "but only had access to the plot. Save these questions and answers in a new CSV file where the columns are `question` and `answer`. " +
        "Don't forget the following important details: \n" +
        "   1. The files are saved in a unique drectory in {output_dir}.\n" +
        "   2. Make sure the plot you are generating is unique by generating data in a random manner.\n" +
        "   3. All data in the saved structures should be in the plots. Do not include extra data. \n"
        "And lastly, the plan here should be quite clear. You do not need to do a bunch of loops to figure it out. " +
        "You also should only ever write each file one time."
    )

    _PLAN_REFINE_PROMPT = "There should not be a need to do this. Keep the plan as is."

    def __init__(
        self,
        vector_store_path: str = None,
    ):
        
        self._vector_store_path = vector_store_path
        self._is_spawned = False
        self._vec_index = None
        self._agent = None

    def spawn(self):

        if not self._is_spawned:
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
        tool_agent_worker = FunctionCallingAgentWorker.from_tools(
            tools,
            llm=Anthropic(model='claude-3-5-sonnet-20240620', max_tokens=2048, temperature=0.4),
            verbose=True
        )

        self._agent = StructuredPlannerAgent(
            tool_agent_worker, 
            tools=tools, 
            verbose=True, 
            llm=Anthropic(
                model='claude-3-5-sonnet-20240620', 
                max_tokens=2048, 
                temperature=0.4
            ),
            initial_plan_prompt=self._INITIAL_PLAN_PROMPT,
            plan_refine_prompt=self._PLAN_REFINE_PROMPT,
        )

    
    def run(self, output_dir: str, data_scenario: str = None):

        if not self._is_spawned:
            self.spawn()

        data_scenario = data_scenario or "Make up whatever you want!"
        response = self._agent.query(self._PROMPT.format(output_dir=output_dir, data_scenario=data_scenario))
            



