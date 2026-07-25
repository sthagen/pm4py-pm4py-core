"""Generate the PNML/XES examples and validate their behavior end to end."""

import random
import sys
from pathlib import Path

# When this file is executed directly, Python adds this data directory (rather
# than the repository root) to sys.path. Locate the checkout explicitly so the
# validation always exercises the local PM4Py sources.
REPOSITORY_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pm4py").is_dir() and (parent / "tests").is_dir()
)
if __package__ in (None, ""):
    sys.path.insert(0, str(REPOSITORY_ROOT))

import pm4py
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
from pm4py.algo.simulation.playout.petri_net import algorithm as playout
from pm4py.objects.petri_net.inhibitor_reset.semantics import (
    InhibitorResetSemantics,
)
from pm4py.objects.petri_net.obj import InhibitorNet, ResetInhibitorNet, ResetNet

if __package__:
    from .models import SCENARIOS, Scenario, build_model
else:
    from models import SCENARIOS, Scenario, build_model


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
SEMANTICS = InhibitorResetSemantics()


def _activities(trace):
    return [event["concept:name"] for event in trace]


def _validate_trace(trace, scenario: Scenario):
    labels = scenario.activities
    activities = _activities(trace)
    assert activities[:3] == [
        labels["start"],
        labels["check"],
        labels["plan"],
    ]

    gate_end = next(
        index
        for index, activity in enumerate(activities)
        if activity in {labels["reset"], labels["clean"]}
    )
    gate_segment = activities[3 : gate_end + 1]
    assert set(gate_segment[:-1]) <= {labels["issue"]}
    if gate_segment[-1] == labels["clean"]:
        assert labels["issue"] not in gate_segment
    else:
        assert gate_segment[-1] == labels["reset"]

    assert activities[gate_end + 1] == labels["authorize"]
    join_index = activities.index(labels["join"])
    branch_segment = activities[gate_end + 2 : join_index]
    assert sorted(branch_segment) == sorted(
        [labels["a1"], labels["a2"], labels["b1"], labels["b2"]]
    )
    assert branch_segment.index(labels["a1"]) < branch_segment.index(
        labels["a2"]
    )
    assert branch_segment.index(labels["b1"]) < branch_segment.index(
        labels["b2"]
    )

    assert activities[join_index + 1] == labels["review"]
    assert activities[-1] == labels["close"]
    assert set(activities[join_index + 2 : -1]) <= {labels["revise"]}


def _replay_trace(trace, net, initial_marking, final_marking):
    marking = initial_marking.copy()
    for activity in _activities(trace):
        matches = [
            transition
            for transition in SEMANTICS.enabled_transitions(net, marking)
            if transition.label == activity
        ]
        assert len(matches) == 1
        marking = SEMANTICS.execute(matches[0], net, marking)
    assert marking == final_marking


def generate():
    """Write seven PNML models and their basic-playout logs."""
    LOG_DIR.mkdir(exist_ok=True)
    for index, scenario in enumerate(SCENARIOS):
        net, initial_marking, final_marking = build_model(scenario)
        pm4py.write_pnml(
            net,
            initial_marking,
            final_marking,
            BASE_DIR / f"{scenario.slug}.pnml",
        )

        random.seed(7300 + index)
        log = playout.apply(
            net,
            initial_marking,
            final_marking,
            variant=playout.Variants.BASIC_PLAYOUT,
            parameters={
                "petri_semantics": SEMANTICS,
                "noTraces": 30,
                "maxTraceLength": 40,
                "add_only_if_fm_is_reached": True,
            },
        )
        pm4py.write_xes(log, LOG_DIR / f"{scenario.slug}.xes")


def validate_repository():
    """Validate serialization, behavior, replay, and zero-cost alignments."""
    assert len(SCENARIOS) == 7
    for scenario in SCENARIOS:
        net_path = BASE_DIR / f"{scenario.slug}.pnml"
        log_path = LOG_DIR / f"{scenario.slug}.xes"
        assert net_path.is_file()
        assert log_path.is_file()

        net, initial_marking, final_marking = pm4py.read_pnml(str(net_path))
        log = pm4py.read_xes(
            str(log_path), return_legacy_log_object=True
        )
        assert isinstance(net, ResetInhibitorNet)
        assert len([t for t in net.transitions if t.label is not None]) >= 12
        assert any(isinstance(arc, ResetNet.ResetArc) for arc in net.arcs)
        assert any(
            isinstance(arc, InhibitorNet.InhibitorArc) for arc in net.arcs
        )
        assert len(log) == 30

        reset_was_exercised = False
        inhibitor_route_was_exercised = False
        for trace in log:
            _validate_trace(trace, scenario)
            _replay_trace(trace, net, initial_marking, final_marking)
            activities = _activities(trace)
            if (
                scenario.activities["issue"] in activities
                and scenario.activities["reset"] in activities
            ):
                reset_was_exercised = True
            if scenario.activities["clean"] in activities:
                inhibitor_route_was_exercised = True
        assert reset_was_exercised
        assert inhibitor_route_was_exercised

        results = alignments.apply(
            log,
            net,
            initial_marking,
            final_marking,
            variant=alignments.Variants.VERSION_DIJKSTRA_SEMANTICS,
            parameters={
                "petri_semantics": SEMANTICS,
                "enable_best_worst_cost": False,
                "show_progress_bar": False,
            },
        )
        assert len(results) == len(log)
        assert all(result is not None for result in results)
        assert all(result["cost"] == 0 for result in results)
        assert all(
            all(left == right for left, right in result["alignment"])
            for result in results
        )


if __name__ == "__main__":
    generate()
    validate_repository()
    print("Validated 7 reset/inhibitor nets and 210 playout traces.")
