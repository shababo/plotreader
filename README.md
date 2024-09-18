# Plotreader

Use LLMs to generate and read plots. Combine them into a teacher-student pair to improve performance.

## Problem

Build a tool that can aggregate information from scientific figures into structured data. For example, extract the functional properities of different variants of opsins - both natual and engineered.

## Approach

Design an agent that takes in a data scenario and paper/figure examples and then outputs structured data, the data plotted into a figure, and several quantitative questions about the figure with difficulty rankings.

For now, I'm prototyping independent plot readers and generators.

## Results

### Plot Reading

Input Figure (from [Machine learning-guided channelrhodopsin engineering enables minimally invasive optogenetics
](https://www.nature.com/articles/s41592-019-0583-8)):


![plot](./docs/images/opsin_features_test_w_caption_full_fig.png?)

#### Step 1: Extract experiments from figure.

Prompt:
```Python
prompt = "For each plot in each panel determine the experiment in terms of independent variables (IVs) and dependent variable (DV)."
```

Structured Output:
```
Panel: a
	Plot: Current traces
		independent_variables=['Time', 'ChR variant'] dependent_variables=['Current']
Panel: b
	Plot: Photocurrent strength with different wavelength excitation
		independent_variables=['ChR variant', 'Wavelength', 'Current type (Peak/Steady state)'] dependent_variables=['Photocurrent']
Panel: c
	Plot: Off-kinetics decay time
		independent_variables=['ChR variant'] dependent_variables=['Off-kinetics decay time (τoff)']
	Plot: Current traces for select variants
		independent_variables=['Time', 'ChR variant'] dependent_variables=['Current']
Panel: d
	Plot: Wavelength sensitivity
		independent_variables=['Wavelength', 'ChR variant'] dependent_variables=['Normalized photocurrent']
Panel: e
	Plot: Peak photocurrent vs Intensity
		independent_variables=['Light intensity', 'ChR variant'] dependent_variables=['Peak photocurrent']
	Plot: Steady-state photocurrent vs Intensity
		independent_variables=['Light intensity', 'ChR variant'] dependent_variables=['Steady-state photocurrent']
```

#### Step 2: Extract values for independent and dependent variables from a single plot

Prompts:
```python
prompt = """In Panel {panel_name}, plot number {plot_ind}, what values are taken by the independent variable {ind_var_name}?
If the variable is not quantitative (like an image), only set the name field of IndependentVariable.
Return your answer as structured data.
""".format(
    panel_name = figure.panels[panel_ind].name, 
    plot_ind=plot_ind+1, 
    ind_var_name = iv
)
```

```python
prompt = """In Panel {panel_name}, plot number {plot_ind}, what statistics used to quantify the deependant variable {dep_var_name} like mean or SEM?
If the variable is not quantitative (like an image), only set the name field of DependentVariable.
Return your answer as structured data.
""".format(
    panel_name = figure.panels[panel_ind].name, 
    plot_ind=plot_ind+1, 
    dep_var_name = dv
)
```

Structured Output:

The values for `Wavelength` are not correct. Hoping to resolve this by allowing RAG over full paper.

```
Panel d, Independent Vars:
name='Wavelength' values=[400, 450, 500, 550, 600, 650] unit='nm'
name='ChR variant' values=['ChRger1', 'ChRger2', 'ChRger3', 'ChR_25_9', 'ChR_15_10', 'CsChrimR', 'ChRiff'] unit='None'
```
```
Panel d, Dependent Vars:
name='Normalized photocurrent' statistics=['mean', 's.e.m.'] unit='None'
```

Step 3: Extract dependent variable statistics for each condition

Prompt:
```python
columns = {iv.name: pd.Series() for iv in ind_vars}
columns.update({dv.name: pd.Series()})
df = pd.DataFrame(columns)

prompt = """In Panel {panel_name}, what are the values of the {dep_var_stat} for the dependent variable {dep_var_name}?
If the variable is not quantitative (like an image), only set the name field of IndependentVariable.
Get the value for each condition. To help, here are the values the independent variable takes:
{ind_vars}
IMPORTANT:
    THE EXPECTED VALUES FOR THE INDEPENDENT VARIABLES MAY BE INCORRECT. DO YOUR BEST TO ESTIMATE THE VALUE FOR THE INPUTS FROM THE PLOT.
The column schema is the following: {schema}.
""".format(
    panel_name = figure.panels[panel_ind].name, 
    dep_var_stat = dv.statistics[0],
    dep_var_name = dv.name,
    ind_vars = ind_vars,
    schema = ", ".join(df.columns),
)
```

Structured Output:
```
   Wavelength ChR variant  Normalized photocurrent
0         400     ChRger1                     0.48
1         450     ChRger1                     0.72
2         500     ChRger1                     1.00
3         550     ChRger1                     0.85
4         600     ChRger1                     0.95
5         650     ChRger1                     0.55
6         400     ChRger2                     0.45
7         450     ChRger2                     0.70
8         500     ChRger2                     0.98
9         550     ChRger2                     0.75
10        600     ChRger2                     0.98
11        650     ChRger2                     0.50
12        400     ChRger3                     0.92
13        450     ChRger3                     0.98
14        500     ChRger3                     0.85
15        550     ChRger3                     0.48
16        600     ChRger3                     0.05
17        650     ChRger3                     0.02
18        400    ChR_25_9                     0.65
19        450    ChR_25_9                     0.78
20        500    ChR_25_9                     0.72
21        550    ChR_25_9                     0.20
22        600    ChR_25_9                     0.05
23        650    ChR_25_9                     0.02
24        400   ChR_15_10                     0.70
25        450   ChR_15_10                     0.95
26        500   ChR_15_10                     0.82
27        550   ChR_15_10                     0.18
28        600   ChR_15_10                     0.05
29        650   ChR_15_10                     0.02
30        400    CsChrimR                     0.52
31        450    CsChrimR                     0.50
32        500    CsChrimR                     0.70
33        550    CsChrimR                     0.95
...
38        500      ChRiff                     0.72
39        550      ChRiff                     1.00
40        600      ChRiff                     0.95
41        650      ChRiff                     0.62
```

Plotting extracted data:

Note: colors were not extracted and so not matched. Not a perfect result - some of this may come from incorrectly extracting the `Wavelength` values.

| Extracted | Source |
| -- | -- |
| ![plot](./docs/images/extracted_data_plot.png?) | ![plot](./docs/images/original_plot_for_extraction.png?) |


### Plot Generation

#### Input

Prompt with both text and example figures.
```Python
generator = PlotGenerator(
        storage_dir = "~/dev/plotreader/storage", 
    )

generator.generate(
    data_scenario = (
        "Scientists are desigining new opsins by mutating existing ones. " +
        "They then measure the currents produced when exciting with different wavelengths of light. " + 
        "They plot comparisons of the different mutants and wild-type as function of these wavelengths."
    ),
    examples_dir='~/dev/plotreader/real_figures/opsins'
)
```

Two of the example figures it was given (from [Machine learning-guided channelrhodopsin engineering enables minimally invasive optogenetics](https://www.nature.com/articles/s41592-019-0583-8)).

| Example 1 | Example 2|
| -- | -- |
| ![plot](./docs/images/example_figure.png?) | ![plot](./docs/images/example_figure_2.png?) |



#### Output

##### Generated Figures

| Example 1 | Example 2|
| -- | -- |
| ![plot](./docs/images/opsin_characterization.png?) | ![plot](./docs/images/channelrhodopsin_characterization_realistic.png?) |

##### Generated Questions (with Output Figure Example 1)
The questions were saved into a `.json` file 
```JSON
[
  {
    "difficulty": "Easy",
    "question": "Which opsin variant shows the highest peak photocurrent at the higher light intensity (0.8 mW mm^-2)?",
    "answer": "ChRger1 shows the highest peak photocurrent at the higher light intensity, with a value of approximately 1500 pA."
  },
  {
    "difficulty": "Medium",
    "question": "Comparing ChR2 and ChRger3, what is the approximate percentage increase in peak photocurrent at the lower light intensity (8 \u00d7 10^-3 mW mm^-2)?",
    "answer": "At the lower light intensity, ChR2 has a peak photocurrent of about 100 pA, while ChRger3 has a peak photocurrent of about 600 pA. The percentage increase is approximately (600 - 100) / 100 * 100 = 500%. ChRger3 shows a 500% increase in peak photocurrent compared to ChR2 at the lower light intensity."
  },
  {
    "difficulty": "Hard",
    "question": "Based on the spectral sensitivity plot, at which wavelength does the difference in normalized photocurrent between ChRger3 and ChR2 appear to be the greatest, and what is the approximate magnitude of this difference?",
    "answer": "The difference in normalized photocurrent between ChRger3 and ChR2 appears to be greatest at around 480-490 nm. At this point, ChRger3 has a normalized photocurrent of about 0.75, while ChR2 has a normalized photocurrent of about 0.55. The magnitude of the difference is approximately 0.75 - 0.55 = 0.2, or a 20% difference in normalized photocurrent."
  }
]
```

##### Generated Data (with Output Figure Example 1)
Three `.csv` files were generated that contain the data used to create the figure.

Light intensity response:
|Opsin             |Light Intensity (mW mm^-2)|Peak Photocurrent (pA)|
|------------------|--------------------------|----------------------|
|ChR2              |0.008                     |100                   |
|ChR2              |0.8                       |400                   |
|CoChR             |0.008                     |200                   |
|CoChR             |0.8                       |900                   |
|ChRger1           |0.008                     |850                   |
|ChRger1           |0.8                       |1500                  |
|ChRger2           |0.008                     |600                   |
|ChRger2           |0.8                       |1400                  |
|ChRger3           |0.008                     |600                   |
|ChRger3           |0.8                       |1300                  |



Kinetic estimates:
|Opsin             |τoff (ms)            |
|------------------|---------------------|
|ChR2              |30                   |
|CheRiff           |40                   |
|C1C2              |60                   |
|ChRger1           |25                   |
|ChRger2           |35                   |
|ChRger3           |45                   |


Spectral Senitivity:
|Wavelength (nm)   |Opsin                |Normalized Photocurrent|
|------------------|---------------------|-----------------------|
|400               |ChR2                 |0.036150690739091766   |
|405               |ChR2                 |0.05259894465789624    |
|410               |ChR2                 |0.07443440578013699    |
|415               |ChR2                 |0.1024487550337355     |
|420               |ChR2                 |0.13714371482751292    |
|425               |ChR2                 |0.17855885704709237    |
|430               |ChR2                 |0.22611175977895312    |
|435               |ChR2                 |0.27848458915645535    |
|440               |ChR2                 |0.3335918628419484     |
|445               |ChR2                 |0.38865655282174394    |
|450               |ChR2                 |0.4404055716042445     |
|455               |ChR2                 |0.48537329642152754    |
|460               |ChR2                 |0.520277707898721      |
|465               |ChR2                 |0.542413914209154      |
|470               |ChR2                 |0.55                   |
|475               |ChR2                 |0.542413914209154      |
|480               |ChR2                 |0.520277707898721      |
|485               |ChR2                 |0.48537329642152754    |
|490               |ChR2                 |0.4404055716042445     |
|495               |ChR2                 |0.38865655282174394    |
|500               |ChR2                 |0.3335918628419484     |
|505               |ChR2                 |0.27848458915645535    |
|510               |ChR2                 |0.22611175977895312    |
|515               |ChR2                 |0.17855885704709237    |
|520               |ChR2                 |0.13714371482751292    |
|525               |ChR2                 |0.1024487550337355     |
|530               |ChR2                 |0.07443440578013699    |
|535               |ChR2                 |0.05259894465789624    |
|540               |ChR2                 |0.036150690739091766   |
|545               |ChR2                 |0.024165313492874083   |
|550               |ChR2                 |0.01571102543150271    |
|555               |ChR2                 |0.009934657380879702   |
|560               |ChR2                 |0.006109948096033269   |
|565               |ChR2                 |0.003654756205507769   |
|570               |ChR2                 |0.002126256076710044   |
|575               |ChR2                 |0.001203120115000587   |
|580               |ChR2                 |0.0006621229971555117  |
|585               |ChR2                 |0.0003544089013127345  |
|590               |ChR2                 |0.00018450444534638154 |
|595               |ChR2                 |9.342117210877588e-05  |
|600               |ChR2                 |4.6006590976350145e-05 |
|400               |CoChR                |0.03668482568419145    |
|405               |CoChR                |0.05033444988644888    |
|410               |CoChR                |0.06766764161830635    |
|415               |CoChR                |0.08913198979252396    |
|420               |CoChR                |0.11503314949690453    |
|425               |CoChR                |0.1454619035230741     |
|430               |CoChR                |0.1802238942989105     |
|435               |CoChR                |0.2187823688501346     |
|440               |CoChR                |0.26022506051035105    |
|445               |CoChR                |0.3032653298563167     |
|450               |CoChR                |0.34628466210259884    |
|455               |CoChR                |0.3874187144416247     |
|460               |CoChR                |0.4246829082841562     |
|465               |CoChR                |0.4561270384142726     |
|470               |CoChR                |0.48000272064273886    |
|475               |CoChR                |0.4949239016893669     |
|480               |CoChR                |0.5                    |
|485               |CoChR                |0.4949239016893669     |
|490               |CoChR                |0.48000272064273886    |
|495               |CoChR                |0.4561270384142726     |
|500               |CoChR                |0.4246829082841562     |
|505               |CoChR                |0.3874187144416247     |
|510               |CoChR                |0.34628466210259884    |
|515               |CoChR                |0.3032653298563167     |
|520               |CoChR                |0.26022506051035105    |
|525               |CoChR                |0.2187823688501346     |
|530               |CoChR                |0.1802238942989105     |
|535               |CoChR                |0.1454619035230741     |
|540               |CoChR                |0.11503314949690453    |
|545               |CoChR                |0.08913198979252396    |
|550               |CoChR                |0.06766764161830635    |
|555               |CoChR                |0.05033444988644888    |
|560               |CoChR                |0.03668482568419145    |
|565               |CoChR                |0.02619657053491279    |
|570               |CoChR                |0.018329020976689005   |
|575               |CoChR                |0.012565244492637209   |
|580               |CoChR                |0.008439942074394954   |
|585               |CoChR                |0.005554498269121153   |
|590               |CoChR                |0.0035816822354596085  |
|595               |CoChR                |0.0022629039333833595  |
|600               |CoChR                |0.0014008190174242421  |
|400               |ChRger3              |0.10150146242745953    |
|405               |ChRger3              |0.1293162179203146     |
|410               |ChRger3              |0.1621988751224155     |
|415               |ChRger3              |0.2002888764197575     |
|420               |ChRger3              |0.2434893505187623     |
|425               |ChRger3              |0.2914185956342731     |
|430               |ChRger3              |0.3433750213287107     |
|435               |ChRger3              |0.3983219932765089     |
|440               |ChRger3              |0.45489799478447507    |
|445               |ChRger3              |0.5114555633927611     |
|450               |ChRger3              |0.5661297014917555     |
|455               |ChRger3              |0.6169331717989985     |
|460               |ChRger3              |0.6618726769384466     |
|465               |ChRger3              |0.6990768692696456     |
|470               |ChRger3              |0.7269249258572581     |
|475               |ChRger3              |0.7441634536951827     |
|480               |ChRger3              |0.75                   |
|485               |ChRger3              |0.7441634536951827     |
|490               |ChRger3              |0.7269249258572581     |
|495               |ChRger3              |0.6990768692696456     |
|500               |ChRger3              |0.6618726769384466     |
|505               |ChRger3              |0.6169331717989985     |
|510               |ChRger3              |0.5661297014917555     |
|515               |ChRger3              |0.5114555633927611     |
|520               |ChRger3              |0.45489799478447507    |
|525               |ChRger3              |0.3983219932765089     |
|530               |ChRger3              |0.3433750213287107     |
|535               |ChRger3              |0.2914185956342731     |
|540               |ChRger3              |0.2434893505187623     |
|545               |ChRger3              |0.2002888764197575     |
|550               |ChRger3              |0.1621988751224155     |
|555               |ChRger3              |0.1293162179203146     |
|560               |ChRger3              |0.10150146242745953    |
|565               |ChRger3              |0.07843425096675109    |
|570               |ChRger3              |0.05966963153867076    |
|575               |ChRger3              |0.044690489071489564   |
|580               |ChRger3              |0.032952700217555565   |
|585               |ChRger3              |0.023921095021617825   |
|590               |ChRger3              |0.017095635662709257   |
|595               |ChRger3              |0.012028281956512912   |
|600               |ChRger3              |0.008331747403681729   |

