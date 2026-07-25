import copy
import os
import unittest
from datetime import datetime, timezone

import pm4py
from pm4py import analysis
from pm4py.objects.log.obj import Event, Trace
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import petri_utils, reduction
from pm4py.util import nx_utils
from pm4py.visualization.petri_net.util import vis_trans_shortest_paths


class _RecordingSession:
    def __init__(self):
        self.calls = []

    def run(self, query, **parameters):
        self.calls.append((query, parameters))
        return []


class _DownloadSession:
    def run(self, query, **parameters):
        if query == "MATCH (n) RETURN n":
            return [
                {
                    "n": {
                        "id": "case-1",
                        "type": "CASE",
                        "concept:name": "case-1",
                    }
                },
                {
                    "n": {
                        "id": "event-1",
                        "type": "EVENT",
                        "concept:name": "A",
                        "time:timestamp": "2020-01-01T00:00:00+00:00",
                    }
                },
            ]
        return [
            {
                "n": {"id": "event-1"},
                "m": {"id": "case-1"},
                "r": {"type": "BELONGS_TO"},
            }
        ]


class GraphAnalysisCoverageTest(unittest.TestCase):
    @staticmethod
    def _input_path(*parts):
        return os.path.join(os.path.dirname(__file__), "input_data", *parts)

    @staticmethod
    def _series_net():
        net = PetriNet("series")
        p0, p1, p2, p3 = [PetriNet.Place(f"p{i}") for i in range(4)]
        a = PetriNet.Transition("a", "A")
        tau = PetriNet.Transition("tau", None)
        b = PetriNet.Transition("b", "B")
        net.places.update({p0, p1, p2, p3})
        net.transitions.update({a, tau, b})
        for source, target in (
            (p0, a), (a, p1), (p1, tau), (tau, p2), (p2, b), (b, p3),
        ):
            petri_utils.add_arc_from_to(source, target, net)
        return net, Marking({p0: 1}), Marking({p3: 1})

    def test_networkx_facade_and_graph_log_conversions(self):
        graph = nx_utils.DiGraph()
        graph.add_edges_from((("A", "B"), ("B", "C"), ("C", "A")))
        undirected = nx_utils.Graph(graph)
        multi = nx_utils.MultiGraph()
        multi_directed = nx_utils.MultiDiGraph()
        multi.add_edge("A", "B")
        multi_directed.add_edge("A", "B")

        self.assertEqual({"B", "C"}, nx_utils.descendants(graph, "A"))
        self.assertEqual({"A", "B"}, nx_utils.ancestors(graph, "C"))
        self.assertEqual(1, len(list(nx_utils.connected_components(undirected))))
        self.assertEqual({"A", "B", "C"}, set(nx_utils.bfs_tree(graph, "A")))
        self.assertTrue(nx_utils.has_path(graph, "A", "C"))
        self.assertTrue(nx_utils.is_strongly_connected(graph))
        self.assertEqual(1, len(list(nx_utils.strongly_connected_components(graph))))
        self.assertEqual("C", nx_utils.shortest_path(graph, "A", "C")[-1])
        self.assertEqual(3, len(dict(nx_utils.all_pairs_shortest_path(graph))))
        self.assertEqual(3, len(dict(nx_utils.all_pairs_dijkstra(graph))))
        self.assertEqual(3, len(nx_utils.degree_centrality(undirected)))
        self.assertTrue(list(nx_utils.find_cliques(undirected)))
        self.assertTrue(nx_utils.greedy_modularity_communities(undirected))

        flow_graph = nx_utils.DiGraph()
        flow_graph.add_edge("s", "t", capacity=2)
        self.assertEqual(2, nx_utils.maximum_flow_value(flow_graph, "s", "t"))
        dag = nx_utils.DiGraph((("A", "B"), ("B", "C")))
        self.assertEqual(["A", "B", "C"], list(nx_utils.topological_sort(dag)))
        self.assertIn("A", nx_utils.contracted_nodes(dag, "A", "B"))

        upload_graph = nx_utils.DiGraph()
        upload_graph.add_node(
            "event-1",
            attr={
                "type": "EVENT",
                "concept:name": "A",
                "time:timestamp": datetime(2020, 1, 1, tzinfo=timezone.utc),
                "cost": 1.5,
                "other": 3,
            },
        )
        upload_graph.add_node(
            "case-1", attr={"type": "CASE", "concept:name": "case-1"}
        )
        upload_graph.add_edge(
            "event-1", "case-1", attr={"type": "BELONGS_TO"}
        )
        session = _RecordingSession()
        nx_utils.neo4j_upload(
            upload_graph, session, parameters={"show_progress_bar": False}
        )
        self.assertEqual(4, len(session.calls))

        downloaded = nx_utils.neo4j_download(_DownloadSession())
        event_log = nx_utils.nx_to_event_log(downloaded)
        self.assertEqual(1, len(event_log))
        self.assertEqual("A", event_log[0][0]["concept:name"])

        ocel_graph = nx_utils.DiGraph()
        ocel_graph.add_node(
            "e1",
            attr={
                "type": "EVENT",
                "ocel:eid": "e1",
                "ocel:activity": "Create",
                "ocel:timestamp": datetime(2020, 1, 1, tzinfo=timezone.utc),
            },
        )
        ocel_graph.add_node(
            "o1",
            attr={"type": "OBJECT", "ocel:oid": "o1", "ocel:type": "order"},
        )
        ocel_graph.add_node(
            "o2",
            attr={"type": "OBJECT", "ocel:oid": "o2", "ocel:type": "item"},
        )
        ocel_graph.add_edge(
            "e1", "o1", attr={"type": "E2O", "qualifier": "creation"}
        )
        ocel_graph.add_edge(
            "o1", "o2", attr={"type": "O2O", "qualifier": "contains"}
        )
        ocel = nx_utils.nx_to_ocel(ocel_graph)
        self.assertEqual(1, len(ocel.events))
        self.assertEqual(2, len(ocel.objects))
        self.assertEqual(1, len(ocel.o2o))

    def test_analysis_public_model_helpers(self):
        net, initial_marking, final_marking = pm4py.read_pnml(
            self._input_path("running-example.pnml")
        )
        log = pm4py.read_xes(
            self._input_path("running-example.xes"),
            return_legacy_log_object=True,
        )
        trace = log[0]

        sync_net, sync_im, sync_fm = analysis.construct_synchronous_product_net(
            trace, net, initial_marking, final_marking
        )
        self.assertTrue(sync_net.transitions)
        self.assertGreaterEqual(
            analysis.solve_marking_equation(net, initial_marking, final_marking), 0
        )
        self.assertGreaterEqual(
            analysis.solve_extended_marking_equation(
                trace, sync_net, sync_im, sync_fm, split_points=[1]
            ),
            0,
        )
        self.assertTrue(analysis.check_is_sound(net, initial_marking, final_marking))
        sound, diagnostics = analysis.check_soundness(
            net, initial_marking, final_marking
        )
        self.assertTrue(sound)
        self.assertIsInstance(diagnostics, dict)
        self.assertTrue(analysis.check_is_workflow_net(net))
        self.assertTrue(
            analysis.maximal_decomposition(net, initial_marking, final_marking)
        )
        for variant in ("arc_degree", "extended_cardoso", "extended_cyclomatic"):
            self.assertGreaterEqual(
                analysis.simplicity_petri_net(
                    net, initial_marking, final_marking, variant=variant
                ),
                0,
            )

        place = next(iter(initial_marking))
        self.assertEqual(1, analysis.generate_marking(net, place)[place])
        self.assertEqual(1, analysis.generate_marking(net, place.name)[place])
        self.assertEqual(2, analysis.generate_marking(net, {place: 2})[place])
        self.assertEqual(3, analysis.generate_marking(net, {place.name: 3})[place])
        self.assertTrue(analysis.get_enabled_transitions(net, initial_marking))
        self.assertIn("register request", analysis.get_activity_labels(log))
        self.assertIn(
            "register request",
            analysis.get_activity_labels(net, initial_marking, final_marking),
        )

        tree = pm4py.convert_to_process_tree(net, initial_marking, final_marking)
        self.assertEqual(1.0, analysis.behavioral_similarity(tree, tree))
        self.assertEqual(1.0, analysis.structural_similarity(tree, tree))
        self.assertEqual(1.0, analysis.label_sets_similarity(tree, tree))
        mapped = analysis.map_labels_from_second_model(tree, tree)
        self.assertEqual(set(analysis.get_activity_labels(tree)), set(analysis.get_activity_labels(mapped)))

        renamed = analysis.replace_activity_labels(
            {"register request": "register"}, tree
        )
        self.assertIn("register", analysis.get_activity_labels(renamed))
        with self.assertRaises(Exception):
            analysis.replace_activity_labels({}, object())

    def test_petri_reduction_rules(self):
        net, initial_marking, final_marking = self._series_net()
        before = (len(net.places), len(net.transitions))
        reduction.apply_simple_reduction(net)
        self.assertLess((len(net.places), len(net.transitions)), before)

        fst_net, _, _ = self._series_net()
        reduction.apply_fst_rule(fst_net)
        fsp_net, fsp_im, fsp_fm = self._series_net()
        reduction.apply_fsp_rule(fsp_net, fsp_im, fsp_fm)

        parallel = PetriNet("parallel transitions")
        p0, p1 = PetriNet.Place("p0"), PetriNet.Place("p1")
        tau1, tau2 = PetriNet.Transition("tau1"), PetriNet.Transition("tau2")
        parallel.places.update({p0, p1})
        parallel.transitions.update({tau1, tau2})
        for transition in (tau1, tau2):
            petri_utils.add_arc_from_to(p0, transition, parallel)
            petri_utils.add_arc_from_to(transition, p1, parallel)
        reduction.apply_fpt_rule(parallel)
        self.assertEqual(1, len(parallel.transitions))

        self_loop = PetriNet("self loop")
        source, loop_place = PetriNet.Place("source"), PetriNet.Place("loop")
        visible = PetriNet.Transition("visible", "A")
        tau = PetriNet.Transition("tau")
        self_loop.places.update({source, loop_place})
        self_loop.transitions.update({visible, tau})
        for source_node, target_node in (
            (source, visible), (visible, loop_place),
            (loop_place, tau), (tau, loop_place),
        ):
            petri_utils.add_arc_from_to(source_node, target_node, self_loop)
        reduction.apply_elt_rule(self_loop)
        self.assertNotIn(tau, self_loop.transitions)

        reduced, reduced_im, reduced_fm = reduction.apply_reset_inhibitor_net_reduction(
            *self._series_net()
        )
        self.assertIsInstance(reduced, PetriNet)
        self.assertIsInstance(reduced_im, Marking)
        self.assertIsInstance(reduced_fm, Marking)
        self.assertEqual(7, len(list(reduction.power_set({1, 2, 3}, min=1))))

    def test_petri_visualization_shortest_path_decorations(self):
        net = PetriNet("branching silent paths")
        places = [PetriNet.Place(f"p{i}") for i in range(5)]
        a = PetriNet.Transition("a", "A")
        tau = PetriNet.Transition("tau")
        b = PetriNet.Transition("b", "B")
        c = PetriNet.Transition("c", "C")
        net.places.update(places)
        net.transitions.update({a, tau, b, c})
        for source, target in (
            (places[0], a), (a, places[1]), (places[1], tau),
            (tau, places[2]), (places[2], b), (b, places[3]),
            (places[2], c), (c, places[4]),
        ):
            petri_utils.add_arc_from_to(source, target, net)

        paths = vis_trans_shortest_paths.get_shortest_paths(
            net, enable_extension=True
        )
        self.assertTrue(paths)
        dfg = {("a", "b"): 3, ("a", "c"): 5}
        counts = {"A": 2, "B": 3, "C": 5}
        for aggregation in ("sum", "mean", "median", "min", "max"):
            decorations = vis_trans_shortest_paths.get_decorations_from_dfg_spaths_acticount(
                net,
                dfg,
                paths,
                counts,
                variant="frequency",
                aggregation_measure=aggregation,
            )
            self.assertTrue(decorations)


if __name__ == "__main__":
    unittest.main()
