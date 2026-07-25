import contextlib
import datetime
import io
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from pm4py.objects.log.obj import Event, EventLog, Trace
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import petri_utils


class RemainingAlgorithmsCoverageTest(unittest.TestCase):
    """Regression coverage for public algorithms and their boundary behavior."""

    @staticmethod
    def _log(*variants):
        log = EventLog()
        for index, activities in enumerate(variants):
            trace = Trace(attributes={"concept:name": str(index)})
            for activity in activities:
                trace.append(Event({"concept:name": activity}))
            log.append(trace)
        return log

    @staticmethod
    def _sequence_net():
        net = PetriNet("sequence")
        source = PetriNet.Place("source")
        sink = PetriNet.Place("sink")
        transition = PetriNet.Transition("a", "A")
        net.places.update({source, sink})
        net.transitions.add(transition)
        petri_utils.add_arc_from_to(source, transition, net)
        petri_utils.add_arc_from_to(transition, sink, net)
        return net, Marking({source: 1}), Marking({sink: 1})

    def test_dfg_precision_and_invisible_conversion(self):
        from pm4py.algo.evaluation.precision.dfg import algorithm as precision
        from pm4py.objects.conversion.dfg.variants import (
            to_petri_net_invisibles_no_duplicates as converter,
        )

        log = self._log(("A", "B", "C"), ("A", "C"), ("X", "Y"))
        dfg = {("A", "B"): 2, ("B", "C"): 2, ("A", "C"): 1}
        value = precision.apply(log, dfg, {"A": 3}, {"C": 3})
        self.assertGreaterEqual(value, 0.0)
        self.assertLessEqual(value, 1.0)
        self.assertEqual(1.0, precision.apply(EventLog(), {}, {}, {}))

        net, initial, final = converter.apply(
            dfg,
            parameters={
                converter.Parameters.START_ACTIVITIES: {"A": 3},
                converter.Parameters.END_ACTIVITIES: {"C": 3},
                converter.Parameters.PARAM_ARTIFICIAL_START_ACTIVITY: "BEGIN",
                converter.Parameters.PARAM_ARTIFICIAL_END_ACTIVITY: "END",
            },
        )
        self.assertEqual(1, sum(initial.values()))
        self.assertEqual(1, sum(final.values()))
        self.assertTrue(any(t.label is None for t in net.transitions))
        self.assertTrue(any(t.label == "A" for t in net.transitions))

    def test_sentence_and_word2vec_trace_encodings(self):
        from pm4py.algo.transformation.trace_encodings.variants import (
            cases_transformers,
            events_transformers,
            word2vec,
        )

        frame = pd.DataFrame(
            {
                "case:concept:name": ["c1", "c1", "c2"],
                "concept:name": ["A", "B", "C"],
                "org:resource": ["r1", "r2", "r1"],
                "@@index": [1, 2, 3],
            }
        )

        class FakeSentenceTransformer:
            def __init__(self, model):
                self.model = model

            def encode(self, sentences):
                return [[float(i), float(len(sentence))] for i, sentence in enumerate(sentences)]

        sentence_module = types.ModuleType("sentence_transformers")
        sentence_module.SentenceTransformer = FakeSentenceTransformer
        with mock.patch.dict(sys.modules, {"sentence_transformers": sentence_module}):
            event_ids, event_vectors = events_transformers.apply(frame)
            self.assertEqual([1, 2, 3], event_ids)
            self.assertEqual(3, len(event_vectors))
            rich_ids, _ = events_transformers.apply(
                frame,
                parameters={"event_attributes": ["concept:name", "org:resource"]},
            )
            self.assertEqual(event_ids, rich_ids)

            case_ids, case_vectors = cases_transformers.apply(frame)
            self.assertEqual({"c1", "c2"}, set(case_ids))
            self.assertEqual(2, len(case_vectors))
            rich_case_ids, _ = cases_transformers.apply(
                frame,
                parameters={"event_attributes": "org:resource"},
            )
            self.assertEqual({"c1", "c2"}, set(rich_case_ids))

        with mock.patch.object(events_transformers.similarity, "apply", return_value=[0.1, 0.9, 0.2]):
            selected = events_transformers.keep_top_k_per_similarity(
                frame,
                "query",
                1,
                event_ids,
                event_vectors,
                parameters={"keep_cases": True},
            )
            self.assertEqual([1, 2], selected["@@index"].tolist())
        with mock.patch.object(cases_transformers.similarity, "apply", return_value=[0.2, 0.8]):
            selected = cases_transformers.keep_top_k_per_similarity(
                frame, "query", 1, case_ids, case_vectors
            )
            self.assertEqual(1, selected["case:concept:name"].nunique())

        self.assertEqual([0.0, 0.0], word2vec._aggregate([], 2, "mean"))
        self.assertEqual([4.0, 6.0], word2vec._aggregate([[1, 2], [3, 4]], 2, "sum"))

        class FakeKeyedVectors(dict):
            pass

        class FakeWord2Vec:
            def __init__(self, *args, **kwargs):
                self.vector_size = kwargs.get("vector_size", 2)
                self.wv = FakeKeyedVectors(A=np.array([1.0, 2.0]), B=np.array([3.0, 4.0]))

        gensim = types.ModuleType("gensim")
        gensim_models = types.ModuleType("gensim.models")
        gensim_models.Word2Vec = FakeWord2Vec
        gensim.models = gensim_models
        with mock.patch.dict(sys.modules, {"gensim": gensim, "gensim.models": gensim_models}):
            data, names = word2vec.apply(
                self._log(("A", "B"), ("missing",)),
                parameters={"vector_size": 2, "aggregation": "sum"},
            )
        self.assertEqual([[4.0, 6.0], [0.0, 0.0]], data)
        self.assertEqual(["@@word2vec_dim_0", "@@word2vec_dim_1"], names)

    def test_small_model_objects_and_attribute_promotion(self):
        from pm4py.objects.heuristics_net.obj import HeuristicsNet
        from pm4py.objects.log.util import move_attrs_to_trace
        from pm4py.objects.trie.obj import Trie

        child = Trie("B", final=True, depth=1)
        root = Trie("A", children=[child])
        child.parent = root
        self.assertIn("-- END --", str(root))
        clone = Trie("A", children=[Trie("B", final=True, depth=1)])
        self.assertEqual(root, clone)
        self.assertNotEqual(root, Trie("X"))
        self.assertNotEqual(root, object())
        self.assertEqual(hash(root), hash(clone))
        root.label, root.final, root.depth = "ROOT", True, 2
        root.children = [child]
        self.assertEqual(("ROOT", True, 2, root), (root.label, root.final, root.depth, child.parent))

        class Node:
            def __init__(self, name):
                self.node_name = name
                self.output_connections = {}

        first = HeuristicsNet({("A", "B"): 1}, net_name="first")
        second = HeuristicsNet({("A", "C"): 1}, net_name="second")
        a1, b1, a2, b2, c2 = Node("A"), Node("B"), Node("A"), Node("B"), Node("C")
        a1.output_connections[b1] = 2
        a2.output_connections[b2] = 3
        a2.output_connections[c2] = 4
        first.nodes = {"A": a1, "B": b1}
        second.nodes = {"A": a2, "B": b2, "C": c2}
        merged = first + second
        self.assertEqual(["first", "second"], merged.net_name)
        self.assertEqual({"A", "B", "C"}, set(merged.nodes))
        self.assertIn("A", repr(merged))

        log = EventLog()
        for index in range(2):
            trace = Trace()
            trace.append(Event({"concept:name": "A", "customer": "gold", "varying": index}))
            trace.append(Event({"concept:name": "B", "customer": "gold", "varying": index + 1}))
            log.append(trace)
        promoted = move_attrs_to_trace.apply(log, {"enable_deepcopy": True})
        self.assertEqual("gold", promoted[0].attributes["customer"])
        self.assertNotIn("customer", promoted[0][0])
        self.assertIn("customer", log[0][0])

    @unittest.skipUnless(
        importlib.util.find_spec("sklearn"), "scikit-learn is not installed"
    )
    def test_visualization_serialization_and_decision_tree_text(self):
        from graphviz import Digraph
        from sklearn.tree import DecisionTreeClassifier
        from pm4py.visualization.common import gview, html
        from pm4py.visualization.decisiontree.util import dt_to_string
        from pm4py.visualization.process_tree.variants import symbolic
        import pm4py

        tree = pm4py.parse_process_tree("->( 'A', tau, X( 'B', 'C' ) )")
        graph = symbolic.apply(
            tree,
            parameters={
                "format": "html",
                "enable_deepcopy": False,
                "enable_graph_title": True,
                "graph_title": "Regression tree",
                "color_map": {tree: "red"},
            },
        )
        self.assertEqual("plain-ext", graph.format)
        self.assertIn("Regression tree", graph.source)
        self.assertEqual("red", symbolic.get_color(tree, {tree: "red"}))
        self.assertEqual("black", symbolic.get_color(tree, {}))

        classifier = DecisionTreeClassifier(max_depth=2, random_state=7).fit(
            [[0, 0], [0, 1], [1, 0], [1, 1]], [0, 0, 1, 1]
        )
        rules, variables = dt_to_string.apply(classifier, ["amount", "priority"])
        self.assertTrue(rules)
        self.assertTrue(any("amount" in names for names in variables.values()))

        dot = Digraph("example")
        dot.node("A")
        self.assertIn(b"digraph example", gview.serialize_dot(dot))
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "graph.html")
            self.assertEqual(path, html.form_html(dot, path))
            with open(path, encoding="utf-8") as html_file:
                self.assertIn("Viz(gv", html_file.read())
            second_path = os.path.join(directory, "saved.html")
            html.save(dot, second_path)
            self.assertTrue(os.path.exists(second_path))

            with mock.patch.object(html.vis_utils, "check_visualization_inside_jupyter", return_value=False), mock.patch.object(
                html.vis_utils, "open_opsystem_image_viewer"
            ) as viewer:
                html.view(dot)
                viewer.assert_called_once()

        dot.format = "gv"
        with mock.patch.object(gview.constants, "DEFAULT_ENABLE_VISUALIZATIONS_VIEW", True), mock.patch.object(
            gview.dot_util, "check_dot_installed", return_value=True
        ), contextlib.redirect_stdout(io.StringIO()) as output:
            gview.view(dot)
        self.assertIn("digraph", output.getvalue())

    def test_attribute_distribution_edge_cases(self):
        from pm4py.statistics.attributes.common import get

        self.assertEqual([["A", 3], ["B", 1]], get.get_sorted_attributes_list({"B": 1, "A": 3}))
        self.assertEqual(2, get.get_attributes_threshold([["A", 3], ["B", 2]], 0.5))
        self.assertEqual(([], []), get.get_kde_numeric_attribute([]))
        x, y = get.get_kde_numeric_attribute([5, 5], {"graph_points": 10})
        self.assertEqual((10, 10), (len(x), len(y)))
        for values in ([1, 2, 4], [-4, -2, -1], [-2, 0, 3]):
            x, y = get.get_kde_numeric_attribute(values, {"graph_points": 8})
            self.assertEqual(len(x), len(y))
        self.assertTrue(get.get_kde_numeric_attribute_json([1, 2, 3]))

        moment = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
        x, y = get.get_kde_date_attribute([moment], {"graph_points": 6})
        self.assertEqual((6, 6), (len(x), len(y)))
        dates = [moment + datetime.timedelta(days=i) for i in range(3)]
        x, y = get.get_kde_date_attribute(dates, {"graph_points": 8, "points_to_sample": 3})
        self.assertEqual(len(x), len(y))
        self.assertTrue(get.get_kde_date_attribute_json(dates, {"graph_points": 8}))

    def test_alpha_plus_loop_and_relation_variants(self):
        from pm4py.algo.discovery.alpha.variants import plus

        scenarios = (
            (("A", "A", "B", "C"),),
            (("A", "B", "B", "C"),),
            (("A", "B", "A", "B", "C"), ("A", "C", "B", "C")),
            (("A",),),
        )
        for variants in scenarios:
            net, initial, final = plus.apply(self._log(*variants))
            self.assertTrue(net.transitions)
            self.assertEqual(1, sum(initial.values()))
            self.assertEqual(1, sum(final.values()))

        causal, parallel, follows = plus.get_relations(
            EventLog([Trace(["A", "B", "A"]), Trace(["B", "A", "B"])])
        )
        self.assertTrue(follows)
        self.assertIsInstance(causal, dict)
        self.assertIsInstance(parallel, dict)
        self.assertIsInstance(plus.get_sharp_relation(follows, "A", "B"), bool)
        self.assertIsInstance(plus.get_sharp_relations_for_sets(follows, {"A"}, {"B"}), bool)

    def test_woflan_diagnostic_branch_orchestration(self):
        from pm4py.algo.analysis.woflan import algorithm as wf

        net, initial, final = self._sequence_net()
        obj = wf.woflan(net, initial, final, print_diagnostics=True)

        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(wf.step_1(wf.woflan("not-a-net", initial, final, True)))
            self.assertFalse(wf.step_1(wf.woflan(net, Marking(), final, True)))
            with mock.patch.object(wf, "step_2", return_value="step2"):
                self.assertEqual("step2", wf.step_1(obj))

            with mock.patch.object(wf, "compute_place_invariants", return_value=np.array([[1, 1]])), mock.patch.object(
                wf, "transform_basis", return_value=np.array([[1, 1]])
            ), mock.patch.object(wf, "compute_s_components", return_value=[set(net.places)]), mock.patch.object(
                wf, "compute_uncovered_places_in_component", return_value=[]
            ), mock.patch.object(wf, "step_10", return_value="ten"):
                obj.set_s_c_net(net)
                self.assertEqual("ten", wf.step_3(obj))

            with mock.patch.object(wf, "compute_uncovered_places_in_component", return_value=[next(iter(net.places))]), mock.patch.object(
                wf, "compute_place_invariants", return_value=np.array([[1, 1]])
            ), mock.patch.object(wf, "transform_basis", return_value=np.array([[1, 1]])), mock.patch.object(
                wf, "compute_s_components", return_value=[]
            ), mock.patch.object(wf, "step_4", return_value="four"):
                self.assertFalse(wf.step_3(obj, return_asap_when_unsound=True))
                self.assertEqual("four", wf.step_3(obj))

            with mock.patch.object(wf, "compute_not_well_handled_pairs", return_value=[]), mock.patch.object(
                wf, "step_5", return_value="five"
            ):
                self.assertEqual("five", wf.step_4(obj))
                self.assertFalse(wf.step_4(obj, return_asap_when_unsound=True))
            with mock.patch.object(wf, "compute_not_well_handled_pairs", return_value=[("p", "t")]), mock.patch.object(
                wf, "step_5", return_value="five"
            ):
                self.assertEqual("five", wf.step_4(obj))

            obj.set_uniform_place_invariants(np.array([[1, 1]]))
            with mock.patch.object(wf, "compute_uncovered_place_in_invariants", return_value=[]), mock.patch.object(
                wf, "step_10", return_value="ten"
            ):
                self.assertEqual("ten", wf.step_5(obj))
            with mock.patch.object(wf, "compute_uncovered_place_in_invariants", return_value=list(net.places)), mock.patch.object(
                wf, "step_6", return_value="six"
            ):
                self.assertEqual("six", wf.step_5(obj))

            obj.set_place_invariants(np.array([[1, 1]]))
            with mock.patch.object(wf, "transform_basis", return_value=np.array([[1, 1]])), mock.patch.object(
                wf, "compute_uncovered_place_in_invariants", return_value=[]
            ), mock.patch.object(wf, "step_10", return_value="ten"):
                self.assertEqual("ten", wf.step_6(obj))
            with mock.patch.object(wf, "transform_basis", return_value=np.array([[1, 1]])), mock.patch.object(
                wf, "compute_uncovered_place_in_invariants", return_value=list(net.places)
            ), mock.patch.object(wf, "step_7", return_value="seven"):
                self.assertEqual("seven", wf.step_6(obj))

            graph = wf.nx_utils.DiGraph()
            graph.add_node(0, marking=np.array([1, 0]))
            with mock.patch.object(wf, "minimal_coverability_graph", return_value=graph), mock.patch.object(
                wf, "check_for_improper_conditions", return_value=[]
            ), mock.patch.object(wf, "step_8", return_value="eight"), mock.patch.object(
                wf, "step_10", return_value="ten"
            ):
                obj.set_left(True)
                self.assertEqual("eight", wf.step_7(obj))
                obj.set_left(False)
                self.assertEqual("ten", wf.step_7(obj))
            with mock.patch.object(wf, "minimal_coverability_graph", return_value=graph), mock.patch.object(
                wf, "check_for_improper_conditions", return_value=[0]
            ), mock.patch.object(wf, "step_9", return_value="nine"):
                self.assertFalse(wf.step_7(obj, return_asap_when_unsound=True))
                self.assertEqual("nine", wf.step_7(obj))

            with mock.patch.object(wf, "step_10", return_value="ten"):
                self.assertEqual("ten", wf.step_8(obj))
            with mock.patch.object(wf, "compute_unbounded_sequences", return_value=[["t"]]):
                self.assertFalse(wf.step_9(obj))

            obj.set_mcg(graph)
            with mock.patch.object(wf, "check_for_dead_tasks", return_value=[]), mock.patch.object(
                wf, "step_11", return_value="eleven"
            ), mock.patch.object(wf, "step_12", return_value="twelve"):
                obj.set_left(True)
                self.assertEqual("eleven", wf.step_10(obj))
                obj.set_left(False)
                self.assertFalse(wf.step_10(obj, return_asap_when_unsound=True))
                self.assertEqual("twelve", wf.step_10(obj))
            with mock.patch.object(wf, "check_for_dead_tasks", return_value=["dead"]):
                self.assertFalse(wf.step_10(obj))

            strongly_connected = wf.nx_utils.DiGraph()
            strongly_connected.add_edge(0, 1)
            strongly_connected.add_edge(1, 0)
            with mock.patch.object(wf, "reachability_graph", return_value=strongly_connected):
                self.assertTrue(wf.step_11(obj))
            disconnected = wf.nx_utils.DiGraph()
            disconnected.add_edge(0, 1)
            with mock.patch.object(wf, "reachability_graph", return_value=disconnected), mock.patch.object(
                wf, "step_13", return_value="thirteen"
            ):
                self.assertFalse(wf.step_11(obj, return_asap_when_unsound=True))
                self.assertEqual("thirteen", wf.step_11(obj))
                self.assertFalse(wf.step_12(obj, return_asap_when_unsound=True))
                self.assertEqual("thirteen", wf.step_12(obj))
            with mock.patch.object(wf, "compute_non_live_sequences", return_value=[["A"]]):
                self.assertFalse(wf.step_13(obj))

        output = obj.get_output()
        self.assertIn(wf.Outputs.DIAGNOSTIC_MESSAGES, output)
        result, diagnostics = wf.apply(
            net,
            initial,
            final,
            parameters={"return_diagnostics": True, "print_diagnostics": False},
        )
        self.assertTrue(result)
        self.assertIn(wf.Outputs.DIAGNOSTIC_MESSAGES, diagnostics)

    @unittest.skipUnless(
        importlib.util.find_spec("pulp"), "pulp is not installed"
    )
    def test_process_tree_alignment_entry_points_and_boundaries(self):
        import pm4py
        from pm4py.algo.conformance.alignments.process_tree.variants import milp, search_graph_pt
        from pm4py.objects.process_tree.obj import Operator, ProcessTree

        tree = pm4py.parse_process_tree("->( 'A', X( 'B', 'C' ), +( 'D', 'E' ) )")
        variants = [("A", "B", "D", "E"), ("A", "C", "E", "D"), ("A", "X")]
        results = search_graph_pt.apply_from_variants_list(
            variants + [variants[0]], tree, {search_graph_pt.Parameters.SHOW_PROGRESS_BAR: False}
        )
        self.assertEqual(4, len(results))
        self.assertEqual(results[0]["cost"], results[-1]["cost"])

        trace = Trace([Event({"concept:name": "A"}), Event({"concept:name": "X"})])
        self.assertIn("alignment", search_graph_pt.apply(trace, tree))
        self.assertIn("alignment", search_graph_pt.apply_multiprocessing(trace, tree))
        frame = pd.DataFrame(
            {
                "case:concept:name": ["c1", "c1", "c2"],
                "concept:name": ["A", "B", "X"],
            }
        )
        self.assertEqual(2, len(search_graph_pt.apply(frame, tree)))

        tau_loop = ProcessTree(
            operator=Operator.LOOP,
            children=[ProcessTree(), ProcessTree(label="R")],
        )
        for child in tau_loop.children:
            child.parent = tau_loop
        tau_aligner = milp.ProcessTreeAligner(tau_loop)
        self.assertEqual(0, tau_aligner.align(tuple())[0])

        unary = ProcessTree(operator=Operator.SEQUENCE, children=[ProcessTree(label="A")])
        unary.children[0].parent = unary
        unary_aligner = milp.ProcessTreeAligner(unary)
        aligned = milp.apply_list_tuple_activities(
            [("A",), ("X",), ("A",)], unary_aligner, {milp.Parameters.SHOW_PROGRESS_BAR: False}
        )
        self.assertEqual(3, len(aligned))

        malformed_loop = ProcessTree(operator=Operator.LOOP, children=[ProcessTree(label="A")])
        malformed_loop.children[0].parent = malformed_loop
        with self.assertRaisesRegex(Exception, "exactly two children"):
            milp.ProcessTreeAligner(malformed_loop)


if __name__ == "__main__":
    unittest.main()
