"""
Word2Vec trace encoding example.

Word2Vec is an embedding method: it learns dense vectors for individual event
tokens by looking at the neighboring tokens around them in the log.

From an event-log point of view, each trace is treated like a sentence:

    A, B, C

becomes:

    ["A", "B", "C"]

Word2Vec learns one vector for A, one for B, and one for C. The trace vector is
then computed by aggregating the event-token vectors in the trace. The default
aggregation is the mean, so the trace above is represented by the average of
the A, B, and C vectors.

This method is useful when traces sharing similar local contexts should end up
with similar dense vectors, even if their raw token columns are not identical.
"""

import importlib.util
import os

import pandas
import pm4py
from pm4py.algo.transformation.trace_encodings import algorithm as trace_encodings


def execute_script():
    # WORD2VEC delegates the actual model training to gensim. It is optional
    # because gensim is a heavier dependency than the core PM4Py stack.
    if not importlib.util.find_spec("gensim"):
        print("gensim is not installed; skipping Word2Vec encoding")
        return

    # Load and normalize the small XES log used in PM4Py tests.
    log: pandas.DataFrame = pm4py.read_xes(
        os.path.join("..", "tests", "input_data", "running-example.xes")
    )
    log = pm4py.format_dataframe(log)

    # This example trains a small Word2Vec model directly on the example log.
    # event_attributes selects what becomes a token. With ["concept:name"], the
    # token sequence is just the activity sequence of each case.
    #
    # vector_size=16 keeps the printed example compact. Larger values can carry
    # more information but need more data to train reliably.
    #
    # epochs controls how many passes gensim makes over the trace "sentences".
    # Because Word2Vec training is stochastic, exact numeric values may differ
    # between runs or environments.
    data, feature_names = trace_encodings.apply(
        log,
        variant=trace_encodings.Variants.WORD2VEC,
        parameters={
            "event_attributes": ["concept:name"],
            "vector_size": 16,
            "epochs": 20,
        },
    )

    print("Word2Vec trace embeddings")
    # Each row corresponds to one trace/case in the event log.
    print("  rows:", len(data))
    # Each column is one dimension of the aggregated dense embedding.
    print("  dimensions:", len(feature_names))
    if len(data):
        # Values are dense floating-point coordinates, not interpretable token
        # counts. Similar vectors should indicate similar learned contexts.
        print("  first row:", data[0][:5])


if __name__ == "__main__":
    execute_script()
