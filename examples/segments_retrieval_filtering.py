import pm4py
import pandas
from collections import Counter
from pm4py.objects.log.obj import EventLog


def execute_script():
    log: pandas.DataFrame = pm4py.read_xes("../tests/input_data/receipt.xes")

    # gets the frequent trace segments
    traces: Counter = pm4py.get_frequent_trace_segments(log, min_occ=100)

    for t in traces:
        # filter on the given trace segment, to obtain an event log where all the cases contain the trace segment
        print(t)
        filtered_log: EventLog | pandas.DataFrame = pm4py.filter_trace_segments(log, [t])
        print(filtered_log)

        break


if __name__ == "__main__":
    execute_script()
