import datetime
import importlib.util
import os
import unittest
import warnings
from unittest import mock

import pandas as pd

import pm4py
from pm4py.objects.log.obj import EventLog, EventStream
from pm4py.util import constants


class FacadeUtilsCoverageTest(unittest.TestCase):
    @staticmethod
    def _path(*parts):
        return os.path.join(os.path.dirname(__file__), "input_data", *parts)

    @classmethod
    def setUpClass(cls):
        cls.dataframe = pm4py.read_xes(
            cls._path("running-example.xes"), variant="iterparse"
        )
        cls.log = pm4py.convert_to_event_log(cls.dataframe)

    def test_filtering_facade_for_dataframe_and_legacy_log(self):
        variant = next(iter(pm4py.get_variants_as_tuples(self.dataframe)))
        for obj in (self.dataframe, self.log):
            for level in ("cases", "events"):
                self.assertIsNotNone(
                    pm4py.filter_log_relative_occurrence_event_attribute(
                        obj, 0.1, level=level
                    )
                )
            self.assertIsNotNone(pm4py.filter_start_activities(obj, ["register request"]))
            self.assertIsNotNone(pm4py.filter_start_activities(obj, ["missing"], retain=False))
            self.assertIsNotNone(pm4py.filter_end_activities(obj, ["pay compensation"]))
            self.assertIsNotNone(pm4py.filter_end_activities(obj, ["missing"], retain=False))
            for level in ("event", "case"):
                self.assertIsNotNone(
                    pm4py.filter_event_attribute_values(
                        obj, "concept:name", ["check ticket"], level=level
                    )
                )
            trace_key = "case:creator" if isinstance(obj, pd.DataFrame) else "creator"
            self.assertIsNotNone(
                pm4py.filter_trace_attribute_values(
                    obj, trace_key, ["Fluxicon Nitro"]
                )
            )
            self.assertIsNotNone(pm4py.filter_variants(obj, [variant]))
            self.assertIsNotNone(
                pm4py.filter_directly_follows_relation(
                    obj, [("register request", "examine casually")]
                )
            )
            for retain in (True, False):
                self.assertIsNotNone(
                    pm4py.filter_eventually_follows_relation(
                        obj,
                        [
                            ("register request", "decide"),
                            ("check ticket", "pay compensation"),
                        ],
                        retain=retain,
                    )
                )

            for mode in (
                "events",
                "traces_contained",
                "traces_intersecting",
                "traces_starting_in",
                "traces_starting_in_exclude",
                "traces_completing_in",
                "traces_completing_in_exclude",
                "unknown",
            ):
                self.assertIsNotNone(
                    pm4py.filter_time_range(
                        obj,
                        "2010-12-29 00:00:00",
                        "2011-01-25 00:00:00",
                        mode=mode,
                    )
                )
            self.assertIsNotNone(pm4py.filter_between(obj, "register request", "decide"))
            self.assertIsNotNone(pm4py.filter_case_size(obj, 1, 20))
            self.assertIsNotNone(pm4py.filter_case_performance(obj, 0, 10**9))
            self.assertIsNotNone(pm4py.filter_activities_rework(obj, "check ticket", 2))
            self.assertIsNotNone(
                pm4py.filter_paths_performance(
                    obj, ("check ticket", "decide"), 0, 10**9, keep=False
                )
            )
            self.assertIsNotNone(pm4py.filter_variants_top_k(obj, 2))
            self.assertIsNotNone(
                pm4py.filter_variants_by_coverage_percentage(obj, 0.1)
            )
            self.assertIsNotNone(
                pm4py.filter_prefixes(
                    obj, "check ticket", strict=False, first_or_last="last"
                )
            )
            self.assertIsNotNone(
                pm4py.filter_suffixes(
                    obj, "check ticket", strict=False, first_or_last="last"
                )
            )
            self.assertIsNotNone(
                pm4py.filter_four_eyes_principle(
                    obj, "check ticket", "decide", keep_violations=True
                )
            )
            self.assertIsNotNone(
                pm4py.filter_activity_done_different_resources(
                    obj, "check ticket", keep_violations=False
                )
            )
            self.assertIsNotNone(
                pm4py.filter_trace_segments(
                    obj, [["...", "check ticket", "decide", "..."]], positive=False
                )
            )

        # Exercise the documented compatibility warning/default-level path.
        from pm4py import utils

        utils.Shared.FILTERING_LEVEL_WARNING_SHOWN = False
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self.assertIsNone(
                pm4py.filter_event_attribute_values(
                    self.dataframe, "concept:name", ["decide"]
                )
            )
        self.assertTrue(caught)

    def test_dataframe_formatting_rebase_classifier_and_sampling(self):
        raw = pd.DataFrame(
            {
                "cid": ["2", "1", None],
                "act": ["B", "A", "drop"],
                "ts": ["2020-01-02", "2020-01-01", "2020-01-03"],
                "start": ["2020-01-01", "2019-12-31", "2020-01-02"],
                "case:concept:name": ["old", "old", "old"],
                "concept:name": ["old", "old", "old"],
                "time:timestamp": ["2021-01-01"] * 3,
            }
        )
        with mock.patch.object(constants, "SHOW_INTERNAL_WARNINGS", True):
            with warnings.catch_warnings(record=True) as caught:
                formatted = pm4py.format_dataframe(
                    raw,
                    case_id="cid",
                    activity_key="act",
                    timestamp_key="ts",
                    start_timestamp_key="start",
                )
        self.assertEqual(2, len(formatted))
        self.assertTrue(caught)
        self.assertIn("@@case_index", formatted.columns)
        for removed_column in ("cid", "act", "ts"):
            # Source columns remain available while canonical columns are rebased.
            self.assertIn(removed_column, formatted.columns)

        for missing in ("cid", "act", "ts"):
            broken = raw.drop(columns=[missing])
            with self.assertRaises(Exception):
                pm4py.format_dataframe(
                    broken, case_id="cid", activity_key="act", timestamp_key="ts"
                )

        rebased_log = pm4py.rebase(pm4py.convert_to_event_log(formatted))
        rebased_stream = pm4py.rebase(pm4py.convert_to_event_stream(formatted))
        self.assertIsInstance(rebased_log, EventLog)
        self.assertIsInstance(rebased_stream, EventStream)

        log = pm4py.parse_event_log_string(
            ["A,B", "A,C"], return_legacy_log_object=True
        )
        log.classifiers["pair"] = ["concept:name", "org:resource"]
        for trace in log:
            for event in trace:
                event["org:resource"] = "r"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pm4py.set_classifier(log, "pair")
            df = pm4py.convert_to_dataframe(log)
            pm4py.set_classifier(df, ["concept:name", "org:resource"])
            with self.assertRaises(Exception):
                pm4py.set_classifier(object(), "concept:name")
        self.assertIn("@@classifier", log[0][0])

        self.assertEqual(2, len(pm4py.project_on_event_attribute(log)))
        self.assertEqual(2, len(pm4py.project_on_event_attribute(df)))
        self.assertEqual(1, len(pm4py.sample_cases(log, 1)))
        self.assertTrue(len(pm4py.sample_cases(df, 1)))
        self.assertEqual(1, len(pm4py.sample_events(pm4py.convert_to_event_stream(df), 1)))
        self.assertEqual(1, len(pm4py.sample_events(df, 1)))

    @unittest.skipUnless(
        importlib.util.find_spec("polars"), "polars is not installed"
    )
    def test_polars_formatting_and_projection(self):
        import polars as pl

        lazy = pl.DataFrame(
            {
                "cid": ["2", "1", None],
                "act": ["B", "A", "drop"],
                "ts": ["2020-01-02", "2020-01-01", "2020-01-03"],
                "start": ["2020-01-01", "2019-12-31", "2020-01-02"],
            }
        ).lazy()
        formatted = pm4py.format_dataframe(
            lazy,
            case_id="cid",
            activity_key="act",
            timestamp_key="ts",
            start_timestamp_key="start",
        )
        self.assertEqual(2, formatted.collect().height)
        self.assertEqual([["A"], ["B"]], pm4py.project_on_event_attribute(formatted))
        self.assertEqual(2, pm4py.rebase(formatted).collect().height)
        with self.assertRaises(Exception):
            pm4py.format_dataframe(lazy.drop("act"), case_id="cid", activity_key="act", timestamp_key="ts")

    def test_ocel_and_dfg_filtering_facades(self):
        ocel = pm4py.read_ocel2_json(
            self._path("ocel", "ocel20_example.jsonocel")
        )
        ocel.events[ocel.event_timestamp] = pd.to_datetime(
            ocel.events[ocel.event_timestamp], utc=True
        )
        event_id = ocel.events.iloc[0][ocel.event_id_column]
        activity = ocel.events.iloc[0][ocel.event_activity]
        object_id = ocel.objects.iloc[0][ocel.object_id_column]
        object_type = ocel.objects.iloc[0][ocel.object_type_column]
        timestamp = ocel.events.iloc[0][ocel.event_timestamp]

        calls = (
            lambda: pm4py.filter_ocel_event_attribute(
                ocel, ocel.event_activity, [activity], positive=False
            ),
            lambda: pm4py.filter_ocel_object_attribute(
                ocel, ocel.object_type_column, [object_type], positive=False
            ),
            lambda: pm4py.filter_ocel_object_types_allowed_activities(
                ocel, {object_type: [activity]}
            ),
            lambda: pm4py.filter_ocel_object_per_type_count(ocel, {object_type: 1}),
            lambda: pm4py.filter_ocel_start_events_per_object_type(ocel, object_type),
            lambda: pm4py.filter_ocel_end_events_per_object_type(ocel, object_type),
            lambda: pm4py.filter_ocel_events_timestamp(
                ocel,
                timestamp - datetime.timedelta(days=1),
                timestamp + datetime.timedelta(days=1),
            ),
            lambda: pm4py.filter_ocel_object_types(ocel, [object_type], positive=False),
            lambda: pm4py.filter_ocel_object_types(ocel, [object_type], level=2),
            lambda: pm4py.filter_ocel_objects(ocel, [object_id], positive=False),
            lambda: pm4py.filter_ocel_objects(ocel, [object_id], level=2),
            lambda: pm4py.filter_ocel_events(ocel, [event_id], positive=False),
            lambda: pm4py.filter_ocel_activities_connected_object_type(ocel, object_type),
            lambda: pm4py.filter_ocel_cc_object(ocel, object_id, return_conn_comp=True),
            lambda: pm4py.filter_ocel_cc_object(ocel, "missing", conn_comp=[]),
            lambda: pm4py.filter_ocel_cc_length(ocel, 1, 1000),
            lambda: pm4py.filter_ocel_cc_otype(ocel, object_type),
            lambda: pm4py.filter_ocel_cc_otype(ocel, object_type, positive=False),
            lambda: pm4py.filter_ocel_cc_activity(ocel, activity),
        )
        for call in calls:
            self.assertIsNotNone(call())

        dfg, starts, ends = pm4py.discover_dfg(self.dataframe)
        self.assertEqual(3, len(pm4py.filter_dfg_activities_percentage(dfg, starts, ends, 0.5)))
        self.assertEqual(3, len(pm4py.filter_dfg_paths_percentage(dfg, starts, ends, 0.5)))


if __name__ == "__main__":
    unittest.main()
