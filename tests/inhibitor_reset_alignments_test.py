import unittest
from pathlib import Path

import pm4py
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
from pm4py.algo.simulation.playout.petri_net import algorithm as playout
from pm4py.objects.log.obj import Event, Trace
from pm4py.objects.petri_net.inhibitor_reset.semantics import (
    InhibitorResetSemantics,
)
from pm4py.objects.petri_net.obj import Marking, PetriNet, ResetInhibitorNet
from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to

from tests.input_data.inh_res_nets.generate_and_validate import (
    validate_repository,
)


class InhibitorResetAlignmentsTest(unittest.TestCase):
    def test_basic_playout_uses_supplied_semantics(self):
        net = ResetInhibitorNet("inhibitor playout")
        source = ResetInhibitorNet.Place("source")
        guard = ResetInhibitorNet.Place("guard")
        sink = ResetInhibitorNet.Place("sink")
        transition = ResetInhibitorNet.Transition("complete", "Complete")
        net.places.update({source, guard, sink})
        net.transitions.add(transition)
        add_arc_from_to(source, transition, net)
        add_arc_from_to(guard, transition, net, type="inhibitor")
        add_arc_from_to(transition, sink, net)

        log = playout.apply(
            net,
            Marking({source: 1}),
            Marking({sink: 1}),
            parameters={
                "petri_semantics": InhibitorResetSemantics(),
                "noTraces": 1,
                "maxTraceLength": 2,
                "add_only_if_fm_is_reached": True,
            },
        )
        self.assertEqual(
            [["Complete"]],
            [[event["concept:name"] for event in trace] for trace in log],
        )

    def test_semantics_dijkstra_supports_classic_nets(self):
        net = PetriNet("classic")
        source = PetriNet.Place("source")
        sink = PetriNet.Place("sink")
        transition = PetriNet.Transition("approve", "Approve")
        net.places.update({source, sink})
        net.transitions.add(transition)
        add_arc_from_to(source, transition, net)
        add_arc_from_to(transition, sink, net)
        initial_marking = Marking({source: 1})
        final_marking = Marking({sink: 1})

        result = alignments.apply(
            Trace([Event({"concept:name": "Approve"})]),
            net,
            initial_marking,
            final_marking,
            variant=alignments.Variants.VERSION_DIJKSTRA_SEMANTICS,
        )
        self.assertEqual(0, result["cost"])
        self.assertEqual([("Approve", "Approve")], result["alignment"])

        deviating = alignments.apply(
            Trace(
                [
                    Event({"concept:name": "Approve"}),
                    Event({"concept:name": "Unexpected"}),
                ]
            ),
            net,
            initial_marking,
            final_marking,
            variant=alignments.Variants.VERSION_DIJKSTRA_SEMANTICS,
        )
        self.assertEqual(10000, deviating["cost"])

    def test_semantics_dijkstra_matches_classic_dijkstra(self):
        input_dir = Path(__file__).resolve().parent / "input_data"
        net, initial_marking, final_marking = pm4py.read_pnml(
            str(input_dir / "running-example.pnml")
        )
        log = pm4py.read_xes(
            str(input_dir / "running-example.xes"),
            return_legacy_log_object=True,
        )
        for trace in log:
            classic = alignments.apply(
                trace,
                net,
                initial_marking,
                final_marking,
                variant=alignments.Variants.VERSION_DIJKSTRA_NO_HEURISTICS,
                parameters={"enable_best_worst_cost": False},
            )
            semantics_aware = alignments.apply(
                trace,
                net,
                initial_marking,
                final_marking,
                variant=alignments.Variants.VERSION_DIJKSTRA_SEMANTICS,
                parameters={"enable_best_worst_cost": False},
            )
            self.assertEqual(classic["cost"], semantics_aware["cost"])

    def test_all_input_logs_replay_and_align(self):
        data_dir = (
            Path(__file__).resolve().parent / "input_data" / "inh_res_nets"
        )
        self.assertTrue(data_dir.is_dir())
        validate_repository()


if __name__ == "__main__":
    unittest.main()
