"""Align all of ``receipt.xes`` by subset selection and edit distance.

Run from the ``examples`` directory with:

    python approx_align_subset_edit_distance.py

The Petri net is discovered from the complete receipt log with Inductive
Miner at noise 0.0.  A small set of frequent variants is aligned through the
model, while the remaining variants are approximated from their nearest
representative.  Unlike the trace-oriented examples, this method efficiently
processes all 1,434 cases in the demonstration.
"""

import os

import pm4py
from pm4py.algo.conformance.alignments.edit_distance import (
    algorithm as edit_distance_alignments,
)
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.petri_net.utils.align_utils import pretty_print_alignments


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


def execute_script():
    log, net, initial_marking, final_marking = load_log_and_discover_model()

    summary = edit_distance_alignments.apply_approximation_with_summary(
        log,
        net,
        initial_marking,
        final_marking,
        parameters={
            # The ten most frequent variants are exact representatives.  Try
            # ``k_medoids`` when coverage of diverse behavior is preferred.
            "selection_method": "frequency",
            "subset_size": 10,
            "max_align_time_trace": 60,
            "max_expansions": 100000,
        },
    )
    results = summary["alignments"]

    print("Receipt cases aligned:", len(results))
    print("Discovered places / transitions:", len(net.places), len(net.transitions))
    print("Valid complete alignments:", sum(result["is_valid"] for result in results))
    print(
        "Cases belonging to exactly aligned representative variants:",
        sum(result["selected_exact"] for result in results),
    )
    print(
        "Approximate log fitness and bounds: "
        f"{summary['log_fitness']:.3f} "
        f"[{summary['fitness_lower_bound']:.3f}, "
        f"{summary['fitness_upper_bound']:.3f}]"
    )
    print("Aggregate deviation counts:", summary["deviation_counts"])

    if results:
        # Prefer a non-representative case so the edit-distance approximation
        # is visible in the printed alignment.
        example = next(
            (result for result in results if not result["selected_exact"]),
            results[0],
        )
        print("\nExample selected exactly:", example["selected_exact"])
        print("Representative model trace:", example["representative_variant"])
        print(
            "Fitness estimate and bounds: "
            f"{example['approximated_fitness']:.3f} "
            f"[{example['fitness_lower_bound']:.3f}, "
            f"{example['fitness_upper_bound']:.3f}]"
        )
        pretty_print_alignments(example)


if __name__ == "__main__":
    execute_script()
