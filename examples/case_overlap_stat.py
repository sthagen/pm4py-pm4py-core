import pm4py
import os
from pm4py.statistics.overlap.cases.log import get as case_overlap_get
import pandas


def execute_script():
    log: pandas.DataFrame = pm4py.read_xes(os.path.join("..", "tests", "input_data", "receipt.xes"))
    # calculates the WIP statistics from the event log object.
    # The WIP statistic associates to each case the number of cases open during the lifecycle of the case
    wip: list[int] = case_overlap_get.apply(log)
    print(wip)


if __name__ == "__main__":
    execute_script()
