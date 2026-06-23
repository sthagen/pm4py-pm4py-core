"""
Count2Vec trace encoding example.

Count2Vec uses the same tokenization idea as one-hot encoding, but stores
frequencies instead of only presence/absence. From an event-log point of view,
a trace such as:

    A, B, C, B

is converted to tokens:

    ["A", "B", "C", "B"]

If the fitted vocabulary is ["A", "B", "C", "D"], the trace is encoded as
[1, 2, 1, 0]. This is useful when repeated behavior matters, for example when
loops or rework should influence the vector more than one-off activities.

With multiple event attributes, a single event can become a combined token
such as "concept:name=A|org:resource=Mary|Costs=100". Trace attributes are
added as case-context tokens and are counted like any other token.
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
    # Each column corresponds to one token found in the fitted vocabulary.
    print("  columns:", len(feature_names))
    print("  first columns:", feature_names[:5])
    if len(data):
        # Values are counts: 2 means the token appears twice in that trace.
        print("  first row:", data[0][:5])


def execute_script():
    # COUNT2VEC is implemented through scikit-learn's CountVectorizer, so the
    # example checks the optional dependency before trying to vectorize.
    if not importlib.util.find_spec("sklearn"):
        print("scikit-learn is not installed; skipping count2vec encoding")
        return

    # Load and normalize the small XES log used in PM4Py tests.
    log: pandas.DataFrame = pm4py.read_xes(
        os.path.join("..", "tests", "input_data", "running-example.xes")
    )
    log = pm4py.format_dataframe(log)

    # Activity-only perspective:
    # every activity label becomes a vocabulary column; the value is the number
    # of times that activity occurs in the trace.
    data, feature_names = trace_encodings.apply(
        log,
        variant=trace_encodings.Variants.COUNT2VEC,
        parameters={"event_attributes": ["concept:name"]},
    )
    _print_result("count2vec, control-flow only", data, feature_names)

    # Context-enriched perspective:
    # the event token includes activity, resource, and cost, and the case
    # creator is added as a trace token. This allows the frequency vector to
    # distinguish, for instance, A performed by Mary from A performed by John.
    data, feature_names = trace_encodings.apply(
        log,
        variant=trace_encodings.Variants.COUNT2VEC,
        parameters={
            "event_attributes": ["concept:name", "org:resource", "Costs"],
            "trace_attributes": ["creator"],
        },
    )
    _print_result("count2vec, with event and case context", data, feature_names)


if __name__ == "__main__":
    execute_script()
