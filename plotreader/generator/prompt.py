_INITIAL_PLAN_PROMPT = """\
You will be creating a plan to generate data, plots, and questions about the plots. The plan should end with a sub-task that can achieve the overall task.
Luckily we have a plan that you can start with. Try to stay as close to this plan as possible!

Example Plan for this task. Only change this plan if necessary or to make it more concise.:
=== Initial plan ===
review_examples_and_data_scenario_prompt:
Read the input prompt and look at the example papers and figures given. 
In particular, note the the types of information in each figure panel, the type of plot, and something related to the number of data points. 
If no examples exist, do your best to imagine what they would be given the other inputs.
-> Summary of a few representatitive figure panels with information about what they plot and how they plot it.
deps: []


create_panel_idea:
Generate an idea for a panel that would look like it came from the examples or data scenario.
Ensure that you can generate data for the panel that has realistic structure.
Choose the most data rich and sophisticated plot that would be appropriate.
Create plots similar to the exmaple figures in terms of style, amount of information, and types information.
When possible, use types of plots where statistics other than the mean are available (violin, box and whisker, errobar, etc.).
-> Detailed description of the data and plot.
deps: [review_examples_and_data_scenario_prompt]


determine_how_to_plot:
Determine how we are going to plot the data using Seaborn and/or Matplotlib.
When possible, use types of plots where statistics other than the mean are available (violin, box and whisker, errobar, etc.).
Seaborn is particularly useful when adding statistics into plots, like errorbars or fills or scatters of individual data points with lines going through means, etc.
The plots should be information rich but not overwhelming. Rely on Seaborn as much as possible. 
Ensure a consistant styling and labeling scheme throughout.
-> Description of how to make plots programmatically.
deps: [create_panel_idea]


determine_how_to_generate_data:
Determine how to generate realistic data.
If provided, you could extract information from the example figures or papers and maniuplate or recombine that.
-> Desciption of how to generate data.
deps: [determine_how_to_plot]

generate_data_and_plot:
Generate the data and plot. Save them to a unique directory in the output directory provided in the instructions.
-> Confirmation of file saving and the location of the files.
deps: [determine_how_to_generate_data]
"""

xx_INITIAL_PLAN_PROMPT = """\
You will be creating a plan to generate data, plots, and questions about the plots. The plan should end with a sub-task that can achieve the overall task.
Luckily we have a plan that you can start with. Try to stay as close to this plan as possible!

When writing prompts and thinking through things, be AS CONCISE AS POSSIBLE. You only need to make some data.
Avoid plots that are mostly noise.
Rely on Seaborn for styling and plotting as much as possible.
Don't save any files until you are absolutely read to save the final files and save them in the appropriate place!!
Avoiding opening or "showing" figures.

Example Plan for this task. Only change this plan if necessary or to make it more concise.:
=== Initial plan ===
create_data_scenario:
Look at the provided data scenario text and use the examples tool to review the input examples. 
Then think of a figure idea based on that input and way to generate the data to create it.
When describing things, focus on the data, its structure, and how to plot it.
DO NOT FOCUS ON EXPLAINING THE UNDERLYING BIOLOGY OR WHAT THE DATA MEANS!
In particular, you could use the data extracted from the examples and maniuplate it to generate similar plots.
Alternatively, you could think of a mathematical model to generate the data so it can some effect and not just be noise.
Multiple panels are okay and encouraged. Think about the types of figures one sees in academic papers. -> A description of the data and how it will be generated, and description of each plot.
deps: []


generate_data:
Create corresponding data. Generate only the information used to make the plots. 
Remember, you could use the data extracted from the examples and maniuplate it to generate similar plots. 
In particular, you could use the data extracted from the examples and maniuplate it to generate similar plots.
Alternatively, you could think of a mathematical model to generate the data so it can some effect and not just be noise.
Ensure the structure of the data makes sense from a physical or biological perspective.
Do not save anything. Return the code for generating the data in your message.  -> Code for generating the data.
deps: ['create_data_scenario']


create_plot:
Create a plot using the generated data by appending new code to the code generated from the previous step. 
Create plots similar to the exmaple figures in terms of style, amount of information, and types information.
When possible, use types of plots where statistics other than the mean are available (violin, box and whisker, errobar, etc.).
Seaborn is particularly useful when adding statistics into plots, like errorbars or fills or scatters of individual data points with lines going through means, etc.
The plots should be information rich but not overwhelming. Rely on Seaborn as much as possible. 
Ensure a consistant styling and labeling scheme throughout.
Do not save anything. Return the new code. -> The data generation code and plotting code in one script.
deps: ['generate_data']


generate_questions_and_answers:
Generate three quantitative questions and answers based on the data which can be answered by looking at the plot. 
These questions should not involve any computation that a human couldn't do fairly easily in their head while looking at the figure. 
There should be any easy, medium, and hard difficulty question.  -> The previous script with a new section at the end which generates the questions, answeres, and difficulty scores.
deps: ['create_plot']


review_code:
Review the final code for generating all of the targets. Ensure it meets all rules and requests in the initial prompt and plan. -> Revised code if necessary.
deps: ['generate_questions_and_answers']


save_files:
Save the generated data to a CSV file in the unique directory within the specified root save folder in the intitial prompt. 
Do this by adding code to the scipt we've been working to save the figure, data, and questions each to their own file. -> Confirmation that the final script has been run and that the files have been saved.
deps: ['review_code']


The tools available are:
{tools_str}

Overall Task: {task}
"""

_PLOTGEN_PROMPT = (
        "Use Python to generate some data and then use Seaborn (and maybe Matplotlib) to generate a plot from it. " +
        "First, you want to make up some scenario related to the biological sciences and data that is represented in the plot. " +
        "Here is some text that could help you think of the type of data and plot create: {data_scenario}. " + 
        "There may also be some provided example papers and figures related to the data scenario. " +
        "Then you want to plot this data using Seaborn and Matplotlib, but don't put quantitative labels on the plot if they are already available visually. " +
        "The plot should have the same amount of labeling you'd expect in an academic paper. Save the figure as a PNG. "
        # "Lastly, write three quantitative questions that could only be answered if the responder was able to understand the quantitative information in the plots. " +
        # "Save these questions and answers in a new CSV file where the columns are `question` and `answer` and `difficulty`. " +
        # "There should be an easy, medium, and hard difficulty question. " +
        # "Don't forget the following important details: \n" +
        # "   1. The files are saved in a unique drectory in {output_dir}.\n" +
        # "   2. Make sure the plot you are generating is unique by generating data in a random manner.\n" +
        # "   3. All data in the saved structures should be in the plots. Do not include extra data. \n"
    )

_PLAN_REFINE_PROMPT = """
There should not be a need to do this. Keep the plan as is.

But also, remember these important points when working. Feel free to remind yourself.

When writing prompts and thinking through things, be AS CONCISE AS POSSIBLE. You only need to make some data. You don't need to go on at length about the biological details. Only include what's absolutely necessary to generate good figures and data.
Use data from the examples to generate new data if examples are provided.
Avoid plots that are mostly noise.
Rely on Seaborn for styling and plotting as much as possible.
Don't save any files until you are absolutely read to save the final files and save them in the appropriate place!!
Avoiding opening or "showing" figures.
"""

_DEFAULT_SCENARIO = "Randomly come up with five biological or biotech data scenarios and choose one."