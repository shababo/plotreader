from plotreader.generator import PlotGenerator


if __name__ == "__main__":

    generator = PlotGenerator(
        vector_store_path = "/Users/loyalshababo/dev/plotreader/sandbox/storage/matplotlib_galleries",
           
    )
    generator.run(
        output_dir="/Users/loyalshababo/dev/plotreader/sandbox/storage/plotgen_output",
        # data_scenario = (
        #     "Scientists are desigining new opsins by mutating existing ones. " +
        #     "They then measure the currents produced when exciting with different wavelengths of light. " + 
        #     "They plot comparisons of the different mutants and wild-type as function of these wavelengths."
        # ) 
        data_scenario = "Choose a complicated or interesting plot other than a line graph or bar plot. Make it look like a modern paper that explore high dimensional and complex data. Also, make it publication level pretty."
    )