import json
import importlib.util
import os
import shutil
import unittest
import zipfile

import pandas as pd

import pm4py


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
        source = os.path.join(OUTPUT_DIR, "ocel2_compact_source.csv")
        exported = os.path.join(OUTPUT_DIR, "ocel2_compact_exported.csv")

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
            self.assertEqual(len(ocel.object_changes), 1)
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
        source = os.path.join(OUTPUT_DIR, "ocel2_revised_constraints.csv")
        exported = os.path.join(OUTPUT_DIR, "ocel2_revised_constraints_exported.csv")

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
            self.assertEqual(len(ocel.object_changes), 1)
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
        output_path = os.path.join(OUTPUT_DIR, "order_management_ocel2_export.csv")

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
            self.assertIn("object_changes/object_changes_orders.parquet", names)
            self.assertFalse(any(name.endswith(".csv") for name in names))

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

            empty_changes = pd.read_csv(
                os.path.join(output_dir, "object_changes", "object_changes_orders.csv")
            )
            self.assertEqual(len(empty_changes), 0)
            self.assertIn("amount", empty_changes.columns)

            imported = pm4py.read_ocel2(output_dir)
            self._assert_same_counts(imported, ocel)
        finally:
            if os.path.exists(source):
                os.remove(source)
            if os.path.isdir(output_dir):
                shutil.rmtree(output_dir)


if __name__ == "__main__":
    unittest.main()
