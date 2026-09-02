import json
import importlib.util
import os
import shutil
import sqlite3
import unittest
import zipfile

import pandas as pd

import pm4py
from pm4py.objects.ocel.obj import OCEL


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(TESTS_DIR)
OUTPUT_DIR = os.path.join(TESTS_DIR, "test_output_data")
EXAMPLE_CSV = os.path.join(REPO_DIR, "Order Management OCEL.csv")
EXAMPLE_XML = os.path.join(REPO_DIR, "Order Management OCEL.xml.gz")
PARQUET_ENGINE_AVAILABLE = any(
    importlib.util.find_spec(package) is not None
    for package in ("pyarrow", "fastparquet")
)


class Ocel2CsvTest(unittest.TestCase):
    def _build_typed_ocel(self):
        event_time = pd.Timestamp("2024-01-01T10:00:00Z")
        change_time = pd.Timestamp("2024-01-02T10:00:00Z")
        return OCEL(
            events=pd.DataFrame(
                [
                    {
                        "ocel:eid": "e1",
                        "ocel:activity": "typed event",
                        "ocel:timestamp": event_time,
                        "label": "001",
                        "count": 5,
                        "ratio": 1.25,
                        "active": True,
                        "observed": event_time,
                    }
                ]
            ),
            objects=pd.DataFrame(
                [
                    {
                        "ocel:oid": "o1",
                        "ocel:type": "typed object",
                        "label": "base",
                        "count": 7,
                        "ratio": 2.5,
                        "active": False,
                        "observed": event_time,
                    }
                ]
            ),
            relations=pd.DataFrame(
                [
                    {
                        "ocel:eid": "e1",
                        "ocel:activity": "typed event",
                        "ocel:timestamp": event_time,
                        "ocel:oid": "o1",
                        "ocel:type": "typed object",
                        "ocel:qualifier": "",
                    }
                ]
            ),
            object_changes=pd.DataFrame(
                [
                    {
                        "ocel:oid": "o1",
                        "ocel:type": "typed object",
                        "ocel:timestamp": change_time,
                        "ocel:field": "active",
                        "active": True,
                    }
                ]
            ),
        )

    def _build_bundled_ocel(self, source):
        dataframe = pd.DataFrame(
            [
                {
                    "id": "create_o1",
                    "activity": "create order",
                    "timestamp": "2024-01-01T10:00:00+0000",
                    "cost": "5",
                    "ot:orders": 'o1#order{"amount":10}',
                    "ot:sales person": 'Alice#seller{"role":"manager"}',
                },
                {
                    "id": "pay_o1",
                    "activity": "pay/order",
                    "timestamp": "2024-01-02T10:00:00+0000",
                    "cost": "7",
                    "ot:orders": "o1#order",
                    "ot:sales person": "Alice#seller",
                },
                {
                    "id": "o1",
                    "activity": "o2o",
                    "timestamp": "",
                    "cost": "",
                    "ot:orders": "",
                    "ot:sales person": "Alice#accountable",
                },
                {
                    "id": "",
                    "activity": "",
                    "timestamp": "",
                    "cost": "",
                    "ot:orders": "o2",
                    "ot:sales person": "",
                },
                {
                    "id": "",
                    "activity": "",
                    "timestamp": "2024-01-03T10:00:00+0000",
                    "cost": "",
                    "ot:orders": "",
                    "ot:sales person": 'Alice{"role":"lead"}',
                },
            ]
        )
        dataframe.to_csv(source, index=False)
        return pm4py.read_ocel2_csv(source)

    def _assert_same_counts(self, imported, ocel):
        self.assertEqual(len(imported.events), len(ocel.events))
        self.assertEqual(len(imported.objects), len(ocel.objects))
        self.assertEqual(len(imported.relations), len(ocel.relations))
        self.assertEqual(len(imported.o2o), len(ocel.o2o))
        self.assertEqual(len(imported.object_changes), len(ocel.object_changes))
        self.assertEqual(
            set(imported.objects[imported.object_id_column]),
            set(ocel.objects[ocel.object_id_column]),
        )

    def test_ocel2_csv_import_export_roundtrip(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_compact_source.ocel.csv")
        exported = os.path.join(OUTPUT_DIR, "ocel2_compact_exported.ocel.csv")

        dataframe = pd.DataFrame(
            [
                {
                    "id": "create_o1",
                    "activity": "create order",
                    "timestamp": "2024-01-01T10:00:00+0000",
                    "cost": "5",
                    "ot:employees": "Alice#employee",
                    "ot:items": 'i1#item{"price":3}',
                    "ot:orders": 'o1#order{"amount":10}',
                },
                {
                    "id": "pay_o1",
                    "activity": "pay order",
                    "timestamp": "2024-01-02T10:00:00+0000",
                    "cost": "",
                    "ot:employees": "",
                    "ot:items": "i1#item",
                    "ot:orders": "o1#order",
                },
                {
                    "id": "o1",
                    "activity": "o2o",
                    "timestamp": "",
                    "cost": "",
                    "ot:employees": "",
                    "ot:items": "i1#contains",
                    "ot:orders": "",
                },
                {
                    "id": "",
                    "activity": "",
                    "timestamp": "2024-01-03T10:00:00+0000",
                    "cost": "",
                    "ot:employees": 'Alice{"role":"manager"}',
                    "ot:items": "",
                    "ot:orders": "",
                },
                {
                    "id": "",
                    "activity": "",
                    "timestamp": "2024-01-04T10:00:00+0000",
                    "cost": "",
                    "ot:employees": 'Alice{"role":"lead"}',
                    "ot:items": "",
                    "ot:orders": "",
                },
            ]
        )

        try:
            dataframe.to_csv(source, index=False)

            ocel = pm4py.read_ocel2(source)
            self.assertEqual(len(ocel.events), 2)
            self.assertEqual(len(ocel.objects), 3)
            self.assertEqual(len(ocel.relations), 5)
            self.assertEqual(len(ocel.o2o), 1)
            self.assertEqual(len(ocel.object_changes), 4)
            self.assertTrue(ocel.objects["price"].isna().all())
            self.assertTrue(ocel.objects["amount"].isna().all())
            self.assertEqual(
                set(ocel.objects[ocel.object_type_column].unique()),
                {"employees", "items", "orders"},
            )

            pm4py.write_ocel2(ocel, exported)
            imported = pm4py.read_ocel2(exported)

            self.assertEqual(len(imported.events), len(ocel.events))
            self.assertEqual(len(imported.objects), len(ocel.objects))
            self.assertEqual(len(imported.relations), len(ocel.relations))
            self.assertEqual(len(imported.o2o), len(ocel.o2o))
            self.assertEqual(len(imported.object_changes), len(ocel.object_changes))
        finally:
            for path in (source, exported):
                if os.path.exists(path):
                    os.remove(path)

    def test_ocel2_csv_revised_constraints(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_revised_constraints.ocel.csv")
        exported = os.path.join(OUTPUT_DIR, "ocel2_revised_constraints_exported.ocel.csv")

        dataframe = pd.DataFrame(
            [
                {
                    "id": " create_o1 ",
                    "activity": " create order ",
                    "timestamp": " 2024-01-01T10:00:00+0000 ",
                    "cost": "5",
                    "ot:items": " i1 # ordered item ",
                    "ot:orders": ' o1 # ordered {"priority":"high"} ',
                },
                {
                    "id": "",
                    "activity": "",
                    "timestamp": "",
                    "cost": "",
                    "ot:items": 'i2{"price":"7"}',
                    "ot:orders": "",
                },
                {
                    "id": "o1",
                    "activity": "O2O",
                    "timestamp": "2024-01-02T10:00:00+0000",
                    "cost": "",
                    "ot:items": 'i2#contains{"price":"9"}',
                    "ot:orders": "",
                },
                {
                    "id": "",
                    "activity": "",
                    "timestamp": "2024-01-03T10:00:00+0000",
                    "cost": "",
                    "ot:items": 'i1{"price":"11"}',
                    "ot:orders": "",
                },
            ]
        )

        try:
            dataframe.to_csv(source, index=False)

            ocel = pm4py.read_ocel2_csv(source)

            self.assertEqual(len(ocel.events), 1)
            self.assertEqual(len(ocel.objects), 3)
            self.assertEqual(len(ocel.relations), 2)
            self.assertEqual(len(ocel.o2o), 1)
            self.assertEqual(len(ocel.object_changes), 3)
            self.assertIn("o1", set(ocel.objects[ocel.object_id_column]))
            self.assertIn("i2", set(ocel.objects[ocel.object_id_column]))
            self.assertEqual(
                ocel.events.iloc[0][ocel.event_id_column],
                "create_o1",
            )
            self.assertEqual(
                ocel.events.iloc[0][ocel.event_activity],
                "create order",
            )
            self.assertEqual(
                set(ocel.objects[ocel.object_type_column].unique()),
                {"items", "orders"},
            )

            pm4py.write_ocel2_csv(ocel, exported)
            exported_dataframe = pd.read_csv(exported, dtype=str).fillna("")
            declaration_rows = exported_dataframe[
                (exported_dataframe["id"] == "")
                & (exported_dataframe["activity"] == "")
                & (exported_dataframe["timestamp"] == "")
            ]
            self.assertEqual(len(declaration_rows), 1)
            self.assertIn('i2{"price":7}', set(declaration_rows["ot:items"]))
            event_rows = exported_dataframe[exported_dataframe["id"] == "create_o1"]
            self.assertNotIn("{", event_rows.iloc[0]["ot:orders"])

            imported = pm4py.read_ocel2_csv(exported)
            self.assertEqual(len(imported.events), len(ocel.events))
            self.assertEqual(len(imported.objects), len(ocel.objects))
            self.assertEqual(len(imported.relations), len(ocel.relations))
            self.assertEqual(len(imported.o2o), len(ocel.o2o))
            self.assertEqual(len(imported.object_changes), len(ocel.object_changes))

            ocel.events[ocel.event_timestamp] = ocel.events[
                ocel.event_timestamp
            ].dt.tz_localize(None)
            ocel.relations[ocel.event_timestamp] = ocel.relations[
                ocel.event_timestamp
            ].dt.tz_localize(None)
            ocel.object_changes[ocel.event_timestamp] = ocel.object_changes[
                ocel.event_timestamp
            ].dt.tz_localize(None)
            pm4py.write_ocel2_csv(ocel, exported)
            imported = pm4py.read_ocel2_csv(exported)
            self.assertEqual(len(imported.events), len(ocel.events))
        finally:
            for path in (source, exported):
                if os.path.exists(path):
                    os.remove(path)

    def test_ocel2_csv_rejects_undeclared_o2o_source(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_undeclared_o2o.csv")
        dataframe = pd.DataFrame(
            [
                {
                    "id": "o1",
                    "activity": "o2o",
                    "timestamp": "",
                    "ot:items": "i1#contains",
                },
            ]
        )

        try:
            dataframe.to_csv(source, index=False)
            with self.assertRaises(ValueError):
                pm4py.read_ocel2_csv(source)
        finally:
            if os.path.exists(source):
                os.remove(source)

    def test_ocel2_csv_rejects_o2o_attributes_without_timestamp(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_o2o_attrs_without_timestamp.csv")
        dataframe = pd.DataFrame(
            [
                {
                    "id": "",
                    "activity": "",
                    "timestamp": "",
                    "ot:orders": "o1",
                    "ot:items": "",
                },
                {
                    "id": "o1",
                    "activity": "o2o",
                    "timestamp": "",
                    "ot:orders": "",
                    "ot:items": 'i1#contains{"weight":2}',
                },
            ]
        )

        try:
            dataframe.to_csv(source, index=False)
            with self.assertRaises(ValueError):
                pm4py.read_ocel2_csv(source)
        finally:
            if os.path.exists(source):
                os.remove(source)

    def test_ocel2_csv_rejects_timestamp_without_timezone(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_timestamp_without_timezone.csv")
        dataframe = pd.DataFrame(
            [
                {
                    "id": "e1",
                    "activity": "a",
                    "timestamp": "2024-01-01T10:00:00",
                    "ot:orders": "o1",
                },
            ]
        )

        try:
            dataframe.to_csv(source, index=False)
            with self.assertRaises(ValueError):
                pm4py.read_ocel2_csv(source)
        finally:
            if os.path.exists(source):
                os.remove(source)

    def test_ocel2_csv_requires_core_columns_and_valid_row_shapes(self):
        missing_header = os.path.join(OUTPUT_DIR, "ocel2_missing_header.ocel.csv")
        invalid_row = os.path.join(OUTPUT_DIR, "ocel2_invalid_row.ocel.csv")
        try:
            pd.DataFrame([{"id": "e1", "activity": "a"}]).to_csv(
                missing_header, index=False
            )
            with self.assertRaises(ValueError):
                pm4py.read_ocel2_csv(missing_header)

            pd.DataFrame(
                [
                    {
                        "id": "orphan",
                        "activity": "",
                        "timestamp": "",
                        "ot:orders": "o1",
                    }
                ]
            ).to_csv(invalid_row, index=False)
            with self.assertRaises(ValueError):
                pm4py.read_ocel2_csv(invalid_row)
        finally:
            for path in (missing_header, invalid_row):
                if os.path.exists(path):
                    os.remove(path)

    def test_ocel2_csv_rejects_conflicting_same_time_assignments(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_conflicting_changes.ocel.csv")
        dataframe = pd.DataFrame(
            [
                {
                    "id": "",
                    "activity": "",
                    "timestamp": "2024-01-01T10:00:00Z",
                    "ot:orders": 'o1{"amount":1}',
                },
                {
                    "id": "",
                    "activity": "",
                    "timestamp": "2024-01-01T10:00:00+00:00",
                    "ot:orders": 'o1{"amount":2}',
                },
            ]
        )
        try:
            dataframe.to_csv(source, index=False)
            with self.assertRaises(ValueError):
                pm4py.read_ocel2_csv(source)
        finally:
            if os.path.exists(source):
                os.remove(source)

    def test_ocel2_csv_preserves_attribute_whitespace_during_inference(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_attribute_whitespace.ocel.csv")
        dataframe = pd.DataFrame(
            [
                {
                    "id": "e1",
                    "activity": "a",
                    "timestamp": "2024-01-01T10:00:00Z",
                    "amount": " 5 ",
                    "ot:orders": "o1",
                },
                {
                    "id": "",
                    "activity": "",
                    "timestamp": "",
                    "amount": "",
                    "ot:orders": 'o1{"label":" 7 "}',
                },
            ]
        )
        try:
            dataframe.to_csv(source, index=False)
            ocel = pm4py.read_ocel2_csv(source)
            self.assertEqual(ocel.events.iloc[0]["amount"], " 5 ")
            self.assertEqual(ocel.objects.iloc[0]["label"], " 7 ")
        finally:
            if os.path.exists(source):
                os.remove(source)

    def test_ocel2_csv_escapes_special_characters_in_references(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_escaping_source.ocel.csv")
        exported = os.path.join(OUTPUT_DIR, "ocel2_escaping_exported.ocel.csv")
        dataframe = pd.DataFrame(
            [
                {
                    "id": "e1",
                    "activity": "pay/order",
                    "timestamp": "2024-01-01T10:00:00Z",
                    "ot:orders": "o\\/1#with\\#hash",
                    "ot:items": "i\\{1",
                },
                {
                    "id": "o/1",
                    "activity": "o2o",
                    "timestamp": "",
                    "ot:orders": "",
                    "ot:items": "i\\{1#part\\/of",
                },
            ]
        )
        try:
            dataframe.to_csv(source, index=False)
            ocel = pm4py.read_ocel2_csv(source)
            self.assertEqual(
                sorted(ocel.objects[ocel.object_id_column]), ["i{1", "o/1"]
            )
            self.assertEqual(
                sorted(ocel.relations["ocel:qualifier"]), ["", "with#hash"]
            )
            self.assertEqual(ocel.o2o["ocel:qualifier"].tolist(), ["part/of"])

            pm4py.write_ocel2(ocel, exported)
            imported = pm4py.read_ocel2(exported)
            self.assertEqual(
                sorted(imported.objects[imported.object_id_column]), ["i{1", "o/1"]
            )
            self.assertEqual(
                sorted(imported.relations["ocel:qualifier"]), ["", "with#hash"]
            )
            self.assertEqual(imported.o2o["ocel:qualifier"].tolist(), ["part/of"])
        finally:
            for path in (source, exported):
                if os.path.exists(path):
                    os.remove(path)

    def test_ocel2_csv_rejects_invalid_escape_sequences(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_bad_escape.ocel.csv")
        dataframe = pd.DataFrame(
            [
                {
                    "id": "e1",
                    "activity": "a",
                    "timestamp": "2024-01-01T10:00:00Z",
                    "ot:orders": "o\\x1",
                }
            ]
        )
        try:
            dataframe.to_csv(source, index=False)
            with self.assertRaises(ValueError):
                pm4py.read_ocel2_csv(source)
        finally:
            if os.path.exists(source):
                os.remove(source)

    def test_ocel2_csv_numbers_require_canonical_form(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_canonical_numbers.ocel.csv")
        dataframe = pd.DataFrame(
            [
                {
                    "id": "e1",
                    "activity": "a",
                    "timestamp": "2024-01-01T10:00:00Z",
                    "code": "007",
                    "count": "5",
                    "big": "9223372036854775808",
                    "padded": "1.50",
                    "ratio": "1.5",
                    "ot:orders": "o1",
                },
                {
                    "id": "e2",
                    "activity": "a",
                    "timestamp": "2024-01-01T11:00:00Z",
                    "code": "12",
                    "count": "7",
                    "big": "3",
                    "padded": "2.25",
                    "ratio": "2.25",
                    "ot:orders": "o1",
                },
            ]
        )
        try:
            dataframe.to_csv(source, index=False)
            ocel = pm4py.read_ocel2_csv(source)
            events = ocel.events.sort_values(ocel.event_id_column)
            self.assertEqual(events["code"].tolist(), ["007", "12"])
            self.assertEqual(events["count"].tolist(), [5, 7])
            self.assertEqual(
                events["big"].tolist(), ["9223372036854775808", "3"]
            )
            self.assertEqual(events["padded"].tolist(), ["1.50", "2.25"])
            self.assertEqual(events["ratio"].tolist(), [1.5, 2.25])
        finally:
            if os.path.exists(source):
                os.remove(source)

    def test_ocel2_bundle_keeps_time0_attributes_only_in_objects(self):
        bundle_dir = os.path.join(OUTPUT_DIR, "ocel2_time0_bundle")
        event_time = pd.Timestamp("2024-01-01T10:00:00Z")
        epoch = pd.Timestamp("1970-01-01T00:00:00Z")
        change_time = pd.Timestamp("2024-01-02T10:00:00Z")
        ocel = OCEL(
            events=pd.DataFrame(
                [
                    {
                        "ocel:eid": "e1",
                        "ocel:activity": "act",
                        "ocel:timestamp": event_time,
                    }
                ]
            ),
            objects=pd.DataFrame(
                [{"ocel:oid": "o1", "ocel:type": "orders", "amount": 10}]
            ),
            relations=pd.DataFrame(
                [
                    {
                        "ocel:eid": "e1",
                        "ocel:activity": "act",
                        "ocel:timestamp": event_time,
                        "ocel:oid": "o1",
                        "ocel:type": "orders",
                        "ocel:qualifier": "",
                    }
                ]
            ),
            object_changes=pd.DataFrame(
                [
                    {
                        "ocel:oid": "o1",
                        "ocel:type": "orders",
                        "ocel:timestamp": epoch,
                        "ocel:field": "amount",
                        "amount": 10,
                    },
                    {
                        "ocel:oid": "o1",
                        "ocel:type": "orders",
                        "ocel:timestamp": epoch,
                        "ocel:field": "status",
                        "status": "new",
                    },
                    {
                        "ocel:oid": "o1",
                        "ocel:type": "orders",
                        "ocel:timestamp": change_time,
                        "ocel:field": "amount",
                        "amount": 12,
                    },
                ]
            ),
        )
        try:
            pm4py.write_ocel2_bundle(ocel, bundle_dir, storage_format="csv")
            changes_file = os.path.join(
                bundle_dir, "object_changes", "object_changes_orders.csv"
            )
            with open(changes_file, "r", newline="") as file:
                changes_text = file.read()
            self.assertNotIn("1970-01-01", changes_text)

            imported = pm4py.read_ocel2_bundle(bundle_dir)
            self.assertEqual(len(imported.object_changes), 1)
            self.assertEqual(imported.objects["status"].tolist(), ["new"])
            self.assertEqual(imported.objects["amount"].tolist(), [10])

            with open(changes_file, "r", newline="") as file:
                content = file.read()
            content += "o1,1970-01-01T00:00:00+00:00,amount,10,\r\n"
            with open(changes_file, "w", newline="") as file:
                file.write(content)
            with self.assertRaises(ValueError):
                pm4py.read_ocel2_bundle(bundle_dir)
        finally:
            if os.path.isdir(bundle_dir):
                shutil.rmtree(bundle_dir)

    def test_ocel2_csv_writer_uses_canonical_extension(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_extension_source.ocel.csv")
        target = os.path.join(OUTPUT_DIR, "ocel2_extension_target.csv")
        canonical_target = target[:-4] + ".ocel.csv"
        try:
            pd.DataFrame(
                [
                    {
                        "id": "e1",
                        "activity": "a",
                        "timestamp": "2024-01-01T10:00:00Z",
                    }
                ]
            ).to_csv(source, index=False)
            ocel = pm4py.read_ocel2(source)
            pm4py.write_ocel2_csv(ocel, target)
            self.assertTrue(os.path.exists(canonical_target))
            self.assertFalse(os.path.exists(target))
        finally:
            for path in (source, target, canonical_target):
                if os.path.exists(path):
                    os.remove(path)

    def test_ocel2_csv_and_bundle_require_utf8(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_utf8_source.ocel.csv")
        bundle_dir = os.path.join(OUTPUT_DIR, "ocel2_non_utf8_bundle")
        try:
            pd.DataFrame(
                [
                    {
                        "id": "e1",
                        "activity": "a",
                        "timestamp": "2024-01-01T10:00:00Z",
                    }
                ]
            ).to_csv(source, index=False)
            with self.assertRaises(ValueError):
                pm4py.read_ocel2_csv(source, encoding="latin-1")
            ocel = pm4py.read_ocel2_csv(source)
            with self.assertRaises(ValueError):
                pm4py.write_ocel2_bundle(
                    ocel, bundle_dir, storage_format="csv", encoding="latin-1"
                )
        finally:
            if os.path.exists(source):
                os.remove(source)
            if os.path.isdir(bundle_dir):
                shutil.rmtree(bundle_dir)

    @unittest.skipUnless(
        os.path.exists(EXAMPLE_CSV) and os.path.exists(EXAMPLE_XML),
        "OCEL2 CSV/XML example files are not available",
    )
    def test_order_management_csv_matches_xml_counts(self):
        csv_ocel = pm4py.read_ocel2_csv(EXAMPLE_CSV)
        xml_ocel = pm4py.read_ocel2_xml(EXAMPLE_XML)

        self.assertEqual(len(csv_ocel.events), len(xml_ocel.events))
        self.assertEqual(len(csv_ocel.objects), len(xml_ocel.objects))
        self.assertEqual(len(csv_ocel.relations), len(xml_ocel.relations))
        self.assertEqual(len(csv_ocel.o2o), len(xml_ocel.o2o))
        self.assertEqual(len(csv_ocel.object_changes), len(xml_ocel.object_changes))

    @unittest.skipUnless(
        os.path.exists(EXAMPLE_XML),
        "OCEL2 XML example file is not available",
    )
    def test_order_management_xml_export_csv_roundtrip_counts(self):
        output_path = os.path.join(OUTPUT_DIR, "order_management_ocel2_export.ocel.csv")

        try:
            ocel = pm4py.read_ocel2_xml(EXAMPLE_XML)
            pm4py.write_ocel2_csv(ocel, output_path)
            imported = pm4py.read_ocel2_csv(output_path)

            self.assertEqual(len(imported.events), len(ocel.events))
            self.assertEqual(len(imported.objects), len(ocel.objects))
            self.assertEqual(len(imported.relations), len(ocel.relations))
            self.assertEqual(len(imported.o2o), len(ocel.o2o))
            self.assertEqual(len(imported.object_changes), len(ocel.object_changes))
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    @unittest.skipUnless(
        PARQUET_ENGINE_AVAILABLE,
        "pyarrow or fastparquet is required for parquet bundle tests",
    )
    def test_ocel2_bundled_parquet_archive_roundtrip(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_bundle_source.csv")
        output_path = os.path.join(OUTPUT_DIR, "ocel2_bundle_export.ocel.zip")

        try:
            ocel = self._build_bundled_ocel(source)
            pm4py.write_ocel2(ocel, output_path)

            with zipfile.ZipFile(output_path, "r") as archive:
                names = set(archive.namelist())
                meta = json.loads(archive.read("ocel-meta.json").decode("utf-8"))

            self.assertEqual(meta["storageFormat"], "parquet")
            self.assertEqual(meta["eventTypes"]["create order"]["file"], "events/event_create%20order.parquet")
            self.assertEqual(meta["eventTypes"]["pay/order"]["file"], "events/event_pay%2Forder.parquet")
            self.assertEqual(meta["objectTypes"]["sales person"]["file"], "objects/object_sales%20person.parquet")
            self.assertIn("attributes", meta["eventTypes"]["create order"])
            self.assertIsInstance(meta["eventTypes"]["create order"]["attributes"], list)
            self.assertIn("object_changes/object_changes_orders.parquet", names)
            self.assertFalse(any(name.endswith(".csv") for name in names))

            import pyarrow as pa
            import pyarrow.parquet as pq
            import io

            with zipfile.ZipFile(output_path, "r") as archive:
                event_table = pq.read_table(
                    io.BytesIO(archive.read("events/event_create%20order.parquet"))
                )
                change_table = pq.read_table(
                    io.BytesIO(
                        archive.read("object_changes/object_changes_orders.parquet")
                    )
                )
            self.assertFalse(event_table.schema.field("ocel_id").nullable)
            self.assertEqual(
                event_table.schema.field("ocel_time").type,
                pa.timestamp("us", tz="UTC"),
            )
            self.assertTrue(event_table.schema.field("cost").nullable)
            self.assertFalse(change_table.schema.field("ocel_changed_field").nullable)

            imported = pm4py.read_ocel2(output_path)
            self._assert_same_counts(imported, ocel)
        finally:
            for path in (source, output_path):
                if os.path.exists(path):
                    os.remove(path)

    def test_ocel2_bundled_csv_directory_roundtrip(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_bundle_csv_source.csv")
        output_dir = os.path.join(OUTPUT_DIR, "ocel2_bundle_csv_dir")

        try:
            ocel = self._build_bundled_ocel(source)
            pm4py.write_ocel2_bundle(ocel, output_dir, storage_format="csv")

            with open(os.path.join(output_dir, "ocel-meta.json"), "r", encoding="utf-8") as f:
                meta = json.load(f)
            self.assertEqual(meta["storageFormat"], "csv")
            self.assertTrue(os.path.exists(os.path.join(output_dir, "events", "event_pay%2Forder.csv")))
            self.assertFalse(
                any(
                    filename.endswith(".parquet")
                    for root, _, filenames in os.walk(output_dir)
                    for filename in filenames
                )
            )

            order_changes = pd.read_csv(
                os.path.join(output_dir, "object_changes", "object_changes_orders.csv")
            )
            self.assertEqual(len(order_changes), 1)
            self.assertIn("amount", order_changes.columns)
            self.assertEqual(order_changes.iloc[0]["amount"], 10)

            imported = pm4py.read_ocel2(output_dir)
            self._assert_same_counts(imported, ocel)
        finally:
            if os.path.exists(source):
                os.remove(source)
            if os.path.isdir(output_dir):
                shutil.rmtree(output_dir)

    def test_ocel2_bundled_csv_metadata_controls_types(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_bundle_types_source.ocel.csv")
        output_dir = os.path.join(OUTPUT_DIR, "ocel2_bundle_types_dir")
        try:
            ocel = self._build_bundled_ocel(source)
            pm4py.write_ocel2_bundle(ocel, output_dir, storage_format="csv")
            meta_path = os.path.join(output_dir, "ocel-meta.json")
            with open(meta_path, "r", encoding="utf-8") as file:
                meta = json.load(file)
            cost_descriptor = meta["eventTypes"]["create order"]["attributes"][0]
            self.assertEqual(cost_descriptor, {"name": "cost", "type": "integer"})

            cost_descriptor["type"] = "string"
            for descriptor in meta["eventTypes"]["pay/order"]["attributes"]:
                if descriptor["name"] == "cost":
                    descriptor["type"] = "string"
            with open(meta_path, "w", encoding="utf-8") as file:
                json.dump(meta, file)

            imported = pm4py.read_ocel2_bundle(output_dir)
            self.assertEqual(imported.events.iloc[0]["cost"], "5")
            self.assertEqual(imported.events.iloc[1]["cost"], "7")
        finally:
            if os.path.exists(source):
                os.remove(source)
            if os.path.isdir(output_dir):
                shutil.rmtree(output_dir)

    def test_ocel2_bundled_all_primitive_types_and_csv_lexical_forms(self):
        output_dir = os.path.join(OUTPUT_DIR, "ocel2_bundle_primitive_types")
        try:
            ocel = self._build_typed_ocel()
            pm4py.write_ocel2_bundle(ocel, output_dir, storage_format="csv")
            with open(
                os.path.join(output_dir, "ocel-meta.json"), "r", encoding="utf-8"
            ) as file:
                meta = json.load(file)
            event_attributes = {
                item["name"]: item["type"]
                for item in meta["eventTypes"]["typed event"]["attributes"]
            }
            self.assertEqual(
                event_attributes,
                {
                    "label": "string",
                    "count": "integer",
                    "ratio": "float",
                    "active": "boolean",
                    "observed": "time",
                },
            )
            event_table = pd.read_csv(
                os.path.join(output_dir, "events", "event_typed%20event.csv"),
                dtype=str,
                keep_default_na=False,
            )
            self.assertEqual(event_table.iloc[0]["label"], "001")
            self.assertEqual(event_table.iloc[0]["active"], "true")
            self.assertEqual(
                event_table.iloc[0]["observed"], "2024-01-01T10:00:00+00:00"
            )
            object_table = pd.read_csv(
                os.path.join(output_dir, "objects", "object_typed%20object.csv"),
                dtype=str,
                keep_default_na=False,
            )
            self.assertEqual(object_table.iloc[0]["active"], "false")

            imported = pm4py.read_ocel2_bundle(output_dir)
            self.assertEqual(imported.events.iloc[0]["label"], "001")
            self.assertTrue(imported.events.iloc[0]["active"])
            self.assertEqual(
                imported.events.iloc[0]["observed"],
                pd.Timestamp("2024-01-01T10:00:00Z"),
            )
        finally:
            if os.path.isdir(output_dir):
                shutil.rmtree(output_dir)

    @unittest.skipUnless(
        importlib.util.find_spec("pyarrow") is not None,
        "pyarrow is required for specification-level parquet schema checks",
    )
    def test_ocel2_bundled_parquet_all_primitive_physical_types(self):
        output_path = os.path.join(
            OUTPUT_DIR, "ocel2_bundle_primitive_types.ocel.zip"
        )
        try:
            import io
            import pyarrow as pa
            import pyarrow.parquet as pq

            pm4py.write_ocel2_bundle(self._build_typed_ocel(), output_path)
            with zipfile.ZipFile(output_path, "r") as archive:
                table = pq.read_table(
                    io.BytesIO(archive.read("events/event_typed%20event.parquet"))
                )
            expected_types = {
                "ocel_id": pa.string(),
                "ocel_time": pa.timestamp("us", tz="UTC"),
                "label": pa.string(),
                "count": pa.int64(),
                "ratio": pa.float64(),
                "active": pa.bool_(),
                "observed": pa.timestamp("us", tz="UTC"),
            }
            self.assertEqual(
                {field.name: field.type for field in table.schema}, expected_types
            )
            self.assertFalse(table.schema.field("ocel_id").nullable)
            self.assertFalse(table.schema.field("ocel_time").nullable)
            for attribute in ("label", "count", "ratio", "active", "observed"):
                self.assertTrue(table.schema.field(attribute).nullable)
            imported = pm4py.read_ocel2_bundle(output_path)
            self.assertEqual(imported.events.iloc[0]["label"], "001")
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_ocel2_bundled_rejects_invalid_metadata_columns_and_mixed_storage(self):
        source = os.path.join(OUTPUT_DIR, "ocel2_bundle_invalid_source.ocel.csv")
        output_dir = os.path.join(OUTPUT_DIR, "ocel2_bundle_invalid_dir")
        try:
            ocel = self._build_bundled_ocel(source)
            pm4py.write_ocel2_bundle(ocel, output_dir, storage_format="csv")
            with open(
                os.path.join(output_dir, "relations", "unused.parquet"), "wb"
            ) as file:
                file.write(b"not parquet")
            with self.assertRaises(ValueError):
                pm4py.read_ocel2_bundle(output_dir)

            os.remove(os.path.join(output_dir, "relations", "unused.parquet"))
            meta_path = os.path.join(output_dir, "ocel-meta.json")
            with open(meta_path, "r", encoding="utf-8") as file:
                meta = json.load(file)
            meta["eventTypes"]["create order"]["attributes"] = {"cost": "integer"}
            with open(meta_path, "w", encoding="utf-8") as file:
                json.dump(meta, file)
            with self.assertRaises(ValueError):
                pm4py.read_ocel2_bundle(output_dir)

            meta["eventTypes"]["create order"]["attributes"] = [
                {"name": "cost", "type": "integer"}
            ]
            with open(meta_path, "w", encoding="utf-8") as file:
                json.dump(meta, file)
            event_path = os.path.join(
                output_dir, "events", "event_create%20order.csv"
            )
            event_table = pd.read_csv(event_path, dtype=str)
            event_table.drop(columns=["ocel_time"]).to_csv(event_path, index=False)
            with self.assertRaises(ValueError):
                pm4py.read_ocel2_bundle(output_dir)
        finally:
            if os.path.exists(source):
                os.remove(source)
            if os.path.isdir(output_dir):
                shutil.rmtree(output_dir)

    def test_ocel2_sqlite_type_mapping_is_injective(self):
        output_path = os.path.join(OUTPUT_DIR, "ocel2_type_collision.sqlite")
        timestamp = pd.Timestamp("2024-01-01T10:00:00Z")
        event_types = [
            "ST CHANGE OVERSTOCK to NORMAL",
            "ST CHANGE Overstock to Normal",
        ]
        ocel = OCEL(
            events=pd.DataFrame(
                [
                    {
                        "ocel:eid": "e1",
                        "ocel:activity": event_types[0],
                        "ocel:timestamp": timestamp,
                    },
                    {
                        "ocel:eid": "e2",
                        "ocel:activity": event_types[1],
                        "ocel:timestamp": timestamp,
                    },
                ]
            ),
            objects=pd.DataFrame(
                [{"ocel:oid": "o1", "ocel:type": "Order"}]
            ),
            relations=pd.DataFrame(
                [
                    {
                        "ocel:eid": "e1",
                        "ocel:activity": event_types[0],
                        "ocel:timestamp": timestamp,
                        "ocel:oid": "o1",
                        "ocel:type": "Order",
                        "ocel:qualifier": "",
                    },
                    {
                        "ocel:eid": "e2",
                        "ocel:activity": event_types[1],
                        "ocel:timestamp": timestamp,
                        "ocel:oid": "o1",
                        "ocel:type": "Order",
                        "ocel:qualifier": "",
                    },
                ]
            ),
        )
        try:
            pm4py.write_ocel2_sqlite(ocel, output_path)
            with sqlite3.connect(output_path) as connection:
                mappings = connection.execute(
                    "SELECT ocel_type, ocel_type_map FROM event_map_type"
                ).fetchall()
            self.assertEqual(len(mappings), 2)
            self.assertEqual(len({mapping.casefold() for _, mapping in mappings}), 2)
            imported = pm4py.read_ocel2_sqlite(output_path)
            self.assertEqual(set(imported.events[imported.event_activity]), set(event_types))
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


if __name__ == "__main__":
    unittest.main()
