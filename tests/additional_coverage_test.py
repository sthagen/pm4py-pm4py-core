import os
import random
import importlib.util
import unittest

import pandas as pd

import pm4py
from pm4py.algo.conformance.alignments.process_tree import algorithm as pt_alignments
from pm4py.algo.simulation.playout.declare import algorithm as declare_playout
from pm4py.algo.simulation.playout.declare.variants import classic as declare_classic
from pm4py.objects.bpmn.layout import layouter as bpmn_layouter
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.obj import Event, EventLog, Trace
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import petri_utils
from pm4py.visualization.ocel.ocpn import visualizer as ocpn_visualizer


class AdditionalCoverageTest(unittest.TestCase):
    """Regression tests for substantial public variants missing from CI."""

    @staticmethod
    def _input_path(*parts):
        return os.path.join(os.path.dirname(__file__), "input_data", *parts)

    @staticmethod
    def _event_log(*variants):
        log = EventLog()
        for index, activities in enumerate(variants):
            trace = Trace(attributes={"concept:name": str(index)})
            for activity in activities:
                trace.append(Event({"concept:name": activity}))
            log.append(trace)
        return log

    def test_brachmann_ocpn_layout(self):
        ocel = pm4py.read_ocel(
            self._input_path("ocel", "example_log.jsonocel")
        )
        ocpn = pm4py.discover_oc_petri_net(ocel)

        graph = ocpn_visualizer.apply(
            ocpn,
            variant=ocpn_visualizer.Variants.BRACHMANN,
            parameters={"format": "svg", "enable_graph_title": True},
        )

        self.assertEqual(graph.format, "svg")
        self.assertIn("Create Order", graph.source)
        self.assertIn("Object-Centric Petri Net", graph.source)

    def test_workflow_net_to_powl(self):
        net, initial_marking, final_marking = pm4py.read_pnml(
            self._input_path("running-example.pnml")
        )

        powl = pm4py.convert_to_powl(net, initial_marking, final_marking)

        self.assertIn("register request", str(powl))
        self.assertGreater(len(powl.children), 1)

    @unittest.skipUnless(
        importlib.util.find_spec("pulp"), "pulp is not installed"
    )
    def test_process_tree_alignment_variants(self):
        scenarios = (
            ("->( 'A', 'B', 'C' )", ("A", "B", "C")),
            ("X( 'A', 'B' )", ("A",)),
            ("+( 'A', 'B' )", ("A", "B")),
            ("*( 'A', 'B' )", ("A", "B", "A")),
        )
        for tree_string, activities in scenarios:
            approximated = pt_alignments.apply(
                self._event_log(activities),
                pm4py.parse_process_tree(tree_string),
                variant=pt_alignments.Variants.APPROXIMATED_ORIGINAL,
                parameters={"show_progress_bar": False},
            )
            self.assertEqual(1, len(approximated))
            self.assertEqual(0, approximated[0]["cost"])

        tree = pm4py.parse_process_tree(
            "->( 'A', X( 'B', 'C' ), +( 'D', 'E' ), *( 'F', 'G' ) )"
        )
        log = self._event_log(
            ("A", "B", "D", "E", "F"),
            ("A", "C", "E", "D", "F", "G", "F"),
            ("A", "B", "D", "F"),
        )
        milp = pt_alignments.apply(
            log,
            tree,
            variant=pt_alignments.Variants.MILP,
            parameters={"show_progress_bar": False},
        )

        self.assertEqual(len(log), len(milp))
        self.assertTrue(all(result["cost"] >= 0 for result in milp))

    def test_declare_playout_automata(self):
        unary_templates = ("existence", "absence", "exactly_one", "init")
        binary_templates = (
            "responded_existence",
            "coexistence",
            "response",
            "precedence",
            "succession",
            "altresponse",
            "altprecedence",
            "altsuccession",
            "chainresponse",
            "chainprecedence",
            "chainsuccession",
            "noncoexistence",
            "nonsuccession",
            "nonchainsuccession",
        )
        model = {template: {"A": {}} for template in unary_templates}
        model.update({template: {("A", "B"): {}} for template in binary_templates})
        model["unknown"] = {("A", "B"): {}}

        playout = declare_classic.DeclarePlayout(
            model, parameters={"n_traces": 2, "min_length": 2, "max_length": 2}
        )
        for activity in ("A", "B"):
            state = playout._new_constraints_state()
            next_state, violated = playout._try_event(activity, state)
            self.assertEqual(set(state), set(next_state))
            self.assertIsInstance(violated, bool)

        random.seed(7)
        generated = declare_playout.apply(
            {"response": {("A", "B"): {}}},
            parameters={"n_traces": 3, "min_length": 3, "max_length": 3},
        )
        self.assertEqual(3, len(generated))
        self.assertTrue(all(len(trace) == 3 for trace in generated))

    def test_graphviz_bpmn_layout(self):
        bpmn = pm4py.read_bpmn(self._input_path("running-example.bpmn"))

        laid_out = bpmn_layouter.apply(
            bpmn,
            variant=bpmn_layouter.Variants.GRAPHVIZ,
            parameters={"screen_size_x": 800, "screen_size_y": 600},
        )

        layout = laid_out.get_layout()
        self.assertTrue(all(layout.get(node).get_width() > 0 for node in laid_out.get_nodes()))
        self.assertTrue(any(flow.get_waypoints() for flow in laid_out.get_flows()))

    def test_iterparse_20_file_and_string(self):
        path = self._input_path("running-example.xes")
        log = xes_importer.apply(
            path,
            variant=xes_importer.Variants.ITERPARSE_20,
            parameters={"show_progress_bar": False, "timestamp_sort": True},
        )
        with open(path, "rb") as stream:
            serialized = stream.read()
        deserialized = xes_importer.deserialize(
            serialized,
            variant=xes_importer.Variants.ITERPARSE_20,
            parameters={"show_progress_bar": False, "max_traces": 2},
        )

        self.assertEqual(6, len(log))
        self.assertEqual(2, len(deserialized))
        self.assertIn("concept:name", log[0][0])

    @unittest.skipUnless(
        importlib.util.find_spec("sklearn"), "scikit-learn is not installed"
    )
    def test_decision_mining_table_and_classifier(self):
        from pm4py.algo.decision_mining import algorithm as decision_mining

        net = PetriNet("choice")
        p0, p1, p2 = (PetriNet.Place(name) for name in ("p0", "choice", "p2"))
        t_a = PetriNet.Transition("t_a", "A")
        t_b = PetriNet.Transition("t_b", "B")
        t_c = PetriNet.Transition("t_c", "C")
        net.places.update((p0, p1, p2))
        net.transitions.update((t_a, t_b, t_c))
        for source, target in (
            (p0, t_a), (t_a, p1), (p1, t_b), (p1, t_c),
            (t_b, p2), (t_c, p2),
        ):
            petri_utils.add_arc_from_to(source, target, net)
        initial_marking, final_marking = Marking(), Marking()
        initial_marking[p0] = 1
        final_marking[p2] = 1

        rows = []
        for case_id, choice, amount, group in (
            ("1", "B", 1.0, "low"), ("2", "B", 2.0, "low"),
            ("3", "C", 9.0, "high"), ("4", "C", 10.0, "high"),
        ):
            rows.extend((
                {"case:concept:name": case_id, "concept:name": "A", "amount": amount, "group": group},
                {"case:concept:name": case_id, "concept:name": choice, "amount": amount, "group": group},
            ))
        log = pd.DataFrame(rows)

        table, points = decision_mining.get_decisions_table(
            log,
            net,
            initial_marking,
            final_marking,
            attributes=["amount", "group"],
            pre_decision_points=["choice"],
        )
        features, target, classes = decision_mining.apply(
            log,
            net,
            initial_marking,
            final_marking,
            decision_point="choice",
            attributes=["amount", "group"],
        )
        self.assertEqual({"choice"}, set(points))
        self.assertEqual(4, len(table["choice"]))
        self.assertEqual(4, len(features))
        self.assertEqual(4, len(target))
        self.assertEqual({"B", "C"}, set(classes))
        self.assertIn("amount", features.columns)
        self.assertTrue(any(column.startswith("group_") for column in features.columns))


if __name__ == "__main__":
    unittest.main()
