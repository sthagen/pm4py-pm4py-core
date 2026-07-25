import copy
import io
import os
import tempfile
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from pm4py.objects.conversion.log.variants import to_event_stream
from pm4py.objects.log.obj import Event, EventLog, EventStream, Trace, XESExtension
from pm4py.objects.log.util import (
    dataframe_utils,
    df_extra_utils,
    get_log_encoded,
    pandas_log_wrapper,
)
from pm4py.objects.ocel.importer.csv.variants import ocel20
from pm4py.util import constants, pandas_utils, xes_constants


class SerializationLogUtilsCoverageTest(unittest.TestCase):
    def setUp(self):
        self.case = constants.CASE_CONCEPT_NAME
        self.activity = xes_constants.DEFAULT_NAME_KEY
        self.timestamp = xes_constants.DEFAULT_TIMESTAMP_KEY
        self.frame = pd.DataFrame(
            {
                self.case: ["c1", "c1", "c2"],
                self.activity: ["a", "b", "a"],
                self.timestamp: pd.to_datetime(
                    [
                        "2024-01-01T00:00:02Z",
                        "2024-01-01T00:00:05Z",
                        "2024-01-01T00:00:10Z",
                    ],
                    utc=True,
                ),
                "start": pd.to_datetime(
                    [
                        "2024-01-01T00:00:01Z",
                        "2024-01-01T00:00:03Z",
                        "2024-01-01T00:00:08Z",
                    ],
                    utc=True,
                ),
                "case:customer": ["gold", "gold", "silver"],
            }
        )

    def test_log_objects_sequence_copy_hash_and_equality_contracts(self):
        self.assertEqual(XESExtension.Time.prefix, "time")
        self.assertTrue(XESExtension.Time.uri.endswith("time.xesext"))

        first = Event({"a": 1, "nested": {"x": 2}})
        same = copy.copy(first)
        deep = copy.deepcopy(first)
        self.assertEqual(first, same)
        self.assertEqual(hash(first), hash(same))
        deep["nested"]["x"] = 3
        self.assertEqual(first["nested"]["x"], 2)
        del same["nested"]
        self.assertNotEqual(first, same)

        metadata = dict(
            attributes={"name": "s"},
            extensions={"time": {}},
            globals={"event": {}},
            classifiers={"activity": ["a"]},
            properties={"p": 1},
        )
        stream = EventStream([first, Event({"a": 2})], **metadata)
        self.assertEqual(list(reversed(stream))[0]["a"], 2)
        self.assertEqual(stream.index(first, 0, 2), 0)
        self.assertEqual(stream.count(first), 1)
        stream[1] = Event({"a": 3})
        stream.properties = {"p": 2}
        self.assertIn("a", str(stream))
        self.assertIsInstance(hash(stream), int)
        shallow_stream = copy.copy(stream)
        deep_stream = copy.deepcopy(stream)
        self.assertEqual(stream, shallow_stream)
        self.assertEqual(stream, deep_stream)

        for attribute, value in (
            ("_attributes", {"different": True}),
            ("_extensions", {"different": True}),
            ("_omni", {"different": True}),
            ("_classifiers", {"different": True}),
        ):
            candidate = copy.copy(stream)
            setattr(candidate, attribute, value)
            self.assertNotEqual(stream, candidate)
        self.assertNotEqual(stream, EventStream([]))
        candidate = copy.copy(stream)
        candidate[0] = Event({"a": 99})
        self.assertNotEqual(stream, candidate)

        empty = Trace(attributes={"case": "empty"})
        one = Trace([first], attributes={"case": "one"}, properties={"x": 1})
        trace = Trace([first, Event({"a": 3})], attributes={"case": "two"})
        self.assertIn("events", repr(empty))
        self.assertIn("events", repr(one))
        self.assertIn("..", repr(trace))
        trace.properties = {"updated": True}
        self.assertEqual(list(reversed(trace))[0]["a"], 3)
        self.assertEqual(trace.index(first, 0, 2), 0)
        self.assertEqual(trace.count(first), 1)
        trace[1] = Event({"a": 4})
        trace.insert(1, Event({"a": 2}))
        self.assertIsInstance(hash(trace), int)
        self.assertEqual(trace, copy.copy(trace))
        self.assertEqual(trace, copy.deepcopy(trace))
        self.assertNotEqual(trace, Trace([]))
        self.assertNotEqual(trace, Trace(list(trace), attributes={"case": "other"}))
        changed = copy.copy(trace)
        changed[0] = Event({"a": 99})
        self.assertNotEqual(trace, changed)

        for log in (EventLog([]), EventLog([one]), EventLog([one, trace])):
            self.assertIsInstance(repr(log), str)
        log = EventLog([one, trace], **metadata)
        self.assertEqual(log, copy.copy(log))
        self.assertEqual(log, copy.deepcopy(log))
        self.assertIsInstance(hash(log), int)
        self.assertNotEqual(log, EventLog([]))
        for attribute, value in (
            ("_attributes", {"different": True}),
            ("_extensions", {"different": True}),
            ("_omni", {"different": True}),
            ("_classifiers", {"different": True}),
        ):
            candidate = copy.copy(log)
            setattr(candidate, attribute, value)
            self.assertNotEqual(log, candidate)
        candidate = copy.copy(log)
        candidate[0] = Trace([Event({"a": "changed"})])
        self.assertNotEqual(log, candidate)

    def test_pandas_log_wrappers_cover_index_slice_iteration_and_lists(self):
        wrapped = pandas_log_wrapper.PandasLogWrapper(self.frame)
        self.assertEqual(len(wrapped), 2)
        self.assertEqual(len(wrapped[0]), 2)
        self.assertEqual(len(wrapped[-1]), 1)
        self.assertEqual(len(wrapped[0:2]), 2)
        self.assertEqual(len(list(wrapped)), 2)
        self.assertEqual(len(wrapped._list), 2)

        trace = wrapped[0]
        self.assertEqual(trace.attributes["customer"], "gold")
        self.assertEqual(trace[0][self.activity], "a")
        self.assertEqual(trace[-1][self.activity], "b")
        self.assertEqual(len(trace[0:1]), 1)
        self.assertEqual(len(list(trace)), 2)
        self.assertEqual(len(trace._list), 2)

        default_trace = pandas_log_wrapper.PandasTraceWrapper(
            self.frame.iloc[:1].reset_index(drop=True)
        )
        default_log = pandas_log_wrapper.PandasLogWrapper(self.frame)
        self.assertEqual(len(default_trace), 1)
        self.assertEqual(len(default_log), 2)

    def test_extra_dataframe_columns_and_log_encoding(self):
        enriched = df_extra_utils.compute_extra_columns(
            self.frame.copy(),
            {df_extra_utils.Parameters.START_TIMESTAMP_KEY: "start"},
        )
        self.assertEqual(enriched.loc[0, "@@case_throughput"], 4.0)
        self.assertEqual(enriched.loc[0, "@@case_start_year"], "2024")
        self.assertEqual(enriched.loc[0, "@@case_end_month"], "M01")

        enriched_again = df_extra_utils.compute_extra_columns(
            enriched,
            {
                df_extra_utils.Parameters.START_TIMESTAMP_KEY: "start",
                df_extra_utils.Parameters.COMPUTE_EXTRA_TEMPORAL_FEATURES: False,
            },
        )
        self.assertIn("@@count", enriched_again)

        log = EventLog(
            [
                Trace(
                    [Event({"act": "a", "cost": 1}), Event({"act": "b"})],
                    attributes={"customer": "gold"},
                ),
                Trace([Event({"act": "c", "cost": 3})], attributes={}),
            ]
        )
        matrix, columns = get_log_encoded.get_log_encoded(
            log,
            trace_attributes=["customer"],
            event_attributes=["act", "cost"],
        )
        self.assertEqual(matrix.shape, (2, 5))
        self.assertEqual(len(columns), 5)
        prefixes, prefix_columns = get_log_encoded.get_log_encoded(
            log,
            trace_attributes=["customer"],
            event_attributes=["act"],
            concatenate=True,
        )
        self.assertEqual(prefixes.shape[0], 3)
        self.assertGreaterEqual(len(prefix_columns), 2)

    def test_dataframe_utils_conversion_sampling_and_artificial_boundaries(self):
        partitioned = dataframe_utils.insert_partitioning(self.frame.copy(), 2)
        self.assertIn("@@partitioning", partitioned)
        partitioned = dataframe_utils.insert_partitioning(
            partitioned,
            3,
            {
                dataframe_utils.Parameters.CASE_INDEX_KEY: constants.DEFAULT_CASE_INDEX_KEY,
                dataframe_utils.Parameters.PARTITION_COLUMN: "part",
            },
        )
        self.assertIn("part", partitioned)

        legacy = pd.DataFrame({"caseAAAconceptAAAname": ["c"], "xAAAy": [1]})
        self.assertIn("case:concept:name", dataframe_utils.legacy_parquet_support(legacy))

        class Table:
            def to_pydict(self):
                return {
                    "caseAAAconceptAAAname": ["c1", "c1"],
                    "conceptAAAname": ["a", "b"],
                    "timeAAAtimestamp": [
                        pd.Timestamp("2024-01-01T00:00:00Z"),
                        pd.Timestamp("2024-01-01T00:00:01Z"),
                    ],
                }

        stream = dataframe_utils.table_to_stream(Table())
        self.assertEqual(len(stream), 2)
        self.assertEqual(len(dataframe_utils.table_to_log(Table())), 1)
        self.assertIsNone(dataframe_utils.convert_timestamp_columns_in_df(None))
        converted = dataframe_utils.convert_timestamp_columns_in_df(
            pd.DataFrame({"date": ["2024-01-01T00:00:00Z"], "bad": ["not-a-date"]})
        )
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(converted["date"]))

        deterministic = dataframe_utils.sample_dataframe(
            self.frame,
            {
                dataframe_utils.Parameters.DETERMINISTIC: True,
                dataframe_utils.Parameters.MAX_NO_CASES: 1,
            },
        )
        # The point sampler intentionally retains both extremes.
        self.assertEqual(deterministic[self.case].nunique(), 2)
        with mock.patch.object(dataframe_utils.random, "shuffle") as shuffle:
            dataframe_utils.sample_dataframe(
                self.frame,
                {dataframe_utils.Parameters.MAX_NO_CASES: 1},
            )
            shuffle.assert_called_once()

        bounded = dataframe_utils.insert_artificial_start_end(self.frame)
        self.assertEqual(len(bounded), len(self.frame) + 4)
        self.assertEqual(bounded.attrs, self.frame.attrs)
        extremes = dataframe_utils.insert_artificial_start_end(
            self.frame,
            {dataframe_utils.Parameters.USE_EXTREMES_TIMESTAMP: True},
        )
        self.assertEqual(len(extremes), len(bounded))

        class SetFriendlyFrame(pd.DataFrame):
            @property
            def _constructor(self):
                return SetFriendlyFrame

            def __getitem__(self, key):
                if isinstance(key, set):
                    key = list(key)
                return super().__getitem__(key)

        activity_table, case_table = dataframe_utils.dataframe_to_activity_case_table(
            SetFriendlyFrame(self.frame)
        )
        self.assertEqual(len(case_table), 2)
        self.assertEqual(len(activity_table), 3)

    def test_pandas_utils_pandas_and_polars_paths(self):
        positioned = pandas_utils.insert_feature_activity_position_in_trace(
            self.frame.copy()
        )
        self.assertEqual(positioned.loc[0, "@@position_a"], 0)
        self.assertTrue(np.isnan(positioned.loc[1, "@@position_a"]))

        rates = pandas_utils.insert_case_arrival_finish_rate(self.frame.copy())
        self.assertIn("@@arrival_rate", rates)
        self.assertIn("@@finish_rate", rates)
        durations = pandas_utils.insert_case_service_waiting_time(
            self.frame.copy(), start_timestamp_column="start"
        )
        self.assertEqual(durations.loc[0, "@@service_time"], 3.0)
        self.assertEqual(durations.loc[0, "@@sojourn_time"], 4.0)

        class ToList:
            def to_list(self):
                return [1, 2]

        class Iterable:
            def __iter__(self):
                return iter((3, 4))

        self.assertEqual(pandas_utils.format_unique(ToList()), [1, 2])
        self.assertEqual(pandas_utils.format_unique(Iterable()), [3, 4])
        self.assertEqual(len(pandas_utils.instantiate_dataframe({"x": [1]})), 1)
        self.assertEqual(len(pandas_utils.instantiate_dataframe_from_dict({"x": [1]})), 1)
        self.assertEqual(
            len(pandas_utils.instantiate_dataframe_from_records([{"x": 1}])), 1
        )
        self.assertIsNotNone(pandas_utils.get_grouper(key=self.timestamp, freq="D"))
        self.assertAlmostEqual(
            pandas_utils.get_total_seconds(
                pd.Series(pd.to_timedelta(["1 day 00:00:01.000001001"]))
            ).iloc[0],
            86401.000001001,
        )

        class BadValues:
            @property
            def values(self):
                raise TypeError("not pandas")

            def to_numpy(self):
                return np.array([2_000_000_000])

        self.assertEqual(pandas_utils.convert_to_seconds(BadValues()), [2.0])

        with mock.patch.object(
            pandas_utils.constants, "TEST_CUDF_DATAFRAMES_ENVIRONMENT", True
        ):
            parsed = pandas_utils.read_csv(io.StringIO("x\n1\n"), encoding="utf-8")
            pandas_utils.dataframe_column_string_to_datetime(["2024-01-01"])
        self.assertEqual(parsed.iloc[0, 0], 1)
        self.assertEqual(len(pandas_utils.concat([parsed, parsed])), 2)
        self.assertEqual(len(pandas_utils.merge(parsed, parsed, on="x")), 1)

        valid = self.frame[[self.case, self.activity, self.timestamp]].copy()
        pandas_utils.check_pandas_dataframe_columns(
            valid,
            activity_key=self.activity,
            case_id_key=self.case,
            timestamp_key=self.timestamp,
            start_timestamp_key=self.timestamp,
        )
        invalid_frames = [
            (valid[[self.case, self.activity]], {}),
            (pd.DataFrame({"a": [1], "b": [2], "c": pd.to_datetime(["2024-01-01"])}), {}),
            (valid.assign(**{self.timestamp: ["x", "y", "z"]}), {}),
            (valid, {"case_id_key": "missing"}),
            (valid.assign(**{self.case: [1, 2, 3]}), {"case_id_key": self.case}),
            (valid.assign(**{self.case: ["c", None, "d"]}), {"case_id_key": self.case}),
            (valid, {"activity_key": "missing"}),
            (valid.assign(**{self.activity: [1, 2, 3]}), {"activity_key": self.activity}),
            (valid.assign(**{self.activity: ["a", None, "b"]}), {"activity_key": self.activity}),
            (valid, {"timestamp_key": "missing"}),
            (valid.assign(**{self.timestamp: ["x", "y", "z"]}), {"timestamp_key": self.timestamp}),
            (valid.assign(**{self.timestamp: [pd.Timestamp("2024-01-01"), pd.NaT, pd.Timestamp("2024-01-02")]}), {"timestamp_key": self.timestamp}),
            (valid, {"start_timestamp_key": "missing"}),
            (valid.assign(start=["x", "y", "z"]), {"start_timestamp_key": "start"}),
            (valid.assign(start=[pd.Timestamp("2024-01-01"), pd.NaT, pd.Timestamp("2024-01-02")]), {"start_timestamp_key": "start"}),
        ]
        for frame, kwargs in invalid_frames:
            with self.subTest(kwargs=kwargs), self.assertRaises(Exception):
                pandas_utils.check_pandas_dataframe_columns(frame, **kwargs)

        self.assertEqual(
            pandas_utils.get_traces(valid, self.case, self.activity),
            [("a", "b"), ("a",)],
        )
        self.assertEqual(pandas_utils.get_attribute_values_count(valid, self.activity)["a"], 2)
        self.assertEqual(pandas_utils.df_row_count(valid), 3)
        pivot = pandas_utils.get_pivot_timestamp_distribution(
            valid.copy(), frequency_alias="D"
        )
        self.assertIn("@@evcount_2024-01-01", pivot)

        try:
            import polars as pl
        except ImportError:
            return
        lazy = pl.from_pandas(self.frame).lazy()
        self.assertEqual(len(pandas_utils.to_dict_records(lazy)), 3)
        self.assertEqual(len(pandas_utils.to_dict_index(lazy)), 3)
        indexed = pandas_utils.insert_index(lazy, column_name="idx").collect()
        self.assertEqual(indexed["idx"].to_list(), [0, 1, 2])
        case_indexed = pandas_utils.insert_case_index(lazy, column_name="cidx").collect()
        self.assertEqual(case_indexed["cidx"].to_list(), [0, 0, 1])
        event_indexed = pandas_utils.insert_ev_in_tr_index(lazy, column_name="eidx").collect()
        self.assertEqual(event_indexed["eidx"].to_list(), [0, 1, 0])
        lazy_positioned = pandas_utils.insert_feature_activity_position_in_trace(lazy).collect()
        self.assertIn("@@position_a", lazy_positioned.columns)
        lazy_rates = pandas_utils.insert_case_arrival_finish_rate(lazy).collect()
        self.assertIn("@@finish_rate", lazy_rates.columns)
        lazy_durations = pandas_utils.insert_case_service_waiting_time(
            lazy, start_timestamp_column="start"
        ).collect()
        self.assertIn("@@waiting_time", lazy_durations.columns)
        pandas_utils.check_pandas_dataframe_columns(
            lazy,
            activity_key=self.activity,
            case_id_key=self.case,
            timestamp_key=self.timestamp,
            start_timestamp_key="start",
        )
        self.assertEqual(
            pandas_utils.get_traces(lazy, self.case, self.activity),
            [("a", "b"), ("a",)],
        )
        self.assertEqual(pandas_utils.get_attribute_values_count(lazy, self.activity)["a"], 2)
        with self.assertRaises(Exception):
            pandas_utils.get_attribute_values_count(lazy, "missing")
        self.assertEqual(pandas_utils.df_row_count(lazy), 3)

    def test_event_stream_conversion_postprocess_compress_extensions_and_case_data(self):
        frame = pd.DataFrame(
            {
                "concept:name": ["a", "a"],
                "org:resource": ["r", "r"],
                "optional": [np.nan, None],
            }
        )
        frame.attrs[constants.PARAMETER_CONSTANT_CASEID_KEY] = "case-id"
        frame.attrs["kept"] = 1
        stream = to_event_stream.apply(
            frame,
            {
                to_event_stream.Parameters.STREAM_POST_PROCESSING: True,
                to_event_stream.Parameters.COMPRESS: True,
            },
        )
        self.assertEqual(len(stream), 2)
        self.assertNotIn("optional", stream[0])
        self.assertNotIn(constants.PARAMETER_CONSTANT_CASEID_KEY, stream.properties)
        self.assertIn("Organizational", stream.extensions)

        new_converter = getattr(
            to_event_stream, "__transform_dataframe_to_event_stream_new"
        )
        new_stream = new_converter(frame, stream_post_processing=True, compress=True)
        self.assertEqual(len(new_stream), 2)

        event_log = EventLog(
            [Trace([Event({"a": 1})], attributes={"customer": "gold"})],
            attributes={"name": "log"},
        )
        with_cases = to_event_stream.apply(event_log)
        self.assertEqual(with_cases[0]["case:customer"], "gold")
        without_cases = to_event_stream.apply(
            event_log,
            {
                to_event_stream.Parameters.INCLUDE_CASE_ATTRIBUTES: False,
                to_event_stream.Parameters.DEEP_COPY: False,
            },
        )
        self.assertIn(constants.CASE_ATTRIBUTE_GLUE, without_cases[0])
        marker = object()
        self.assertIs(to_event_stream.apply(marker), marker)

    def test_ocel20_csv_helpers_type_inference_and_validation(self):
        self.assertTrue(ocel20._is_empty(None))

        class AmbiguousNa:
            def __str__(self):
                return "value"

        self.assertFalse(ocel20._is_empty(AmbiguousNa()))
        self.assertEqual(ocel20._strip_value("  x  "), "x")
        self.assertEqual(ocel20._split_entries("a/b"), ["a", "b"])
        entries = ocel20._split_entries('a#q{"url":"x/y","quoted":"a\\\"/b"}/b')
        self.assertEqual(len(entries), 2)
        self.assertEqual(ocel20._split_reference(' o1 # q {"n":1}'), ("o1", "q", {"n": 1}))

        invalid_references = ['#q', 'a/b', 'a#bad#q', 'a{"nested":{"x":1}}']
        for reference in invalid_references:
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                ocel20._split_reference(reference)
        with self.assertRaises(ValueError):
            ocel20._validate_attribute_values({"nested": []})

        registry = {}
        ocel20._register_object_type(registry, "o1", "order")
        with self.assertRaises(ValueError):
            ocel20._register_object_type(registry, "o1", "item")
        self.assertEqual(len(ocel20._instantiate_dataframe([], ["a"])), 0)
        self.assertEqual(len(ocel20._instantiate_dataframe([{"a": 1}], ["a"])), 1)

        self.assertEqual(ocel20._parse_timestamp(""), "")
        with self.assertRaises(ValueError):
            ocel20._parse_timestamp("2024-01-01T00:00:00")
        with self.assertRaises(ValueError):
            ocel20._parse_timestamp("2024-99-99T00:00:00Z")
        self.assertEqual(ocel20._parse_timestamp_column(pd.Series(["", ""])), ["", ""])
        with self.assertRaises(ValueError):
            ocel20._parse_timestamp_column(pd.Series(["2024-01-01T00:00:00"]))
        with self.assertRaises(ValueError):
            ocel20._parse_timestamp_column(pd.Series(["2024-99-99T00:00:00Z"]))

        attrs = {}
        ocel20._collect_object_attribute(attrs, "o1", "amount", "", 1, 0)
        self.assertEqual(ocel20._attribute_sort_key(attrs[("o1", "amount")][0])[0], 0)
        self.assertEqual(
            ocel20._attribute_sort_key(
                (1, pd.Timestamp("2024-01-01T00:00:00Z"), 2)
            )[0],
            1,
        )
        self.assertIsNone(ocel20._try_parse_integer([True]))
        self.assertEqual(ocel20._try_parse_integer([1, "2"]), [1, 2])
        self.assertIsNone(ocel20._try_parse_float([True]))
        self.assertIsNone(ocel20._try_parse_float(["x"]))
        self.assertEqual(ocel20._try_parse_boolean([True, "false"]), [True, False])
        self.assertIsNone(ocel20._try_parse_boolean([1]))
        self.assertIsNone(ocel20._try_parse_timestamp_values([1]))
        self.assertIsNone(ocel20._try_parse_timestamp_values(["not-a-date"]))
        self.assertEqual(ocel20._infer_values(["", None]), ["", None])
        self.assertEqual(ocel20._infer_values(["1", "2"]), [1, 2])
        self.assertEqual(ocel20._infer_values(["1.5", "2.0"]), [1.5, 2.0])
        self.assertEqual(ocel20._infer_values(["true", "false"]), [True, False])
        timestamps = ocel20._infer_values(["2024-01-01T00:00:00Z"])
        self.assertIsInstance(timestamps[0], pd.Timestamp)
        self.assertEqual(ocel20._infer_values(["hello"]), ["hello"])
        empty = pd.DataFrame()
        self.assertIs(ocel20._infer_column_type(empty, "x"), empty)

        objects = pd.DataFrame(
            {"id": ["o1", "i1"], "type": ["order", "item"], "value": ["1", "true"]}
        )
        changes = pd.DataFrame(
            {"id": ["o1"], "type": ["order"], "value": ["2"]}
        )
        converted_objects, converted_changes = ocel20._infer_object_attribute_types(
            objects, changes, "type", {"id", "type"}
        )
        self.assertEqual(converted_objects.loc[0, "value"], 1)
        self.assertEqual(converted_changes.loc[0, "value"], 2)
        unchanged_objects, unchanged_changes = ocel20._infer_object_attribute_types(
            empty, empty, "type", set()
        )
        self.assertIs(unchanged_objects, empty)
        self.assertIs(unchanged_changes, empty)

    def test_ocel20_csv_apply_empty_and_rejection_paths(self):
        cases = [
            ({"activity": ["o2o"]}, "source"),
            ({"id": ["e1"], "activity": ["act"], "timestamp": [""]}, "invalid"),
            ({"timestamp": ["2024-01-01T00:00:00Z"], "ot:item": ["i1"]}, "attributes"),
            ({"ot:item": ["i1#q"]}, "qualifier"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            empty_path = os.path.join(directory, "empty.csv")
            pd.DataFrame({"other": []}).to_csv(empty_path, index=False)
            empty = ocel20.apply(empty_path)
            self.assertEqual(len(empty.events), 0)

            for index, (data, label) in enumerate(cases):
                path = os.path.join(directory, "%s.csv" % index)
                pd.DataFrame(data).to_csv(path, index=False)
                with self.subTest(label=label), self.assertRaises(ValueError):
                    ocel20.apply(path)


if __name__ == "__main__":
    unittest.main()
