_INITIAL_PLAN_PROMPT = """\
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
Then think of a figure idea and way to generate the data to create it.
In particular, you could use the data extracted from the examples and maniuplate it to generate similar plots.
Alternatively, you could think of a mathematical model to generate the data so it can some effect and not just be noise.
Multiple panels are okay and encouraged. Think about the types of figures one sees in academic papers. -> A description of the data and how it will be generated, and description of each plot.
deps:[]


generate_data:
Create corresponding data. Generate only the information used to make the plots, not raw data. That is, no analysis or processing should be needed to generate the plots from the data.  Do not save anything. Return the code for generating the data in your message.  -> Code for generating the data.
deps: ['create_data_scenario']


create_plot:
Create a plot using the generated data by appending new code to the code generated from the previous step. Make sure that the stylistic choices are optimzed for the quantitative display of information. The plots should be information rich but not overwhelming. Rely on Seaborn as much as possible. Do not save anything. Return the new code. -> The data generation code and plotting code in one script.
deps: ['generate_data']


generate_questions_and_answers:
Generate three quantitative questions and answers based on the data which can be answered by looking at the plot. These questions should not involve any computation that a human couldn't do fairly easily in their head while looking at the figure. There should be any easy, medium, and hard difficulty question.  -> The previous script with a new section at the end which generates the questions, answeres, and difficulty scores.
deps: ['create_plot']


review_code:
Review the final code for generating all of the targets. Ensure it meets all rules and requests in the initial prompt and plan. -> Revised code if necessary.
deps: ['generate_questions_and_answers']


save_files:
Save the generated data to a CSV file in the unique directory within the specified root save folder in the intitial prompt. Do this by adding code to the scipt we've been working to save the figure, data, and questions each to their own file. -> Confirmation that the final script has been run and that the files have been saved.
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
        "The plots should have the same amount of labeling you'd expect in an academic paper. Save the figure as a PNG. " +
        "Lastly, write three quantitative questions that could only be answered if the responder was able to understand the quantitative information in the plots. " +
        "Save these questions and answers in a new CSV file where the columns are `question` and `answer` and `difficulty`. " +
        "There should be an easy, medium, and hard difficulty question. " +
        "Don't forget the following important details: \n" +
        "   1. The files are saved in a unique drectory in {output_dir}.\n" +
        "   2. Make sure the plot you are generating is unique by generating data in a random manner.\n" +
        "   3. All data in the saved structures should be in the plots. Do not include extra data. \n"
    )

_PLAN_REFINE_PROMPT = """
There should not be a need to do this. Keep the plan as is.

But also, remember these important points when working. Feel free to remind yourself.

When writing prompts and thinking through things, be AS CONCISE AS POSSIBLE. You only need to make some data. You don't need to go on at length about the biological details. Only include what's absolutely necessary to generate good figures and data.
Avoid plots that are mostly noise.
Rely on Seaborn for styling and plotting as much as possible.
Don't save any files until you are absolutely read to save the final files and save them in the appropriate place!!
Avoiding opening or "showing" figures.
"""

_DEFAULT_SCENARIO = "Make up whatever you want!"