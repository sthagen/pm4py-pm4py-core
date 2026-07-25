"""Apply sliding-window top-k alignment to variants of ``receipt.xes``.

Run from the ``examples`` directory with:

    python approx_align_sliding_window.py

The model is learned from the complete log using Inductive Miner with a noise
threshold of 0.0.  One trace from each of the most frequent variants is then
aligned in windows.  This representative batch keeps the example fast while
still exercising PM4Py's log-level alignment interface.
"""

import os

import pm4py
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.utils.align_utils import pretty_print_alignments
from pm4py.statistics.variants.log import get as variants_get


# Increase this value, up to the 116 variants in the log, for a larger batch.
NUMBER_OF_VARIANTS = 12


def load_log_and_discover_model():
    examples_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(
        examples_dir, "..", "tests", "input_data", "receipt.xes"
    )
    log = xes_importer.apply(log_path)
    net, initial_marking, final_marking = pm4py.discover_petri_net_inductive(
        log, noise_threshold=0.0
    )
    return log, net, initial_marking, final_marking


def most_frequent_variant_representatives(log, limit):
    """Select one trace from each of the ``limit`` largest variant groups."""
    groups = sorted(
        variants_get.get_variants(log).values(),
        key=len,
        reverse=True,
    )[:limit]
    return EventLog([traces[0] for traces in groups]), sum(map(len, groups))


def execute_script():
    log, net, initial_marking, final_marking = load_log_and_discover_model()
    alignment_log, covered_cases = most_frequent_variant_representatives(
        log, NUMBER_OF_VARIANTS
    )

    results = alignments.apply(
        alignment_log,
        net,
        initial_marking,
        final_marking,
        variant=alignments.Variants.APPROX_SLIDING_WINDOW,
        parameters={
            # Each fragment consumes at most five observed events.
            "window_size": 5,
            # Keep paths ending in up to three distinct model markings.
            "max_candidates": 3,
            "max_post_model_moves": 3,
            "max_align_time": 60,
            "max_align_time_trace": 10,
            "max_expansions": 100000,
            "show_progress_bar": False,
            "enable_best_worst_cost": False,
        },
    )

    completed = [result for result in results if result is not None]
    valid = sum(result["is_valid"] for result in completed)
    print("Receipt cases used to discover the model:", len(log))
    print("Discovered places / transitions:", len(net.places), len(net.transitions))
    print("Representative variants aligned:", len(alignment_log))
    print("Cases represented by those variants:", covered_cases)
    print("Valid complete alignments:", valid, "/", len(completed))
    print(
        "Alignments requiring exact-search fallback:",
        sum(result["fallback_used"] for result in completed),
    )

    if completed:
        # Display the example split into the greatest number of windows.
        example = max(completed, key=lambda result: result["window_count"])
        print("\nExample window count:", example["window_count"])
        print("Candidates retained per window:", example["retained_candidates"])
        print("Cost / upper bound:", example["upper_bound"])
        pretty_print_alignments(example)


if __name__ == "__main__":
    execute_script()
