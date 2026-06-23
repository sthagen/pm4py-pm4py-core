"""
N-gram trace encoding example.

N-grams add local ordering information to bag-of-token encodings. From an
event-log point of view, a trace is first tokenized, and then contiguous token
windows are counted.

For a trace:

    A, B, C

activity 1-grams are:

    A, B, C

activity 2-grams are:

    A >> B, B >> C

With ngram_range=(2, 2), the vector contains only directly-following pairs.
With ngram_range=(1, 2), it contains both individual tokens and adjacent
pairs. This is helpful when the difference between "A then B" and "B then A"
matters.
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
    # Each column corresponds to an observed n-gram.
    print("  columns:", len(feature_names))
    print("  first columns:", feature_names[:5])
    if len(data):
        # Values are counts of the corresponding n-gram in the trace.
        print("  first row:", data[0][:5])


def execute_script():
    # N_GRAMS uses the same scikit-learn vectorization utility as COUNT2VEC,
    # but customizes the analyzer so it can count process-sequence windows.
    if not importlib.util.find_spec("sklearn"):
        print("scikit-learn is not installed; skipping n-gram encoding")
        return

    # Load and normalize the small XES log used in PM4Py tests.
    log: pandas.DataFrame = pm4py.read_xes(
        os.path.join("..", "tests", "input_data", "running-example.xes")
    )
    log = pm4py.format_dataframe(log)

    # Directly-follows perspective:
    # ngram_range=(2, 2) means "only pairs". The vocabulary contains columns
    # like "A >> B" whenever A is followed immediately by B in a trace.
    data, feature_names = trace_encodings.apply(
        log,
        variant=trace_encodings.Variants.N_GRAMS,
        parameters={
            "event_attributes": ["concept:name"],
            "ngram_range": (2, 2),
        },
    )
    _print_result("2-grams, control-flow only", data, feature_names)

    # Mixed unigram/bigram perspective:
    # ngram_range=(1, 2) keeps individual event tokens and adjacent pairs. The
    # event token also includes the resource, and the creator is prepended as a
    # trace-context token, so some n-grams connect case context to the first
    # observed event token.
    data, feature_names = trace_encodings.apply(
        log,
        variant=trace_encodings.Variants.N_GRAMS,
        parameters={
            "event_attributes": ["concept:name", "org:resource"],
            "trace_attributes": ["creator"],
            "ngram_range": (1, 2),
        },
    )
    _print_result("1- and 2-grams, with event and case context", data, feature_names)


if __name__ == "__main__":
    execute_script()
