"""
BERT-style trace encoding example.

This method converts a trace to a sentence and embeds that sentence with a
sentence-transformers model. From an event-log point of view, a case such as:

    A, B, C

is converted to a textual sentence:

    "A B C"

The sentence-transformer maps the whole sentence to a dense vector. This can
capture information beyond raw counts when a suitable language/sequence model
is available. In process-mining settings, the "words" are process tokens
derived from event attributes, not natural-language words.

The model name can also be a local model path. In offline environments, the
model must already be available locally or in the sentence-transformers cache.
"""

import importlib.util
import os

import pandas
import pm4py
from pm4py.algo.transformation.trace_encodings import algorithm as trace_encodings


def execute_script():
    # BERT-style encoding delegates to sentence-transformers. This dependency
    # is optional and may also need a locally available model checkpoint.
    if not importlib.util.find_spec("sentence_transformers"):
        print("sentence-transformers is not installed; skipping BERT encoding")
        return

    # Load and normalize the small XES log used in PM4Py tests.
    log: pandas.DataFrame = pm4py.read_xes(
        os.path.join("..", "tests", "input_data", "running-example.xes")
    )
    log = pm4py.format_dataframe(log)

    # event_attributes controls how process events are rendered as text tokens.
    # With ["concept:name"], each trace sentence is simply its activity
    # sequence. Additional event or trace attributes can be added when the
    # embedding should include resource, cost, or case-level context.
    #
    # bert_model is passed to sentence-transformers. Use a cached model name or
    # a local path when running without network access.
    data, feature_names = trace_encodings.apply(
        log,
        variant=trace_encodings.Variants.BERT,
        parameters={
            "event_attributes": ["concept:name"],
            "bert_model": "bert-base-nli-mean-tokens",
        },
    )

    print("BERT-style trace embeddings")
    # Each row corresponds to one trace/case in the event log.
    print("  rows:", len(data))
    # Each column is one dense embedding dimension returned by the model.
    print("  dimensions:", len(feature_names))
    if len(data):
        # Values are dense floating-point coordinates. Their meaning depends on
        # the selected transformer model, not on explicit process feature names.
        print("  first row:", data[0][:5])


if __name__ == "__main__":
    execute_script()
