"""
Event-level transformer similarity example.

This example uses EVENTS_TRANSFORMERS through keep_top_k_per_similarity. Each
event is converted to a short sentence and embedded with a sentence-transformers
model. With the default activity perspective, an event such as:

    {"concept:name": "pay compensation"}

becomes the sentence:

    "pay compensation"

The query text is embedded with the same model, and PM4Py keeps the events
whose embeddings are closest to the query embedding. With keep_cases=True, it
keeps the full cases that contain those top events.
"""

import importlib.util

import pandas
import pm4py
from pm4py.algo.transformation.trace_encodings import algorithm as trace_encodings


def execute_script():
    # EVENTS_TRANSFORMERS depends on sentence-transformers. The example skips
    # cleanly when the optional dependency is not installed.
    if not importlib.util.find_spec("sentence_transformers"):
        print("sentence-transformers is not installed; skipping event embeddings")
        return

    log: pandas.DataFrame = pm4py.read_xes("../tests/input_data/running-example.xes")
    log = pm4py.format_dataframe(log)

    # Event filtering mode:
    # keep only the top three individual events whose embeddings are closest to
    # the text query "pay compensation". The output dataframe can contain only a
    # subset of events from a case.
    filt_log_1 = trace_encodings.keep_top_k_per_similarity(
        log,
        "pay compensation",
        k=3,
        variant=trace_encodings.Variants.EVENTS_TRANSFORMERS,
    )
    print(filt_log_1)

    # Case filtering mode:
    # first find the top three matching events, then keep the complete cases
    # containing those events. This is useful when the event match is a signal
    # for selecting whole traces.
    filt_log_2 = trace_encodings.keep_top_k_per_similarity(
        log,
        "pay compensation",
        k=3,
        variant=trace_encodings.Variants.EVENTS_TRANSFORMERS,
        parameters={"keep_cases": True},
    )
    print(filt_log_2)


if __name__ == "__main__":
    execute_script()
