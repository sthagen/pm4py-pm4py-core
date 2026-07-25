"""Apply tandem-repeat alignment to repetitive variants of ``receipt.xes``.

Run from the ``examples`` directory with:

    python approx_align_tandem_repeats.py

The Petri net is discovered from the complete receipt log with Inductive
Miner and no noise filtering.  To keep the example focused and quick, the
alignment batch contains one trace for every log variant in which the tandem
repeat reduction can actually remove events.
"""

import os

import pm4py
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
from pm4py.algo.conformance.alignments.petri_net.variants.approx_tandem_repeats import (
    reduce_tandem_repeats,
)
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.utils.align_utils import pretty_print_alignments
from pm4py.statistics.variants.log import get as variants_get


def load_log_and_discover_model():
    """Load the complete log and discover its zero-noise accepting net."""
    examples_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(
        examples_dir, "..", "tests", "input_data", "receipt.xes"
    )
    log = xes_importer.apply(log_path)

    # A threshold of 0.0 tells Inductive Miner not to filter infrequent
    # behavior.  The returned markings make the Petri net accepting.
    net, initial_marking, final_marking = pm4py.discover_petri_net_inductive(
        log, noise_threshold=0.0
    )
    return log, net, initial_marking, final_marking


def select_repetitive_variants(log):
    """Return one receipt trace for each compressible log variant."""
    representatives = []
    for traces in variants_get.get_variants(log).values():
        trace = traces[0]
        labels = [event["concept:name"] for event in trace]
        _reduced, _kept_indices, repeats = reduce_tandem_repeats(labels)
        if repeats:
            representatives.append(trace)
    return EventLog(representatives)


def execute_script():
    log, net, initial_marking, final_marking = load_log_and_discover_model()
    repetitive_log = select_repetitive_variants(log)

    results = alignments.apply(
        repetitive_log,
        net,
        initial_marking,
        final_marking,
        variant=alignments.Variants.APPROX_TANDEM_REPEATS,
        parameters={
            "max_align_time": 60,
            "max_align_time_trace": 10,
            "max_expansions": 100000,
            "show_progress_bar": False,
            # Computing best-worst cost is optional and would run an extra
            # alignment solely to normalize fitness.
            "enable_best_worst_cost": False,
        },
    )

    completed = [result for result in results if result is not None]
    valid = sum(result["is_valid"] for result in completed)
    print("Receipt cases used to discover the model:", len(log))
    print("Discovered places / transitions:", len(net.places), len(net.transitions))
    print("Compressible receipt variants aligned:", len(repetitive_log))
    print("Valid complete alignments:", valid, "/", len(completed))
    print(
        "Events removed during all reductions:",
        sum(result["removed_events"] for result in completed),
    )
    print(
        "Model-loop copies restored during expansion:",
        sum(result["model_loop_expansions"] for result in completed),
    )

    if completed:
        # Show the trace on which compression removed the largest number of
        # events.  The printed result is the expanded, executable alignment.
        example = max(completed, key=lambda result: result["removed_events"])
        print("\nMost compressed example:")
        print(
            "Original / reduced length:",
            example["original_trace_length"],
            "/",
            example["reduced_trace_length"],
        )
        print("Cost / upper bound:", example["upper_bound"])
        pretty_print_alignments(example)


if __name__ == "__main__":
    execute_script()
