"""
Alignment-based trace encoding example.

Alignments are another process-model-based encoding. Each trace is aligned
against a Petri net by finding a least-cost explanation of how the observed log
moves can match the model moves.

In this example the model is:

    A -> B -> C

The event log contains two traces:

    fit:    A, B, C
    skip_b: A, C

The first trace aligns synchronously with the model. The second trace cannot
match the model without a deviation, so the alignment cost increases and the
fitness decreases. The output vector stores these conformance diagnostics.
"""

from pm4py.algo.transformation.trace_encodings import algorithm as trace_encodings
from pm4py.objects.log.obj import Event, EventLog, Trace
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import petri_utils


def _build_log_and_model():
    """Build a tiny event log and a matching A -> B -> C Petri net."""
    # Build the log explicitly so the two cases and their expected behavior are
    # visible without opening an external file.
    log = EventLog()
    for case_id, activities in [("fit", ["A", "B", "C"]), ("skip_b", ["A", "C"])]:
        trace = Trace(attributes={"concept:name": case_id})
        for activity in activities:
            trace.append(Event({"concept:name": activity}))
        log.append(trace)

    # Build a simple sequential Petri net:
    # p0 --A--> p1 --B--> p2 --C--> p3
    net = PetriNet("abc")
    p0 = PetriNet.Place("p0")
    p1 = PetriNet.Place("p1")
    p2 = PetriNet.Place("p2")
    p3 = PetriNet.Place("p3")
    t_a = PetriNet.Transition("A", "A")
    t_b = PetriNet.Transition("B", "B")
    t_c = PetriNet.Transition("C", "C")

    for place in [p0, p1, p2, p3]:
        net.places.add(place)
    for transition in [t_a, t_b, t_c]:
        net.transitions.add(transition)

    petri_utils.add_arc_from_to(p0, t_a, net)
    petri_utils.add_arc_from_to(t_a, p1, net)
    petri_utils.add_arc_from_to(p1, t_b, net)
    petri_utils.add_arc_from_to(t_b, p2, net)
    petri_utils.add_arc_from_to(p2, t_c, net)
    petri_utils.add_arc_from_to(t_c, p3, net)

    # The initial marking puts one token in p0; the final marking expects one
    # token in p3 after replaying A, then B, then C.
    initial_marking = Marking()
    initial_marking[p0] = 1
    final_marking = Marking()
    final_marking[p3] = 1

    return log, net, initial_marking, final_marking


def execute_script():
    log, net, initial_marking, final_marking = _build_log_and_model()

    # ALIGNMENTS returns one row per trace with these columns:
    #   @@alignment_is_fit
    #   @@alignment_fitness
    #   @@alignment_cost
    #   @@alignment_bwc
    #   @@alignment_visited_states
    #   @@alignment_queued_states
    #   @@alignment_traversed_arcs
    #
    # The first columns describe conformance quality. The state/arc counters
    # describe computational effort of the alignment search.
    data, feature_names = trace_encodings.apply(
        log,
        variant=trace_encodings.Variants.ALIGNMENTS,
        parameters={
            "net": net,
            "initial_marking": initial_marking,
            "final_marking": final_marking,
            "show_progress_bar": False,
        },
    )

    print(feature_names)
    for trace, row in zip(log, data):
        # Compare the "fit" and "skip_b" rows: the skipped-B trace should have
        # a non-zero cost and a lower fitness than the perfectly fitting trace.
        print(trace.attributes["concept:name"], row)


if __name__ == "__main__":
    execute_script()
