if True:
    # ignore this part in true PowerBI executions
    import pandas as pd
    from pm4py.objects.log.util import dataframe_utils

    dataset = pd.read_csv("C:/running-example.csv")
    dataset = dataframe_utils.convert_timestamp_columns_in_df(dataset)

import pandas as pd

# this part is required because the dataframe provided by PowerBI has strings
dataset["time:timestamp"] = pd.to_datetime(dataset["time:timestamp"])
dataset = dataset.sort_values("time:timestamp")

from pm4py.statistics.traces.pandas import case_statistics
from pm4py.visualization.graphs import visualizer as graphs_visualizer

x_cases, y_cases = case_statistics.get_kde_caseduration(dataset)

graph_cases = graphs_visualizer.apply(x_cases, y_cases, variant=graphs_visualizer.Variants.CASES,
                                      parameters={graphs_visualizer.Variants.CASES.value.Parameters.FORMAT: "png"})

graphs_visualizer.matplotlib_view(graph_cases)
