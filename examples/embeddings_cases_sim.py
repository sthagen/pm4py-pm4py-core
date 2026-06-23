"""
Case-level transformer similarity example.

This example uses CASES_TRANSFORMERS through keep_top_k_per_similarity. Each
case is converted to a sentence and embedded with a sentence-transformers
model. With the default activity perspective, a trace such as:

    register, check ticket, decide

becomes a sentence similar to:

    "register check ticket decide"

The query text, for example "paid cases", is embedded with the same model.
PM4Py then keeps the cases whose trace embeddings have the highest cosine
similarity to the query embedding.
"""

import importlib.util

import pandas
import pm4py
from pm4py.algo.transformation.trace_encodings import algorithm as trace_encodings
from pm4py.util import constants


def execute_script():
    # CASES_TRANSFORMERS depends on sentence-transformers. The example skips
    # cleanly when the optional dependency is not installed.
    if not importlib.util.find_spec("sentence_transformers"):
        print("sentence-transformers is not installed; skipping case embeddings")
        return

    log: pandas.DataFrame = pm4py.read_xes("../tests/input_data/running-example.xes")

    # Use activity names as the words in each case sentence. The result keeps
    # the two cases whose learned sentence embeddings are closest to "paid
    # cases". This is semantic filtering, not exact string matching.
    log_paid = trace_encodings.keep_top_k_per_similarity(
        log,
        "paid cases",
        2,
        parameters={constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY: "concept:name"},
    )
    print(log_paid)

    # The same case embeddings can be compared with a different query. Here the
    # retained cases are those most similar to "rejected cases".
    log_rejected = trace_encodings.keep_top_k_per_similarity(
        log,
        "rejected cases",
        2,
        parameters={constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY: "concept:name"},
    )
    print(log_rejected)


if __name__ == "__main__":
    execute_script()
