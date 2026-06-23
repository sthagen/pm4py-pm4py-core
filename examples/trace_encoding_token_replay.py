"""
Token-replay trace encoding example.

Token replay is a process-model-based encoding. Instead of looking only at the
events in a trace, it replays each trace on a Petri net and stores conformance
diagnostics as numeric features.

In this example the model is:

    A -> B -> C

The event log contains two traces:

    fit:    A, B, C
    skip_b: A, C

The first trace can be replayed without deviations. The second trace skips B,
so token replay has to compensate for missing/remaining tokens. The resulting
vector records whether the trace is fit, its fitness, and token counters.
"""

from pm4py.algo.transformation.trace_encodings import algorithm as trace_encodings
from pm4py.objects.log.obj import Event, EventLog, Trace
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import petri_utils


def _build_log_and_model():
    """Build a tiny event log and a matching A -> B -> C Petri net."""
    # Build the log explicitly so the example is independent of external XES
    # files and the intended deviations are easy to inspect.
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

    # The initial marking puts one token in p0. A perfectly replayed trace
    # consumes and produces tokens until one token reaches p3.
    initial_marking = Marking()
    initial_marking[p0] = 1
    final_marking = Marking()
    final_marking[p3] = 1

    return log, net, initial_marking, final_marking


def execute_script():
    log, net, initial_marking, final_marking = _build_log_and_model()

    # TOKEN_REPLAY returns one row per trace with these columns:
    #   @@token_replay_is_fit
    #   @@token_replay_fitness
    #   @@token_replay_missing_tokens
    #   @@token_replay_consumed_tokens
    #   @@token_replay_remaining_tokens
    #   @@token_replay_produced_tokens
    #
    # Passing an explicit net makes the conformance reference clear. If no net
    # is supplied, the variant can discover one, but that is less didactic for
    # this small example.
    data, feature_names = trace_encodings.apply(
        log,
        variant=trace_encodings.Variants.TOKEN_REPLAY,
        parameters={
            "net": net,
            "initial_marking": initial_marking,
            "final_marking": final_marking,
            "show_progress_bar": False,
        },
    )

    print(feature_names)
    for trace, row in zip(log, data):
        # Compare the "fit" and "skip_b" rows: the skipped-B trace should show
        # lower fitness and/or non-zero token-deviation counters.
        print(trace.attributes["concept:name"], row)


if __name__ == "__main__":
    execute_script()
