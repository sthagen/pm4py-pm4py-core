"""
Doc2Vec trace encoding example.

Doc2Vec is related to Word2Vec, but learns a vector for each whole trace
directly. From an event-log point of view, every case is a document and every
event token is a word in that document:

    case 1: A, B, C
    case 2: A, B, D

Doc2Vec learns one dense vector for "A B C" and another dense vector for
"A B D". Unlike Word2Vec, the trace vector is not calculated by averaging
event vectors after training; the document/trace vector is part of the model.

This method is useful when the whole case should be embedded as one object,
rather than as a simple aggregate of event embeddings.
"""

import importlib.util
import os

import pandas
import pm4py
from pm4py.algo.transformation.trace_encodings import algorithm as trace_encodings


def execute_script():
    # DOC2VEC delegates model training to gensim. The example skips cleanly
    # when gensim is not installed.
    if not importlib.util.find_spec("gensim"):
        print("gensim is not installed; skipping Doc2Vec encoding")
        return

    # Load and normalize the small XES log used in PM4Py tests.
    log: pandas.DataFrame = pm4py.read_xes(
        os.path.join("..", "tests", "input_data", "running-example.xes")
    )
    log = pm4py.format_dataframe(log)

    # This example trains a small Doc2Vec model directly on the example log.
    # event_attributes selects what becomes a word in the trace document.
    #
    # vector_size=16 keeps the printed example compact. Real applications
    # usually need more training data and may use a larger vector size.
    #
    # epochs controls how many training passes gensim performs. Doc2Vec
    # training is stochastic, so the exact coordinates may differ by run.
    data, feature_names = trace_encodings.apply(
        log,
        variant=trace_encodings.Variants.DOC2VEC,
        parameters={
            "event_attributes": ["concept:name"],
            "vector_size": 16,
            "epochs": 20,
        },
    )

    print("Doc2Vec trace embeddings")
    # Each row corresponds to one trace/case in the event log.
    print("  rows:", len(data))
    # Each column is one dimension of the learned trace/document vector.
    print("  dimensions:", len(feature_names))
    if len(data):
        # Values are dense floating-point coordinates. Individual dimensions do
        # not have direct process labels like "activity A count".
        print("  first row:", data[0][:5])


if __name__ == "__main__":
    execute_script()
