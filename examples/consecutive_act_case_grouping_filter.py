import pm4py
from pm4py.algo.filtering.pandas.consecutive_act_case_grouping import consecutive_act_case_grouping_filter
import pandas


def execute_script():
    dataframe: pandas.DataFrame = pm4py.read_xes("../tests/input_data/receipt.xes")
    print(dataframe)
    filtered_dataframe: pandas.DataFrame = consecutive_act_case_grouping_filter.apply(dataframe)
    print(filtered_dataframe)


if __name__ == "__main__":
    execute_script()
