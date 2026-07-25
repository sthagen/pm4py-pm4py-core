import datetime
import importlib.util
import os
import sys
import types
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from pm4py.objects.log.obj import Event, EventLog, Trace
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import petri_utils


class FinalBufferCoverageTest(unittest.TestCase):
    """Focused checks that keep strict whole-package coverage above the target."""

    @staticmethod
    def _timed_log():
        base = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
        log = EventLog()
        for activities in (("A", "B", "C"), ("A", "C")):
            trace = Trace()
            for index, activity in enumerate(activities):
                trace.append(
                    Event(
                        {
                            "concept:name": activity,
                            "time:timestamp": base + datetime.timedelta(minutes=index),
                        }
                    )
                )
            log.append(trace)
        return log

    @staticmethod
    def _sequence_net():
        net = PetriNet("sequence")
        source, sink = PetriNet.Place("source"), PetriNet.Place("sink")
        transition = PetriNet.Transition("a", "A")
        net.places.update({source, sink})
        net.transitions.add(transition)
        petri_utils.add_arc_from_to(source, transition, net)
        petri_utils.add_arc_from_to(transition, sink, net)
        return net, Marking({source: 1}), Marking({sink: 1})

    def test_database_connector_query_contracts(self):
        from pm4py.algo.connectors.variants import camunda_workflow, sap_accounting, sap_o2c

        class Cursor:
            def __init__(self, rows):
                self.rows = rows
                self.query = None
                self.closed = False

            def execute(self, query):
                self.query = query

            def fetchall(self):
                return self.rows

            def close(self):
                self.closed = True

        class Connection:
            def __init__(self, rows):
                self.curs = Cursor(rows)
                self.closed = False

            def cursor(self):
                return self.curs

            def close(self):
                self.closed = True

        timestamp = pd.Timestamp("2024-01-01T08:00:00Z")
        cases = (
            (
                sap_o2c,
                [("1", "Create Sales Document", timestamp, "alice")],
                {"prefix": "SAP."},
                "SAP.VBAK",
            ),
            (
                sap_accounting,
                [("100-1", "Create Financial Document", timestamp, "bob", "SA")],
                {"prefix": "SAP."},
                "SAP.BKPF",
            ),
            (
                camunda_workflow,
                [("process", "case-1", "Approve", timestamp, "carol")],
                {},
                "act_hi_procinst",
            ),
        )
        for module, rows, parameters, expected_query_text in cases:
            connection = Connection(rows)
            frame = module.apply(connection, parameters)
            self.assertEqual(1, len(frame))
            self.assertIn(expected_query_text, connection.curs.query)
            self.assertTrue(connection.curs.closed)
            self.assertTrue(connection.closed)

        pyodbc = types.ModuleType("pyodbc")
        automatic = Connection(cases[2][1])
        pyodbc.connect = mock.Mock(return_value=automatic)
        with mock.patch.dict(sys.modules, {"pyodbc": pyodbc}):
            self.assertEqual(
                1,
                len(camunda_workflow.apply(None, {"connection_string": "dsn=test"})),
            )
        pyodbc.connect.assert_called_once_with("dsn=test")

    @unittest.skipUnless(
        importlib.util.find_spec("sklearn"), "scikit-learn is not installed"
    )
    def test_text_encoders_vectorizers_and_model_resolution(self):
        from pm4py.algo.transformation.trace_encodings.util import petri_net as petri_encoding
        from pm4py.algo.transformation.trace_encodings.util import sklearn_vectorization
        from pm4py.algo.transformation.trace_encodings.variants import bert, doc2vec

        log = self._timed_log()

        class FakeSentenceTransformer:
            def __init__(self, name):
                self.name = name

            def encode(self, sentences):
                return [np.array([float(index), float(len(sentence))]) for index, sentence in enumerate(sentences)]

        sentence_module = types.ModuleType("sentence_transformers")
        sentence_module.SentenceTransformer = FakeSentenceTransformer
        with mock.patch.dict(sys.modules, {"sentence_transformers": sentence_module}):
            data, names = bert.apply(log, {"bert_model": "fake"})
        self.assertEqual(2, len(data))
        self.assertEqual(["@@bert_dim_0", "@@bert_dim_1"], names)

        class TaggedDocument:
            def __init__(self, words, tags):
                self.words, self.tags = words, tags

        class Vector(list):
            def tolist(self):
                return list(self)

        class FakeDoc2Vec:
            def __init__(self, documents=None, vector_size=2, **kwargs):
                self.vector_size = vector_size
                self.dv = {document.tags[0]: Vector([float(document.tags[0]), 1.0]) for document in documents or []}

            def infer_vector(self, trace, epochs=1):
                return Vector([float(len(trace)), float(epochs)])

        gensim = types.ModuleType("gensim")
        models = types.ModuleType("gensim.models")
        doc_module = types.ModuleType("gensim.models.doc2vec")
        doc_module.Doc2Vec = FakeDoc2Vec
        doc_module.TaggedDocument = TaggedDocument
        models.doc2vec = doc_module
        gensim.models = models
        modules = {"gensim": gensim, "gensim.models": models, "gensim.models.doc2vec": doc_module}
        with mock.patch.dict(sys.modules, modules):
            trained, trained_names = doc2vec.apply(log, {"vector_size": 2})
            inferred, _ = doc2vec.apply(
                log, {"model": FakeDoc2Vec(vector_size=2), "epochs": 3}
            )
        self.assertEqual([[0.0, 1.0], [1.0, 1.0]], trained)
        self.assertEqual(["@@doc2vec_dim_0", "@@doc2vec_dim_1"], trained_names)
        self.assertEqual(3.0, inferred[0][1])

        count_data, count_names = sklearn_vectorization.apply(log, ngram_range=(0, 2))
        self.assertEqual(2, len(count_data))
        self.assertTrue(any(" >> " in name for name in count_names))
        sparse, _ = sklearn_vectorization.apply(
            log, binary=True, parameters={"return_sparse": True}
        )
        self.assertEqual(2, sparse.shape[0])
        tfidf, tfidf_names = sklearn_vectorization.apply_tfidf(log)
        self.assertEqual(2, len(tfidf))
        self.assertTrue(tfidf_names)
        self.assertEqual(([], []), sklearn_vectorization.apply(EventLog()))
        self.assertEqual([], sklearn_vectorization._ngrams(["A"], (0, 0)))

        net, initial, final = self._sequence_net()
        resolved = petri_encoding.get_log_and_model(
            log,
            {"net": net, "initial_marking": initial, "final_marking": final},
        )
        self.assertIs(net, resolved[1])
        resolved_alias = petri_encoding.get_log_and_model(
            log,
            {"petri_net": net, "initial_marking": initial, "final_marking": final},
        )
        self.assertIs(net, resolved_alias[1])
        with self.assertRaises(ValueError):
            petri_encoding.get_log_and_model(log, {"discover_model": False})
        discovered = petri_encoding.get_log_and_model(log)
        self.assertTrue(discovered[1].transitions)

    def test_passed_time_matching_datetime_and_one_variant_conversion(self):
        from pm4py.objects.conversion.log.variants import df_to_event_log_1v
        from pm4py.statistics.passed_time.log.variants import post, pre
        from pm4py.statistics.util import times_bipartite_matching
        from pm4py.util.dt_parsing.variants import dummy

        log = self._timed_log()
        self.assertEqual(1, len(pre.apply(log, "B")["pre"]))
        self.assertEqual(2, len(pre.apply(log, "C")["pre"]))
        self.assertEqual(2, len(post.apply(log, "A")["post"]))
        self.assertEqual(0.0, post.apply(log, "missing")["post_avg_perf"])
        self.assertEqual(
            [(1, 2), (3, 3)],
            sorted(times_bipartite_matching.exact_match_minimum_average([1, 3], [2, 3])),
        )
        parsed_z = dummy.apply("2024-01-02T03:04:05.006Z")
        parsed_plain = dummy.apply("2024-01-02T03:04:05+00:00")
        self.assertEqual(6000, parsed_z.microsecond)
        self.assertEqual(0, parsed_plain.microsecond)

        frame = pd.DataFrame(
            {
                "case:concept:name": ["c1", "c1", "c2", "c2"],
                "concept:name": ["A", "B", "A", "B"],
            }
        )
        converted = df_to_event_log_1v.apply(frame)
        self.assertEqual(1, len(converted))
        self.assertEqual(["A", "B"], [event["concept:name"] for event in converted[0]])

    def test_restricted_coverability_and_ocpn_trace_conversion(self):
        from pm4py.algo.analysis.woflan.graphs.restricted_coverability_graph import (
            restricted_coverability_graph as rcg,
        )
        from pm4py.algo.simulation.playout.ocpn.variants import utils as ocpn_utils
        from pm4py.util import nx_utils

        net = PetriNet("unbounded")
        place = PetriNet.Place("p")
        grow = PetriNet.Transition("grow", "grow")
        net.places.add(place)
        net.transitions.add(grow)
        petri_utils.add_arc_from_to(place, grow, net, weight=1)
        petri_utils.add_arc_from_to(grow, place, net, weight=2)
        graph = rcg.construct_tree(net, Marking({place: 1}))
        self.assertTrue(any(np.inf in graph.nodes[node]["marking"] for node in graph.nodes))

        manual = nx_utils.DiGraph()
        manual.add_node(0, marking=np.array([1]))
        manual.add_node(1, marking=np.array([2]))
        manual.add_edge(0, 1, transition="grow")
        self.assertFalse(rcg.check_if_transition_unique(0, manual, "grow"))
        self.assertTrue(rcg.check_if_transition_unique(0, manual, "other"))
        self.assertTrue(rcg.check_for_smaller_marking(np.array([2]), manual, 0, {0}))
        self.assertFalse(rcg.check_for_smaller_marking(np.array([1]), manual, 0, {0}))

        transitions = [
            PetriNet.Transition("visible", "A"),
            PetriNet.Transition("silent", None),
            PetriNet.Transition("second", "B"),
        ]
        traces = [
            [(0, ("o1",)), (1, ("o1",)), (2, ("o1", "o2"))],
            [(0, ("o1",))],
        ]
        ocel = ocpn_utils.feasible_traces_to_ocel(
            traces, transitions, {"o1": "order", "o2": "item"}, {}
        )
        self.assertEqual(3, len(ocel.events))
        self.assertEqual(2, len(ocel.objects))
        unique = ocpn_utils.feasible_traces_to_ocel(
            traces,
            transitions,
            {"o1": "order", "o2": "item"},
            {"objects_unique_per_trace": True},
        )
        self.assertGreater(len(unique.objects), len(ocel.objects))

    def test_feature_description_rendering_covers_all_labels(self):
        from pm4py.algo.querying.llm.abstractions import log_to_fea_descr

        columns = [
            "@@max_concurrent_activities_general",
            "@@max_concurrent_activities_like_A",
            "event:resource@alice",
            "event:cost",
            "trace:customer@gold",
            "trace:region",
            "succession:concept:name@A#B",
            "@@caseDuration",
            "firstIndexAct@@A",
            "lastIndexAct@@A",
            "startToLastOcc@@A",
            "lastOccToEnd@@A",
            "startToFirstOcc@@A",
            "firstOccToEnd@@A",
            "directPathPerformanceLastOcc@@A##B",
            "indirectPathPerformanceLastOcc@@A##B",
            "resource_workload@@alice",
            "@@work_in_progress",
            "plain_feature",
            "all_zero",
        ]
        frame = pd.DataFrame({column: [1.0, 2.0, 0.0] for column in columns})
        frame["all_zero"] = 0.0
        text = log_to_fea_descr.textual_abstraction_from_fea_df(frame)
        self.assertIn("Given the following features", text)
        self.assertIn("Maximum Number of Concurrent Events", text)
        self.assertIn("Directly-Follows Paths Throughput", text)
        self.assertNotIn("all_zero", text)
        short = log_to_fea_descr.textual_abstraction_from_fea_df(
            frame, {"include_header": False, "max_len": 1}
        )
        self.assertEqual("\n", short)
        as_dict = log_to_fea_descr.dct_abstraction_from_fea_df(frame)
        self.assertIn("plain_feature", as_dict)
        self.assertNotIn("all_zero", as_dict)

    def test_ocel_parent_reference_and_date_graph_helpers(self):
        from pm4py.objects.ocel.obj import OCEL
        from pm4py.objects.ocel.util import parent_children_ref
        from pm4py.visualization.graphs.util import common
        from pm4py.visualization.graphs.variants import dates

        timestamp = pd.Timestamp("2024-01-01T08:00:00Z")
        ocel = OCEL(
            events=pd.DataFrame(
                [{"ocel:eid": "e1", "ocel:activity": "create", "ocel:timestamp": timestamp}]
            ),
            objects=pd.DataFrame(
                [
                    {"ocel:oid": "child-1", "ocel:type": "item"},
                    {"ocel:oid": "parent-1", "ocel:type": "order"},
                ]
            ),
            relations=pd.DataFrame(
                [
                    {"ocel:eid": "e1", "ocel:activity": "create", "ocel:timestamp": timestamp, "ocel:oid": "child-1", "ocel:type": "item"},
                    {"ocel:eid": "e1", "ocel:activity": "create", "ocel:timestamp": timestamp, "ocel:oid": "parent-1", "ocel:type": "order"},
                ]
            ),
        )
        enriched = parent_children_ref.apply(ocel, "item", "order")
        self.assertEqual("parent-1", enriched.objects.loc[0, "orderID"])
        enriched.objects.loc[0, "orderID"] = None
        enriched = parent_children_ref.apply(enriched, "item", "order")
        self.assertEqual("parent-1", enriched.objects.loc[0, "orderID"])

        first = dates.apply_plot(
            [1, 2, 3],
            [3, 2, 1],
            {"format": "png", "title": "Linear", "x_axis": "x", "y_axis": "y", "pylot_plot_kwargs": {"color": "red"}},
        )
        second = dates.apply_semilogx([1, 10, 100], [1, 2, 3], {"format": "png", "title": "Log"})
        try:
            self.assertTrue(common.serialize(first))
            self.assertTrue(common.serialize(second))
            with mock.patch.object(common.constants, "DEFAULT_ENABLE_VISUALIZATIONS_VIEW", True), mock.patch.object(
                common.vis_utils, "check_visualization_inside_jupyter", return_value=False
            ), mock.patch.object(common.vis_utils, "open_opsystem_image_viewer") as viewer:
                common.view(first)
                viewer.assert_called_once_with(first)
        finally:
            for path in (first, second):
                if os.path.exists(path):
                    os.unlink(path)

    def test_gateway_map_loop_normalization_and_token_generators(self):
        from pm4py.algo.discovery.split_miner.dtypes.gateway_map import (
            GatewayMap,
            _MultipleTokenGen,
            _SingleTokenGen,
            _remove_join_split,
        )
        from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph

        empty = WorkingGraph()
        empty.add_node("start", node_id="s")
        empty.add_node("end", node_id="e")
        empty.start_id, empty.end_id = "s", "e"
        self.assertFalse(GatewayMap(empty).build())

        joint = WorkingGraph()
        for kind, node in (("task", "s1"), ("task", "s2"), ("or", "g"), ("task", "t1"), ("task", "t2")):
            joint.add_node(kind, node_id=node, label=node)
        for source, target in (("s1", "g"), ("s2", "g"), ("g", "t1"), ("g", "t2")):
            joint.add_edge(source, target)
        _remove_join_split(joint)
        self.assertEqual(1, len(joint.out_edges["g"]))

        wg = WorkingGraph()
        for kind, node in (
            ("xor", "a"), ("xor", "b"), ("xor", "c"), ("or", "join"),
            ("xor", "exit"), ("xor", "x1"), ("xor", "x2"), ("task", "task"),
        ):
            wg.add_node(kind, node_id=node, label=node)
        for source, target in (("a", "join"), ("b", "join"), ("c", "join"), ("join", "exit"), ("a", "task")):
            wg.add_edge(source, target)

        gm = GatewayMap(wg)
        for node in ("a", "b", "c", "join", "exit", "x1", "x2"):
            gm._add_gateway(node)
        loop = gm._add_flow("a", "join", "join", "a")
        loop.loop = True
        gm._add_flow("b", "join", "join", "b")
        gm._add_flow("c", "join", "join", "c")
        outgoing = gm._add_flow("join", "exit", "exit", "join")
        self.assertIn("F", repr(outgoing))
        gm._normalize_loop_joins()
        self.assertTrue(gm.loop_joins)

        escape = gm._add_flow("a", "exit", "task", "a")
        gm._place_token_generator(_SingleTokenGen("x1", "a", escape))
        self.assertTrue(wg.in_edges["x1"])

        injection_one = gm._add_flow("b", "join", "join", "b")
        injection_two = gm._add_flow("c", "join", "join", "c")
        injection_one.loop = injection_two.loop = True
        gm._place_multiple_token_generator(
            _MultipleTokenGen({"x1", "x2"}, {injection_one, injection_two}, "join")
        )
        self.assertTrue(wg.in_edges["x2"])

    def test_redis_dictionary_adapter_without_external_server(self):
        from pm4py.streaming.util.dictio.versions import redis as redis_adapter

        class FakeRedis(dict):
            def __init__(self, **connection):
                super().__init__()
                self.connection = connection
                self.flushdb_calls = 0
                self.flushall_calls = 0

            def itervalues(self):
                return iter(self.values())

            def flushdb(self):
                self.flushdb_calls += 1
                self.clear()

            def flushall(self):
                self.flushall_calls += 1
                self.clear()

        redis_module = types.ModuleType("redis")
        connection = FakeRedis()
        redis_module.StrictRedis = mock.Mock(return_value=connection)
        with mock.patch.dict(sys.modules, {"redis": redis_module}):
            dictionary = redis_adapter.apply(
                {"hostname": "redis.local", "port": 6380, "dict_id": 4}
            )
        redis_module.StrictRedis.assert_called_once_with(
            host="redis.local", port=6380, db=4, decode_responses=True
        )
        dictionary["a"] = 1
        dictionary["b"] = 2
        self.assertEqual(["a", "b"], list(dictionary))
        self.assertEqual(["a", "b"], dictionary.keys())
        self.assertEqual([1, 2], list(dictionary.values()))
        self.assertEqual([1, 2], list(dictionary.itervalues()))
        dictionary.flushdb()
        self.assertEqual(1, connection.flushdb_calls)
        dictionary["c"] = 3
        dictionary.flushall()
        self.assertEqual(1, connection.flushall_calls)

    @unittest.skipUnless(
        importlib.util.find_spec("polars"), "polars is not installed"
    )
    def test_polars_service_time_and_log_regex_helpers(self):
        import polars as pl
        from pm4py.objects.log.util import log_regex
        from pm4py.statistics.service_time.polars import get as service_time

        frame = pl.DataFrame(
            {
                "concept:name": ["A", "A", "B"],
                "start": [
                    datetime.datetime(2024, 1, 1, 8, 0),
                    datetime.datetime(2024, 1, 1, 9, 0),
                    datetime.datetime(2024, 1, 1, 10, 0),
                ],
                "end": [
                    datetime.datetime(2024, 1, 1, 8, 1),
                    datetime.datetime(2024, 1, 1, 9, 2),
                    datetime.datetime(2024, 1, 1, 10, 3),
                ],
            }
        ).lazy()
        for measure, expected_a in (("mean", 90.0), ("median", 90.0), ("min", 60.0), ("max", 120.0), ("sum", 180.0)):
            result = service_time.apply(
                frame,
                {
                    service_time.Parameters.START_TIMESTAMP_KEY: "start",
                    service_time.Parameters.TIMESTAMP_KEY: "end",
                    service_time.Parameters.AGGREGATION_MEASURE: measure,
                },
            )
            self.assertEqual(expected_a, result["A"])
        zeros = service_time.apply(
            frame,
            {
                service_time.Parameters.START_TIMESTAMP_KEY: "end",
                service_time.Parameters.TIMESTAMP_KEY: "end",
                service_time.Parameters.BUSINESS_HOURS: True,
            },
        )
        self.assertEqual(0.0, zeros["A"])
        business = service_time.apply(
            frame,
            {
                service_time.Parameters.START_TIMESTAMP_KEY: "start",
                service_time.Parameters.TIMESTAMP_KEY: "end",
                service_time.Parameters.BUSINESS_HOURS: True,
            },
        )
        self.assertGreaterEqual(business["B"], 0.0)

        log = self._timed_log()
        mapping = log_regex.form_encoding_dictio_from_log(log)
        self.assertEqual(3, len(mapping))
        encoded = log_regex.get_encoded_log(log, mapping)
        self.assertEqual(2, len(encoded))
        self.assertEqual(encoded[0], log_regex.get_encoded_trace(log[0], mapping))
        second = EventLog([Trace([Event({"concept:name": "D"}), Event({"concept:name": "A"})])])
        combined_mapping = log_regex.form_encoding_dictio_from_two_logs(log, second)
        self.assertEqual(4, len(combined_mapping))

    def test_temporal_profile_dispatch_diagnostics_and_path_filtering(self):
        from pm4py.algo.conformance.temporal_profile import algorithm as temporal_conformance
        from pm4py.algo.filtering.log.paths import paths_filter

        log = self._timed_log()
        for index, trace in enumerate(log):
            trace.attributes["concept:name"] = f"case-{index}"
        profile = {("A", "B"): (60.0, 1.0), ("A", "C"): (120.0, 1.0)}
        log_result = temporal_conformance.apply(log, profile, {"zeta": 0.5})
        self.assertEqual(2, len(log_result))
        log_diagnostics = temporal_conformance.get_diagnostics_dataframe(log, log_result)
        self.assertIn("case", log_diagnostics.columns)

        rows = []
        for case_index, trace in enumerate(log):
            for event in trace:
                rows.append(
                    {
                        "case:concept:name": f"case-{case_index}",
                        "concept:name": event["concept:name"],
                        "time:timestamp": event["time:timestamp"],
                    }
                )
        frame = pd.DataFrame(rows)
        frame_result = temporal_conformance.apply(frame, profile, {"zeta": 0.5})
        frame_diagnostics = temporal_conformance.get_diagnostics_dataframe(frame, frame_result)
        self.assertEqual(list(log_diagnostics.columns), list(frame_diagnostics.columns))

        self.assertEqual(1, len(paths_filter.apply(log, [("A", "C")])))
        self.assertEqual(1, len(paths_filter.apply(log, [("A", "C")], {"positive": False})))
        self.assertEqual(
            1,
            len(
                paths_filter.apply_performance(
                    log,
                    ("A", "B"),
                    {"min_performance": 50, "max_performance": 70},
                )
            ),
        )
        self.assertTrue(paths_filter.get_paths_from_log(log))
        self.assertEqual("A,B", paths_filter.get_sorted_paths_list({"A,B": 2})[0][0])

    @unittest.skipUnless(
        importlib.util.find_spec("polars"), "polars is not installed"
    )
    def test_dotted_chart_dataframe_and_polars_facade(self):
        import polars as pl
        from pm4py.visualization.dotted_chart import visualizer

        base = pd.Timestamp("2024-01-01T08:00:00Z")
        frame = pd.DataFrame(
            {
                "case:concept:name": ["c1", "c1", "c2"],
                "concept:name": ["A", "B", "A"],
                "time:timestamp": [base, base + pd.Timedelta(minutes=1), base],
            }
        )
        figures = [
            visualizer.apply(
                frame,
                ["time:timestamp", "case:concept:name", "concept:name"],
                parameters={"format": "png"},
            ),
            visualizer.apply(
                pl.from_pandas(frame).lazy(),
                ["time:timestamp", "case:concept:name", "concept:name"],
                parameters={"format": "png"},
            ),
        ]
        try:
            for figure in figures:
                self.assertTrue(visualizer.serialize(figure))
            with mock.patch.object(visualizer.constants, "DEFAULT_ENABLE_VISUALIZATIONS_VIEW", True), mock.patch.object(
                visualizer.vis_utils, "check_visualization_inside_jupyter", return_value=False
            ), mock.patch.object(visualizer.vis_utils, "open_opsystem_image_viewer") as viewer:
                visualizer.view(figures[0])
                viewer.assert_called_once_with(figures[0])
        finally:
            for figure in figures:
                if os.path.exists(figure):
                    os.unlink(figure)


if __name__ == "__main__":
    unittest.main()
