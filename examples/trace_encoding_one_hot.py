"""
One-hot trace encoding example.

This encoding turns each trace into a sparse vocabulary vector. From an
event-log point of view, every case is first converted to a list of textual
tokens. With the default activity-only perspective, a trace such as:

    A, B, C, B

is seen as the token list:

    ["A", "B", "C", "B"]

The one-hot vector only records whether a token appears at least once in the
trace. If the log vocabulary is ["A", "B", "C", "D"], the trace above is
encoded as [1, 1, 1, 0]. The second occurrence of B does not increase the B
column because this method models presence/absence, not frequency.

When several event attributes are selected, each event becomes a richer token.
For example, an event with concept:name="A" and org:resource="Mary" becomes a
token such as "concept:name=A|org:resource=Mary". Trace attributes are added
as case-context tokens before the event sequence.
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
        # Values are 0/1 for one-hot: 1 means the token appears in the trace.
        print("  first row:", data[0][:5])


def execute_script():
    # ONE_HOT is implemented through scikit-learn's CountVectorizer with
    # binary=True, so the example can only run when scikit-learn is available.
    if not importlib.util.find_spec("sklearn"):
        print("scikit-learn is not installed; skipping one-hot encoding")
        return

    # The running example is a small XES event log shipped with the tests.
    # format_dataframe normalizes the dataframe columns for PM4Py log handling.
    log: pandas.DataFrame = pm4py.read_xes(
        os.path.join("..", "tests", "input_data", "running-example.xes")
    )
    log = pm4py.format_dataframe(log)

    # Activity-only perspective:
    # the vocabulary contains activity labels such as "register request" or
    # "check ticket". A trace receives 1 in a column if that activity appears.
    data, feature_names = trace_encodings.apply(
        log,
        variant=trace_encodings.Variants.ONE_HOT,
        parameters={"event_attributes": ["concept:name"]},
    )
    _print_result("one-hot, control-flow only", data, feature_names)

    # Context-enriched perspective:
    # each event token combines activity, resource, and cost; the creator case
    # attribute is also added as a trace-level context token. This produces more
    # specific columns than the activity-only encoding.
    data, feature_names = trace_encodings.apply(
        log,
        variant=trace_encodings.Variants.ONE_HOT,
        parameters={
            "event_attributes": ["concept:name", "org:resource", "Costs"],
            "trace_attributes": ["creator"],
        },
    )
    _print_result("one-hot, with event and case context", data, feature_names)


if __name__ == "__main__":
    execute_script()
