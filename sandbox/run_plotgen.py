from plotreader.generator import PlotGenerator


if __name__ == "__main__":

    generator = PlotGenerator(
        storage_dir = "/Users/loyalshababo/dev/plotreader/storage", 
    )

    generator.generate(
        # data_scenario = (
        #     "Scientists are desigining new opsins by mutating existing ones. " +
        #     "They then measure the currents produced when exciting with different wavelengths of light. " + 
        #     "They plot comparisons of the different mutants and wild-type as function of these wavelengths."
        # ),
        examples_dir='/Users/loyalshababo/dev/plotreader/real_figures/opsins',
        data_scenario = "Please reference the examples figures provided in the exmaples tool."
        # data_scenario = "Choose a complicated or interesting plot other than a line graph or bar plot, but it doesn't have to hypercomplex. Make it look like a modern paper that explores high dimensional and complex data. Also, make it publication level pretty."
    )