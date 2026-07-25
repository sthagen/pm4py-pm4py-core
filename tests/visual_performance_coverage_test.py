import importlib.machinery
import os
import sys
import tempfile
import time
import types
import unittest
from collections import Counter
from datetime import datetime, timedelta, timezone
from unittest import mock

import pandas as pd

import pm4py
from pm4py.algo.discovery.performance_spectrum import algorithm as performance_spectrum
from pm4py.algo.filtering.dfg import dfg_filtering
from pm4py.objects.log.obj import Event, EventLog, Trace
from pm4py.objects.ocpn.obj import OCMarking, OCPetriNet
from pm4py.objects.ocpn.variants import to_alternative_format
from pm4py.objects.org.sna.obj import SNA
from pm4py.objects.process_tree.obj import Operator, ProcessTree
from pm4py.objects.process_tree.utils import regex as process_tree_regex
from pm4py.util import timeout
from pm4py.visualization.footprints.variants import comparison_symmetric
from pm4py.visualization.ocel.object_graph import visualizer as object_graph_visualizer
from pm4py.visualization.sna import visualizer as sna_visualizer


class _FakeNetwork:
    def __init__(self, **kwargs):
        self.directed = kwargs["directed"]
        self.nodes = []
        self.edges = []

    def barnes_hut(self):
        return None

    def add_node(self, node_id, *args, **kwargs):
        if not any(node["id"] == node_id for node in self.nodes):
            self.nodes.append({"id": node_id, "title": kwargs["title"]})

    def add_edge(self, source, target, **kwargs):
        self.edges.append((source, target, kwargs))

    def get_adj_list(self):
        result = {node["id"]: [] for node in self.nodes}
        for source, target, _ in self.edges:
            result[source].append(target)
            if not self.directed:
                result[target].append(source)
        return result

    def show_buttons(self, **kwargs):
        return None

    def generate_html(self):
        return "<html>network</html>"

    def write_html(self, path):
        with open(path, "w") as file:
            file.write(self.generate_html())


