"""Apply sequential fixed-horizon alignment to ``receipt.xes`` variants.

Run from the ``examples`` directory with:

    python approx_align_fixed_horizon.py

The accepting Petri net is discovered from the complete receipt log using
Inductive Miner at noise 0.0.  Fixed-horizon alignment solves many integer
tail estimates, so this runnable example uses the five most frequent variants.
Increase ``NUMBER_OF_VARIANTS`` when a larger benchmark is desired.
"""

import os

import pm4py
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.utils.align_utils import pretty_print_alignments
from pm4py.statistics.variants.log import get as variants_get


NUMBER_OF_VARIANTS = 5


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
        variant=alignments.Variants.APPROX_FIXED_HORIZON,
        parameters={
            # Search and commit short executable prefixes.  Increasing the
            # horizon usually improves quality at greater computational cost.
            "horizon": 3,
            "min_progress": 1,
            "max_horizon": 6,
            "max_prefix_states": 3000,
            "max_iterations": 100,
            "max_align_time": 60,
            "max_align_time_trace": 10,
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
        "Integer tail problems solved:",
        sum(result["lp_solved"] for result in completed),
    )
    print(
        "Alignments requiring exact-search fallback:",
        sum(result["fallback_used"] for result in completed),
    )

    if completed:
        example = max(completed, key=lambda result: len(result["alignment"]))
        print("\nCommitted horizons:", example["committed_horizons"])
        if example["fallback_reason"] is not None:
            # No supported LP solver is one possible reason.  The variant
            # falls back to direct search rather than returning an invalid path.
            print("Fallback reason:", example["fallback_reason"])
        print("Cost / upper bound:", example["upper_bound"])
        pretty_print_alignments(example)


if __name__ == "__main__":
    execute_script()
