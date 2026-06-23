import importlib.util
import math
import os
import unittest
import warnings

import pandas as pd

from pm4py.algo.transformation.trace_encodings import algorithm as trace_encodings
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.obj import EventLog, Trace, Event
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils


class TraceEncodingsTest(unittest.TestCase):
    def _read_log(self):
        return xes_importer.apply(
            os.path.join("tests", "input_data", "running-example.xes")
        )

    def _abc_log_and_model(self):
        log = EventLog()
        trace = Trace(attributes={"concept:name": "1"})
        for activity in ["A", "B", "C"]:
            trace.append(Event({"concept:name": activity}))
        log.append(trace)

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

        initial_marking = Marking()
        initial_marking[p0] = 1
        final_marking = Marking()
        final_marking[p3] = 1

        return log, net, initial_marking, final_marking

    def _numeric_feature_dataframe(self):
        return pd.DataFrame(
            {
                "case:concept:name": ["c1", "c1", "c1", "c2", "c2"],
                "concept:name": ["A", "B", "C", "A", "B"],
                "time:timestamp": pd.to_datetime(
                    [
                        "2020-01-01 00:00:00",
                        "2020-01-01 00:01:00",
                        "2020-01-01 00:02:00",
                        "2020-01-02 00:00:00",
                        "2020-01-02 00:01:00",
                    ],
                    utc=True,
                ),
                "cost": [1.0, 3.0, 5.0, 10.0, None],
            }
        )

    def test_trace_based_new_package(self):
        log = self._read_log()
        data, feature_names = trace_encodings.apply(
            log,
            variant=trace_encodings.Variants.TRACE_BASED,
            parameters={
                "str_tr_attr": [],
                "str_ev_attr": ["concept:name"],
                "num_tr_attr": [],
                "num_ev_attr": [],
            },
        )

        self.assertEqual(len(log), len(data))
        self.assertTrue(feature_names)

    def test_pandas_numeric_attribute_statistics(self):
        import pm4py

        df = self._numeric_feature_dataframe()
        default_features = pm4py.extract_features_dataframe(
            df,
            str_tr_attr=[],
            num_tr_attr=[],
            str_ev_attr=[],
            num_ev_attr=["cost"],
            include_case_id=True,
        )
        self.assertIn("cost", default_features.columns)
        self.assertNotIn("cost_LAST", default_features.columns)

        features = pm4py.extract_features_dataframe(
            df,
            str_tr_attr=[],
            num_tr_attr=[],
            str_ev_attr=[],
            num_ev_attr=["cost"],
            include_case_id=True,
            enable_numeric_attribute_statistics=True,
        )

        expected_columns = [
            "case:concept:name",
            "cost_LAST",
            "cost_FIRST",
            "cost_MIN",
            "cost_MAX",
            "cost_MEAN",
            "cost_STDEV",
        ]
        self.assertEqual(expected_columns, list(features.columns))
        self.assertNotIn("cost", features.columns)

        by_case = features.set_index("case:concept:name")
        self.assertEqual(5.0, by_case.loc["c1", "cost_LAST"])
        self.assertEqual(1.0, by_case.loc["c1", "cost_FIRST"])
        self.assertEqual(1.0, by_case.loc["c1", "cost_MIN"])
        self.assertEqual(5.0, by_case.loc["c1", "cost_MAX"])
        self.assertEqual(3.0, by_case.loc["c1", "cost_MEAN"])
        self.assertAlmostEqual(
            math.sqrt(8.0 / 3.0), by_case.loc["c1", "cost_STDEV"], places=6
        )
        self.assertEqual(10.0, by_case.loc["c2", "cost_LAST"])
        self.assertEqual(0.0, by_case.loc["c2", "cost_STDEV"])

    @unittest.skipUnless(
        importlib.util.find_spec("polars"), "polars is not installed"
    )
    def test_polars_numeric_attribute_statistics(self):
        import pm4py
        import polars as pl

        lf = pl.LazyFrame(self._numeric_feature_dataframe())
        default_features = pm4py.extract_features_dataframe(
            lf,
            str_tr_attr=[],
            num_tr_attr=[],
            str_ev_attr=[],
            num_ev_attr=["cost"],
            include_case_id=True,
        ).collect()
        self.assertIn("cost", default_features.columns)
        self.assertNotIn("cost_LAST", default_features.columns)

        features = pm4py.extract_features_dataframe(
            lf,
            str_tr_attr=[],
            num_tr_attr=[],
            str_ev_attr=[],
            num_ev_attr=["cost"],
            include_case_id=True,
            enable_numeric_attribute_statistics=True,
        ).collect()

        expected_columns = [
            "case:concept:name",
            "cost_LAST",
            "cost_FIRST",
            "cost_MIN",
            "cost_MAX",
            "cost_MEAN",
            "cost_STDEV",
        ]
        self.assertEqual(expected_columns, features.columns)
        self.assertNotIn("cost", features.columns)

        by_case = {
            row["case:concept:name"]: row for row in features.to_dicts()
        }
        self.assertEqual(5.0, by_case["c1"]["cost_LAST"])
        self.assertEqual(1.0, by_case["c1"]["cost_FIRST"])
        self.assertEqual(1.0, by_case["c1"]["cost_MIN"])
        self.assertEqual(5.0, by_case["c1"]["cost_MAX"])
        self.assertEqual(3.0, by_case["c1"]["cost_MEAN"])
        self.assertAlmostEqual(
            math.sqrt(8.0 / 3.0), by_case["c1"]["cost_STDEV"], places=6
        )
        self.assertEqual(10.0, by_case["c2"]["cost_LAST"])
        self.assertEqual(0.0, by_case["c2"]["cost_STDEV"])

    @unittest.skipUnless(
        importlib.util.find_spec("sklearn"), "scikit-learn is not installed"
    )
    def test_sklearn_baseline_trace_encodings(self):
        log = self._read_log()
        control_flow = {"event_attributes": ["concept:name"]}
        context = {
            "event_attributes": ["concept:name", "org:resource"],
            "trace_attributes": ["creator"],
        }

        data, feature_names = trace_encodings.apply(
            log, variant=trace_encodings.Variants.ONE_HOT, parameters=control_flow
        )
        self.assertEqual(len(log), len(data))
        self.assertIn("register request", feature_names)

        context_data, context_feature_names = trace_encodings.apply(
            log, variant=trace_encodings.Variants.COUNT2VEC, parameters=context
        )
        self.assertEqual(len(log), len(context_data))
        self.assertGreater(len(context_feature_names), len(feature_names))

        _, ngram_features = trace_encodings.apply(
            log,
            variant=trace_encodings.Variants.N_GRAMS,
            parameters={"event_attributes": ["concept:name"], "ngram_range": (2, 2)},
        )
        self.assertTrue(any(" >> " in x for x in ngram_features))

        data, feature_names = trace_encodings.apply(
            log, variant=trace_encodings.Variants.TF_IDF, parameters=control_flow
        )
        self.assertEqual(len(log), len(data))
        self.assertIn("register request", feature_names)

    def test_optional_embedding_variants_are_registered(self):
        self.assertEqual(
            trace_encodings.Variants.WORD2VEC.value.__name__.split(".")[-1],
            "word2vec",
        )
        self.assertEqual(
            trace_encodings.Variants.DOC2VEC.value.__name__.split(".")[-1],
            "doc2vec",
        )
        self.assertEqual(
            trace_encodings.Variants.BERT.value.__name__.split(".")[-1],
            "bert",
        )

    def test_pm_based_trace_encodings(self):
        log, net, initial_marking, final_marking = self._abc_log_and_model()
        parameters = {
            "net": net,
            "initial_marking": initial_marking,
            "final_marking": final_marking,
            "show_progress_bar": False,
        }

        data, feature_names = trace_encodings.apply(
            log, variant=trace_encodings.Variants.TOKEN_REPLAY, parameters=parameters
        )
        self.assertEqual([1.0, 1.0], data[0][:2])
        self.assertIn("@@token_replay_fitness", feature_names)

        data, feature_names = trace_encodings.apply(
            log, variant=trace_encodings.Variants.ALIGNMENTS, parameters=parameters
        )
        self.assertEqual([1.0, 1.0, 0.0], data[0][:3])
        self.assertIn("@@alignment_cost", feature_names)

    def test_legacy_log_to_features_warns_and_delegates(self):
        log = self._read_log()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            from pm4py.algo.transformation.log_to_features import (
                algorithm as log_to_features,
            )

            data, feature_names = log_to_features.apply(
                log,
                variant=log_to_features.Variants.TRACE_BASED,
                parameters={
                    "str_tr_attr": [],
                    "str_ev_attr": ["concept:name"],
                    "num_tr_attr": [],
                    "num_ev_attr": [],
                },
            )

        self.assertEqual(len(log), len(data))
        self.assertTrue(feature_names)
        self.assertTrue(
            any("deprecated" in str(x.message) for x in caught)
        )

    def test_legacy_to_embeddings_warns_on_import(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            from pm4py.algo.transformation.to_embeddings import (
                algorithm as to_embeddings,
            )

        self.assertEqual(
            ["CASES_TRANSFORMERS", "EVENTS_TRANSFORMERS"],
            [x.name for x in to_embeddings.Variants],
        )
        self.assertTrue(
            any("deprecated" in str(x.message) for x in caught)
        )


if __name__ == "__main__":
    unittest.main()
