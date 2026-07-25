"""Stream all cases in ``receipt.xes`` through an IWS approximate aligner.

Run from the ``examples`` directory with:

    python approx_align_iws_streaming.py

The model is discovered from the full log with Inductive Miner at noise 0.0.
The twenty most frequent variants form the finite proxy trie, after which all
1,434 receipt cases are replayed event by event and explicitly completed.
Cases outside the proxy can still be explained using log/model moves.
"""

import os

import pm4py
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.utils.align_utils import pretty_print_alignments
from pm4py.statistics.variants.log import get as variants_get
from pm4py.streaming.algo.conformance.alignments import (
    algorithm as streaming_alignments,
)


PROXY_VARIANTS = 20


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


def frequent_variant_proxy(log, limit):
    """Build a small proxy log containing one trace per frequent variant."""
    groups = sorted(
        variants_get.get_variants(log).values(),
        key=len,
        reverse=True,
    )[:limit]
    return EventLog([traces[0] for traces in groups])


def execute_script():
    log, net, initial_marking, final_marking = load_log_and_discover_model()
    proxy_log = frequent_variant_proxy(log, PROXY_VARIANTS)

    online_aligner = streaming_alignments.apply(
        net,
        initial_marking,
        final_marking,
        variant=streaming_alignments.Variants.APPROX_IWS,
        parameters={
            "proxy_log": proxy_log,
            "look_ahead": 3,
            "decay_time": 8,
            "discount_factor": 0.9,
            "max_states": 20,
            "max_align_time_trace": 10,
            "max_expansions": 100000,
        },
    )

    completed = []
    first_prefix = None
    for trace_index, trace in enumerate(log):
        # A generated identifier avoids relying on a particular trace-level
        # case attribute in the XES file.
        case_id = f"receipt-{trace_index}"
        for event_index, event in enumerate(trace):
            online_aligner.receive(
                {
                    "case:concept:name": case_id,
                    "concept:name": event["concept:name"],
                }
            )
            if trace_index == 0 and event_index == 0:
                first_prefix = online_aligner.get()[case_id]

        # finish() appends the cheapest proxy-model suffix and validates that
        # the result reaches the accepting final marking.
        completed.append(online_aligner.finish(case_id))

    print("Receipt cases streamed:", len(completed))
    print("Receipt events streamed:", sum(len(trace) for trace in log))
    print("Proxy variants:", len(proxy_log))
    print("Discovered places / transitions:", len(net.places), len(net.transitions))
    print("Valid complete alignments:", sum(result["is_valid"] for result in completed))
    print(
        "Mean standard-cost upper bound:",
        sum(result["upper_bound"] for result in completed) / len(completed),
    )

    if first_prefix is not None:
        print("\nPrefix alignment after the first streamed event:")
        print("Active alternatives:", first_prefix["active_states"])
        print("Best-state decay:", first_prefix["decay"])
        pretty_print_alignments(first_prefix)

    if completed:
        # Show the completed case with the largest proxy-alignment cost.
        example = max(completed, key=lambda result: result["standard_cost"])
        print("Highest completed cost / upper bound:", example["upper_bound"])
        pretty_print_alignments(example)


if __name__ == "__main__":
    execute_script()
