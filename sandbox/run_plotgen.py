from plotreader.generator import PlotGenerator


if __name__ == "__main__":

    generator = PlotGenerator(
        storage_dir = "/Users/loyalshababo/dev/plotreader/storage", 
    )

    generator.generate(
        data_scenario = (
            "Scientists are desigining many, many new opsins by mutating existing ones. " +
            "They then measure different functional properties of the opsin produced when exciting with different wavelengths and or intensities of light. " + 
            "They plot comparisons of the different mutants and wild-types as function of these wavelengths."
            "Create plots similar to the exmaple figures in terms of style, amount of information, and types information."
            "When possible, use types of plots where statistics other than the mean are available (violin, box and whisker, errobar, etc.)."
        ),
        examples_dir='/Users/loyalshababo/dev/plotreader/real_figures/opsins',
        # data_scenario = "Please reference the examples figures provided in the exmaples tool."
        # data_scenario = "Choose a complicated or interesting plot other than a line graph or bar plot, but it doesn't have to hypercomplex. Make it look like a modern paper that explores high dimensional and complex data. Also, make it publication level pretty."
    )