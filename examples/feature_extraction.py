"""
Basic trace and event feature extraction example.

This example shows the two older structured encodings that are still exposed
through the trace_encodings API.

TRACE_BASED creates one fixed-size vector per trace. From an event-log point of
view, the whole case is summarized as a single row: activity occurrences,
selected trace attributes, selected event attributes, and optional engineered
features can all become columns.

EVENT_BASED keeps the event sequence shape. Each trace becomes a sequence of
event vectors, padded to the maximum trace length in the log. This is useful
when downstream code needs one vector per event rather than one summary vector
per case.
"""

import os

import pandas
import pm4py
from pm4py.algo.transformation.trace_encodings import algorithm as trace_encodings


def execute_script():
    # Load a compact XES log used throughout PM4Py examples/tests.
    log: pandas.DataFrame = pm4py.read_xes(
        os.path.join("..", "tests", "input_data", "running-example.xes")
    )

    # TRACE_BASED returns a matrix-like object:
    #   rows    -> traces/cases
    #   columns -> extracted trace-level features
    #
    # Example intuition: if a trace contains activity "decide", then a column
    # representing that activity can be set for the whole trace.
    feature_names: list[str]
    data, feature_names = trace_encodings.apply(
        log, variant=trace_encodings.Variants.TRACE_BASED
    )
    print("trace-based data")
    print(data)
    print("trace-based feature names")
    print(feature_names)

    # EVENT_BASED returns a three-dimensional structure:
    #   first dimension  -> traces/cases
    #   second dimension -> event positions inside each trace
    #   third dimension  -> event-level features
    #
    # Example intuition: a trace A, B becomes two event vectors, one for A and
    # one for B. Shorter traces are padded so the tensor has a stable shape.
    data, feature_names = trace_encodings.apply(
        log, variant=trace_encodings.Variants.EVENT_BASED
    )
    print("event-based data")
    print(data)
    print("event-based feature names")
    print(feature_names)


if __name__ == "__main__":
    execute_script()
