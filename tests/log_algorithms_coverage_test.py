import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import pandas as pd

from pm4py.algo.discovery.correlation_mining.variants import (
    classic_split,
    trace_based as correlation_trace_based,
)
from pm4py.algo.evaluation.precision.variants import automaton_after_align
from pm4py.algo.filtering.log.paths import paths_filter as log_paths_filter
from pm4py.algo.filtering.pandas.paths import paths_filter as pandas_paths_filter
from pm4py.algo.transformation.trace_encodings.variants import (
    event_based,
    temporal,
    temporal_lazy,
)
from pm4py.objects.log import obj as log_obj
from pm4py.objects.log.obj import Event, EventLog, Trace
from pm4py.objects.log.util import get_prefixes, interval_lifecycle
from pm4py.objects.log.util import log as log_utils
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import petri_utils
from pm4py.statistics.chaotic_activities.variants import niek_sidorova


class LogAlgorithmsCoverageTest(unittest.TestCase):
    @staticmethod
    def _log():
        base = datetime(2024, 1, 1, 8, tzinfo=timezone.utc)
        log = EventLog(attributes={"source": "synthetic"})
        for case_id, activities in (
            ("1", ("A", "B", "C")),
            ("2", ("A", "C")),
            ("3", ("B", "A", "B")),
        ):
            trace = Trace(attributes={"concept:name": case_id, "group": "g"})
            for index, activity in enumerate(activities):
                end = base + timedelta(days=int(case_id) - 1, minutes=5 * index)
                trace.append(
                    Event(
                        {
                            "concept:name": activity,
                            "time:timestamp": end,
                            "start_timestamp": end - timedelta(minutes=2),
                            "org:resource": f"r{index % 2}",
                            "cost": float(index + 1),
                            "shared": case_id,
                        }
                    )
                )
            log.append(trace)
        return log

    @staticmethod
    def _series_net():
        net = PetriNet("series")
        p0, p1, p2 = (PetriNet.Place(name) for name in ("p0", "p1", "p2"))
        a = PetriNet.Transition("a", "A")
        b = PetriNet.Transition("b", "B")
        net.places.update({p0, p1, p2})
        net.transitions.update({a, b})
        for source, target in ((p0, a), (a, p1), (p1, b), (b, p2)):
            petri_utils.add_arc_from_to(source, target, net)
        return net, Marking({p0: 1}), Marking({p2: 1})

    def test_prefix_and_projection_utilities(self):
        log = self._log()
        prefixes = get_prefixes.get_prefixes_from_log(log, 2)
        self.assertEqual([2, 2, 2], [len(trace) for trace in prefixes])
        self.assertIs(log[1], prefixes[1])

        all_prefixes, changes = get_prefixes.get_log_with_log_prefixes(log)
        self.assertEqual(16, len(all_prefixes))
        self.assertEqual([[5, 5, 5], [9, 9], [15, 15, 15]], changes)

        until_b, durations = get_prefixes.get_log_traces_until_activity(log, "B")
        self.assertEqual(1, len(until_b))
        self.assertEqual([300.0], durations)
        future, explicit = get_prefixes.get_log_traces_until_activity(
            log,
            "C",
            parameters={"duration": "cost", "use_future_attributes": True},
        )
        self.assertEqual([3.0, 2.0], explicit)
        self.assertEqual(2, len(future))
        sublogs, activities = get_prefixes.get_log_traces_to_activities(log, ["B", "C"])
        self.assertEqual(len(sublogs), len(activities))
        self.assertTrue(set(activities).issubset({"B", "C"}))

        self.assertEqual(["A", "B", "C"], log_utils.get_event_labels(log, "concept:name"))
        self.assertEqual(3, log_utils.get_event_labels_counted(log, "concept:name")["A"])
        variants, variant_map = log_utils.get_trace_variants(log)
        self.assertEqual(3, len(variants))
        self.assertEqual(3, sum(map(len, variant_map.values())))
        self.assertEqual(["A", "B", "C"], log_utils.project_traces(log)[0])
        self.assertEqual("A", log_utils.project_traces(log, ["concept:name"])[0][0]["concept:name"])

        lifted = log_utils.derive_and_lift_trace_attributes_from_event_attributes(
            self._log(), ignore={"concept:name", "time:timestamp", "start_timestamp", "org:resource", "cost"}
        )
        self.assertEqual("1", lifted[0].attributes["shared"])
        self.assertNotIn("shared", lifted[0][0])
        retained = log_utils.derive_and_lift_trace_attributes_from_event_attributes(
            self._log(),
            ignore={"concept:name", "time:timestamp", "start_timestamp", "org:resource", "cost"},
            retain_on_event_level=True,
        )
        self.assertIn("shared", retained[0][0])

        with mock.patch.object(EventLog, "Event", Event, create=True):
            artificial = log_utils.add_artficial_start_and_end(EventLog([Trace([Event({"concept:name": "A"})])]))
        self.assertEqual(["[start>", "A", "[end]"], [x["concept:name"] for x in artificial[0]])

    def test_lifecycle_interval_roundtrip_and_lead_cycle_time(self):
        base = datetime(2024, 1, 1, 8, tzinfo=timezone.utc)
        lifecycle = EventLog(
            [
                Trace(
                    [
                        Event({"concept:name": "A", "lifecycle:transition": "start", "concept:instance": "1", "time:timestamp": base}),
                        Event({"concept:name": "B", "lifecycle:transition": "complete", "time:timestamp": base + timedelta(minutes=3)}),
                        Event({"concept:name": "A", "lifecycle:transition": "complete", "concept:instance": "1", "time:timestamp": base + timedelta(minutes=5)}),
                    ],
                    attributes={"concept:name": "case"},
                )
            ]
        )
        interval = interval_lifecycle.to_interval(lifecycle, parameters={"business_hours": True})
        self.assertEqual("interval", interval.attributes["PM4PY_TYPE"])
        self.assertEqual(2, len(interval[0]))
        self.assertEqual(300.0, interval[0][0]["@@duration"])
        self.assertIn("@@approx_bh_duration", interval[0][0])
        self.assertIs(interval, interval_lifecycle.to_interval(interval))

        lifecycle_again = interval_lifecycle.to_lifecycle(interval)
        self.assertEqual(4, len(lifecycle_again[0]))
        self.assertIs(lifecycle_again, interval_lifecycle.to_lifecycle(lifecycle_again))
        enriched = interval_lifecycle.assign_lead_cycle_time(interval)
        self.assertIn("@@approx_bh_partial_cycle_time", enriched[0][-1])
        self.assertIn("@approx_bh_ratio_cycle_lead_time", enriched[0][-1])
        self.assertIsNone(interval_lifecycle.to_interval(None))
        self.assertIsNone(interval_lifecycle.to_lifecycle(None))

    def test_event_and_temporal_encodings(self):
        log = self._log()
        names = event_based.extract_all_ev_features_names_from_log(
            log,
            str_ev_attr=["concept:name", "org:resource"],
            num_ev_attr=["cost"],
        )
        data, selected = event_based.extract_features(log, names)
        self.assertEqual((3, 3, len(names)), data.shape)
        self.assertEqual(names, selected)
        explicit, explicit_names = event_based.apply(log, parameters={"feature_names": names[:2]})
        self.assertEqual(names[:2], explicit_names)
        self.assertEqual((3, 3, 2), explicit.shape)

        dataframe = pd.DataFrame(
            [
                {
                    "case:concept:name": trace.attributes["concept:name"],
                    **event,
                }
                for trace in log
                for event in trace
            ]
        )
        temporal_features = temporal.apply(
            dataframe,
            parameters={"grouper_freq": "D", "start_timestamp_column": "start_timestamp"},
        )
        self.assertEqual(3, len(temporal_features))
        self.assertIn("number_of_cases", temporal_features.columns)

        self.assertEqual("2w", temporal_lazy._freq_to_polars_duration("2W-MON"))
        self.assertEqual("1m", temporal_lazy._freq_to_polars_duration("MIN"))
        with self.assertRaises(ValueError):
            temporal_lazy._freq_to_polars_duration("")
        with self.assertRaises(ValueError):
            temporal_lazy._freq_to_polars_duration("17")
        with self.assertRaises(ValueError):
            temporal_lazy._freq_to_polars_duration("fortnight")
        if importlib.util.find_spec("polars") is not None:
            with self.assertRaises(TypeError):
                temporal_lazy.apply(dataframe)

    def test_chaotic_activity_metrics(self):
        traces = [["A", "B", "C"], ["A", "C"], ["B", "A", "B"]]
        metrics = niek_sidorova.chaotic_metrics(traces)
        self.assertEqual({"A", "B", "C"}, {x["activity"] for x in metrics})
        self.assertGreater(niek_sidorova.total_entropy(traces), 0)
        counts, pairs = niek_sidorova._pair_counts(traces)
        before, after = niek_sidorova._entropy_vectors("A", set(counts), counts, pairs, alpha=0.5)
        self.assertEqual(len(counts) + 1, len(before))
        self.assertEqual(len(before), len(after))
        self.assertGreaterEqual(niek_sidorova._entropy([0.5, 0.5, 0]), 0)
        self.assertEqual(3, len(niek_sidorova.apply(self._log(), parameters={"alpha": 0.5})))

    def test_correlation_mining_matrix_and_split_variants(self):
        log = self._log()
        traces, grouped, activities, counter = correlation_trace_based.preprocess_log(log)
        self.assertEqual(3, len(traces))
        ps_matrix, duration_matrix = correlation_trace_based.get_PS_duration_matrix(activities, grouped)
        self.assertEqual((3, 3), ps_matrix.shape)
        self.assertEqual((3, 3), duration_matrix.shape)
        dfg, performance = correlation_trace_based.resolve_lp_get_dfg(
            ps_matrix, duration_matrix, activities, counter
        )
        self.assertIsInstance(dfg, dict)
        self.assertIsInstance(performance, dict)

        dataframe = pd.DataFrame(
            [{"case:concept:name": trace.attributes["concept:name"], **event} for trace in log for event in trace]
        )
        dfg2, performance2 = correlation_trace_based.apply(
            dataframe, parameters={"start_timestamp_key": "start_timestamp"}
        )
        self.assertIsInstance(dfg2, dict)
        self.assertIsInstance(performance2, dict)
        split_dfg, split_performance = classic_split.apply(
            log, parameters={"sample_size": 3, "start_timestamp_key": "start_timestamp"}
        )
        self.assertIsInstance(split_dfg, dict)
        self.assertIsInstance(split_performance, dict)

    def test_log_and_dataframe_path_filters(self):
        log = self._log()
        self.assertEqual(2, len(log_paths_filter.apply(log, [("A", "B")])))
        self.assertEqual(1, len(log_paths_filter.apply(log, [("A", "B")], parameters={"positive": False})))
        self.assertEqual(
            2,
            len(
                log_paths_filter.apply_performance(
                    log, ("A", "B"), parameters={"min_performance": 299, "max_performance": 301}
                )
            ),
        )
        self.assertEqual(1, len(log_paths_filter.apply_performance(log, ("A", "B"), parameters={"positive": False})))
        paths = log_paths_filter.get_paths_from_log(log)
        a_to_b = next(key for key in paths if key.startswith("A") and key.endswith("B"))
        self.assertEqual(2, paths[a_to_b])
        sorted_paths = log_paths_filter.get_sorted_paths_list(paths)
        self.assertGreaterEqual(log_paths_filter.get_paths_threshold(sorted_paths, 0.5), 1)

        dataframe = pd.DataFrame(
            [{"case:concept:name": trace.attributes["concept:name"], **event} for trace in log for event in trace]
        )
        positive = pandas_paths_filter.apply(dataframe, [("A", "B")])
        negative = pandas_paths_filter.apply(dataframe, [("A", "B")], parameters={"positive": False})
        self.assertEqual({"1", "3"}, set(positive["case:concept:name"]))
        self.assertEqual({"2"}, set(negative["case:concept:name"]))
        perf = pandas_paths_filter.apply_performance(
            dataframe, ("A", "B"), parameters={"min_performance": 299, "max_performance": 301}
        )
        self.assertEqual({"1", "3"}, set(perf["case:concept:name"]))

    def test_alignment_automaton_precision_helpers_and_algorithm(self):
        alignment = [
            (("A", "a"), ("A", "A")),
            ((">>", "tau"), (">>", None)),
            ((">>", ">>"), ("X", ">>")),
            (("B", "b"), ("B", "B")),
        ]
        self.assertEqual(["A", "B"], automaton_after_align._extract_model_sequence(alignment))
        self.assertEqual(["a", "b"], automaton_after_align._extract_model_sequence(alignment, use_task_ids=True))
        with self.assertRaises(ValueError):
            automaton_after_align._get_alignment_model_part(("bad",))
        next_by_prefix, prefix_weight = {}, {}
        automaton_after_align._update_prefix_stats(["A", "B", "C"], 2, next_by_prefix, prefix_weight)
        automaton_after_align._update_prefix_stats(["A"], 1, next_by_prefix, prefix_weight)
        self.assertEqual(2, prefix_weight[("A",)])

        net, initial_marking, final_marking = self._series_net()
        fitting_log = EventLog(
            [
                Trace([Event({"concept:name": "A"}), Event({"concept:name": "B"})]),
                Trace([Event({"concept:name": "A"}), Event({"concept:name": "B"})]),
            ]
        )
        precision = automaton_after_align.apply(
            fitting_log,
            net,
            initial_marking,
            final_marking,
            parameters={"show_progress_bar": False, "debug_level": 1},
        )
        self.assertAlmostEqual(1.0, precision)

        unsound = PetriNet("unsound")
        place = PetriNet.Place("p")
        unsound.places.add(place)
        with self.assertRaises(ValueError):
            automaton_after_align.apply(EventLog(), unsound, Marking({place: 1}), Marking())


if __name__ == "__main__":
    unittest.main()