class VisualPerformanceCoverageTest(unittest.TestCase):
    @staticmethod
    def _input_path(*parts):
        return os.path.join(os.path.dirname(__file__), "input_data", *parts)

    @staticmethod
    def _log_and_dataframe():
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        log = EventLog()
        rows = []
        for case, activities in (("1", ("A", "B", "C")), ("2", ("A", "C", "B"))):
            trace = Trace(attributes={"concept:name": case})
            for index, activity in enumerate(activities):
                event = Event({"concept:name": activity, "time:timestamp": base + timedelta(hours=int(case), minutes=index)})
                trace.append(event)
                rows.append({"case:concept:name": case, **event})
            log.append(trace)
        return log, pd.DataFrame(rows)

    def test_all_performance_spectrum_variants(self):
        log, dataframe = self._log_and_dataframe()
        activities = ["A", "B", "C"]
        outputs = [
            performance_spectrum.apply(log, activities, variant=performance_spectrum.Variants.LOG),
            performance_spectrum.apply(log, activities, variant=performance_spectrum.Variants.LOG_DISCONNECTED),
            performance_spectrum.apply(dataframe, activities, variant=performance_spectrum.Variants.DATAFRAME),
            performance_spectrum.apply(dataframe, activities, variant=performance_spectrum.Variants.DATAFRAME_DISCONNECTED),
        ]
        for output in outputs:
            self.assertEqual(activities, output["list_activities"])
            self.assertIn("points", output)
        with self.assertRaises(Exception):
            performance_spectrum.apply(log, ["A"])
        self.assertFalse(performance_spectrum.is_polars_lazyframe(dataframe))

    def test_networkx_and_mocked_pyvis_sna_visualizations(self):
        directed = SNA({("alice", "bob"): 2, ("bob", "carol"): 0.5}, True)
        undirected = SNA({("alice", "bob"): 2}, False)
        image = sna_visualizer.apply(
            directed,
            parameters={"weight_threshold": 1, "format": "png"},
            variant=sna_visualizer.Variants.NETWORKX,
        )
        self.assertTrue(os.path.exists(image))
        with tempfile.NamedTemporaryFile(suffix=".png") as destination:
            sna_visualizer.save(
                image, destination.name, variant=sna_visualizer.Variants.NETWORKX
            )
            self.assertGreater(os.path.getsize(destination.name), 0)
        with mock.patch("pm4py.visualization.sna.variants.networkx.constants.DEFAULT_ENABLE_VISUALIZATIONS_VIEW", False):
            self.assertIsNone(
                sna_visualizer.view(image, variant=sna_visualizer.Variants.NETWORKX)
            )

        pyvis_network = types.ModuleType("pyvis.network")
        pyvis_network.Network = _FakeNetwork
        pyvis_network.__spec__ = importlib.machinery.ModuleSpec("pyvis.network", loader=None)
        pyvis_package = types.ModuleType("pyvis")
        pyvis_package.network = pyvis_network
        pyvis_package.__spec__ = importlib.machinery.ModuleSpec("pyvis", loader=None)
        with mock.patch.dict(sys.modules, {"pyvis": pyvis_package, "pyvis.network": pyvis_network}):
            html = sna_visualizer.apply(
                undirected,
                parameters={"weight_threshold": 0},
                variant=sna_visualizer.Variants.PYVIS,
            )
        with open(html) as html_file:
            self.assertIn("network", html_file.read())
        with tempfile.NamedTemporaryFile(suffix=".html") as destination:
            sna_visualizer.save(html, destination.name, variant=sna_visualizer.Variants.PYVIS)
            self.assertGreater(os.path.getsize(destination.name), 0)
        with mock.patch("pm4py.visualization.sna.variants.pyvis.constants.DEFAULT_ENABLE_VISUALIZATIONS_VIEW", False):
            self.assertIsNone(sna_visualizer.view(html, variant=sna_visualizer.Variants.PYVIS))

    def test_object_graph_and_footprints_visualizations(self):
        ocel = pm4py.read_ocel(self._input_path("ocel", "example_log.jsonocel"))
        object_ids = list(ocel.objects[ocel.object_id_column])[:3]
        graph = {(object_ids[0], object_ids[1]), (object_ids[1], object_ids[2])}
        directed = object_graph_visualizer.apply(
            ocel,
            graph,
            parameters={"directed": True, "format": "svg", "enable_graph_title": True, "graph_title": "Objects"},
        )
        undirected = object_graph_visualizer.apply(
            ocel, graph, parameters={"directed": False, "format": "svg"}
        )
        self.assertIn("digraph", directed.source)
        self.assertIn("graph", undirected.source)

        first = {"sequence": {("A", "B"), ("B", "C")}, "parallel": {("A", "C"), ("C", "A")}}
        second = {"sequence": {("A", "B"), ("C", "B")}, "parallel": set()}
        comparison = comparison_symmetric.apply(
            first,
            second,
            parameters={"format": "svg", "enable_graph_title": True, "graph_title": "Comparison"},
        )
        self.assertIn("table", comparison.source)
        with self.assertRaises(Exception):
            comparison_symmetric.apply([first], second)

    def test_ocpn_alternative_format_projection_and_metrics(self):
        p1 = OCPetriNet.Place("p1", "order")
        p2 = OCPetriNet.Place("p2", "order")
        p3 = OCPetriNet.Place("p3", "item")
        p4 = OCPetriNet.Place("p4", "item")
        transition = OCPetriNet.Transition("create", "create")
        arcs = [
            OCPetriNet.Arc(p1, transition, "order", is_variable=False),
            OCPetriNet.Arc(transition, p2, "order", is_variable=False),
            OCPetriNet.Arc(p3, transition, "item", is_variable=True),
            OCPetriNet.Arc(transition, p4, "item", is_variable=True),
        ]
        for arc in arcs:
            arc.source.add_out_arc(arc)
            arc.target.add_in_arc(arc)
        ocpn = OCPetriNet(
            "ocpn",
            places=[p1, p2, p3, p4],
            transitions=[transition],
            arcs=arcs,
            initial_marking=OCMarking({p1: Counter({"o1": 1}), p3: Counter({"i1": 1, "i2": 1})}),
            final_marking=OCMarking({p2: Counter({"o1": 1}), p4: Counter({"i1": 1, "i2": 1})}),
        )
        alternative = to_alternative_format.apply(ocpn)
        self.assertEqual({"order", "item"}, alternative["object_types"])
        self.assertEqual({"create"}, alternative["activities"])
        self.assertFalse(alternative["double_arcs_on_activity"]["order"]["create"])
        self.assertTrue(alternative["double_arcs_on_activity"]["item"]["create"])
        order_net, order_im, order_fm = alternative["petri_nets"]["order"]
        self.assertEqual(1, sum(order_im.values()))
        self.assertEqual(1, sum(order_fm.values()))
        self.assertTrue(order_net.transitions)
        self.assertFalse(to_alternative_format.oc_marking_to_petri(None, {}))

    def test_process_tree_regex_and_timeout_utility(self):
        a = ProcessTree(label="A")
        b = ProcessTree(label="B")
        tau = ProcessTree()
        sequence = ProcessTree(operator=Operator.SEQUENCE, children=[a, b])
        xor = ProcessTree(operator=Operator.XOR, children=[sequence, tau])
        expression, mapping = process_tree_regex.pt_to_regex(xor)
        self.assertTrue(expression.startswith("^"))
        self.assertEqual({"A", "B"}, set(mapping))
        loop = ProcessTree(operator=Operator.LOOP, children=[a])
        self.assertIn("+", process_tree_regex.pt_to_regex(loop)[0])
        parallel = ProcessTree(operator=Operator.PARALLEL, children=[a, b])
        with self.assertRaises(Exception):
            process_tree_regex.pt_to_regex(parallel)

        self.assertEqual(3, timeout.func_timeout(None, lambda x, y=0: x + y, args=(1,), kwargs={"y": 2}))
        self.assertEqual("ok", timeout.func_timeout(1, lambda: "ok"))
        with self.assertRaisesRegex(ValueError, "timeout"):
            timeout.func_timeout(0, lambda: None)
        with self.assertRaisesRegex(RuntimeError, "boom"):
            timeout.func_timeout(1, lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        with self.assertRaises(timeout.FunctionTimedOut):
            timeout.func_timeout(0.001, time.sleep, args=(0.05,))

    def test_dfg_filtering_connectivity_and_activity_boundaries(self):
        dfg = {
            ("A", "B"): 10,
            ("A", "C"): 4,
            ("C", "B"): 4,
            ("B", "D"): 10,
            ("A", "X"): 1,
            ("X", "D"): 1,
            ("B", "A"): 1,
        }
        starts = {"A": 15}
        ends = {"D": 15}
        counts = {"A": 15, "B": 14, "C": 4, "D": 15, "X": 1}

        graph, source, sink = dfg_filtering.generate_nx_graph_from_dfg(
            dfg, starts, ends, counts
        )
        self.assertIn(source, graph)
        self.assertIn(sink, graph)
        adjacency, reverse, source2, sink2 = dfg_filtering.build_adjacency_structures(
            dfg, starts, ends
        )
        self.assertIn("D", dfg_filtering.bfs_reachable(source2, adjacency))
        cleaned = dfg_filtering.remove_unreachable_nodes(
            dict(dfg), dict(starts), dict(ends), {**counts, "Z": 1},
            {**adjacency, "Z": set()}, {**reverse, "Z": set()}, source2, sink2
        )
        self.assertNotIn("Z", cleaned[3])

        results = [
            dfg_filtering.filter_dfg_on_activities_percentage(dfg, starts, ends, counts, 0.5),
            dfg_filtering.filter_dfg_on_paths_percentage(dfg, starts, ends, counts, 0.5),
            dfg_filtering.filter_dfg_on_paths_percentage(dfg, starts, ends, counts, 0.5, keep_all_activities=True),
            dfg_filtering.filter_dfg_keep_connected(dfg, starts, ends, counts, 0.5),
            dfg_filtering.filter_dfg_keep_connected(dfg, starts, ends, counts, 0.5, keep_all_activities=True),
            dfg_filtering.filter_dfg_to_activity(dfg, starts, ends, counts, "B"),
            dfg_filtering.filter_dfg_from_activity(dfg, starts, ends, counts, "B"),
            dfg_filtering.filter_dfg_contain_activity(dfg, starts, ends, counts, "C"),
        ]
        for filtered_dfg, filtered_starts, filtered_ends, filtered_counts in results:
            self.assertIsInstance(filtered_dfg, dict)
            self.assertIsInstance(filtered_starts, dict)
            self.assertIsInstance(filtered_ends, dict)
            self.assertIsInstance(filtered_counts, dict)

        cleaned_dict = dfg_filtering.clean_dfg_based_on_noise_thresh(
            dfg, counts, 0.5, parameters={"most_common_paths": [("A", "X")]}
        )
        self.assertIn(("A", "B"), cleaned_dict)
        list_dfg = list(dfg.items())
        cleaned_list = dfg_filtering.clean_dfg_based_on_noise_thresh(
            list_dfg, counts, 0.5
        )
        self.assertIsInstance(cleaned_list, list)


if __name__ == "__main__":
    unittest.main()
