"""
TF-IDF trace encoding example.

TF-IDF keeps the bag-of-token shape of Count2Vec, but changes the value stored
in each column. The value is high when a token is frequent in the current
trace and relatively rare across other traces.

From an event-log point of view, suppose the fitted vocabulary contains
activities A, B, and C. If activity A appears in almost every case, while C
appears only in a few exceptional cases, then C receives a higher inverse
document-frequency weight. This can make exceptional behavior more visible to
downstream machine-learning algorithms.

The same tokenization rules are used as in the other text-style encodings:
selected event attributes form event tokens, trace attributes form case
context tokens, and ngram_range can include adjacent process fragments.
"""

import importlib.util
import os

import pandas
import pm4py
from pm4py.algo.transformation.trace_encodings import algorithm as trace_encodings


def _print_result(name, data, feature_names):
    """Print a compact preview of a trace encoding matrix."""
    print(name)
    # Each row corresponds to one trace/case in the event log.
    print("  rows:", len(data))
    # Each column corresponds to one token or n-gram in the fitted vocabulary.
    print("  columns:", len(feature_names))
    print("  first columns:", feature_names[:5])
    if len(data):
        # Values are floating-point TF-IDF weights, not raw counts.
        print("  first row:", data[0][:5])


def execute_script():
    # TF_IDF is implemented through scikit-learn's TfidfVectorizer.
    if not importlib.util.find_spec("sklearn"):
        print("scikit-learn is not installed; skipping TF-IDF encoding")
        return

    # Load and normalize the small XES log used in PM4Py tests.
    log: pandas.DataFrame = pm4py.read_xes(
        os.path.join("..", "tests", "input_data", "running-example.xes")
    )
    log = pm4py.format_dataframe(log)

    # Activity-only perspective:
    # each activity is weighted by how characteristic it is for the trace.
    # Common activities still appear in the vector, but they receive less
    # emphasis than tokens that are rarer across the log.
    data, feature_names = trace_encodings.apply(
        log,
        variant=trace_encodings.Variants.TF_IDF,
        parameters={"event_attributes": ["concept:name"]},
    )
    _print_result("TF-IDF, control-flow only", data, feature_names)

    # Context and local-order perspective:
    # adding resource and creator context enriches the token vocabulary, while
    # ngram_range=(1, 2) adds adjacent token pairs. The resulting weights can
    # highlight rare activity-resource combinations or rare short fragments.
    data, feature_names = trace_encodings.apply(
        log,
        variant=trace_encodings.Variants.TF_IDF,
        parameters={
            "event_attributes": ["concept:name", "org:resource"],
            "trace_attributes": ["creator"],
            "ngram_range": (1, 2),
        },
    )
    _print_result("TF-IDF, with event and case context", data, feature_names)


if __name__ == "__main__":
    execute_script()
