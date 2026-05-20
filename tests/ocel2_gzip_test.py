import gzip
import importlib.util
import os
import shutil
import unittest

import pm4py
from pm4py.objects.ocel.validation import jsonocel, xmlocel


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_OCEL_DIR = os.path.join(TESTS_DIR, "input_data", "ocel")
OUTPUT_DIR = os.path.join(TESTS_DIR, "test_output_data")


class Ocel2GzipTest(unittest.TestCase):
    def _assert_gzip_file(self, path):
        with open(path, "rb") as f:
            self.assertEqual(f.read(2), b"\x1f\x8b")

    def _assert_same_counts(self, original, imported):
        self.assertEqual(len(original.events), len(imported.events))
        self.assertEqual(len(original.objects), len(imported.objects))
        self.assertEqual(len(original.relations), len(imported.relations))
        self.assertEqual(len(original.o2o), len(imported.o2o))

    def _assert_gzip_roundtrip(self, ocel, output_path):
        pm4py.write_ocel2(ocel, output_path)

        self._assert_gzip_file(output_path)
        imported = pm4py.read_ocel2(output_path)
        self._assert_same_counts(ocel, imported)

    def _gzip_copy(self, source_path, target_path):
        with open(source_path, "rb") as source:
            with gzip.open(target_path, "wb") as target:
                shutil.copyfileobj(source, target)

    def test_ocel2_json_gzip_import_export(self):
        input_path = os.path.join(INPUT_OCEL_DIR, "ocel20_example.jsonocel")
        validation_path = os.path.join(INPUT_OCEL_DIR, "schema_ocel2.json")
        output_paths = [
            os.path.join(OUTPUT_DIR, "ocel20_example.json.gz"),
            os.path.join(OUTPUT_DIR, "ocel20_example.jsonocel.gz"),
        ]

        try:
            ocel = pm4py.read_ocel2(input_path)
            for output_path in output_paths:
                self._assert_gzip_roundtrip(ocel, output_path)
                if importlib.util.find_spec("jsonschema"):
                    self.assertTrue(jsonocel.apply(output_path, validation_path))
        finally:
            for path in output_paths:
                if os.path.exists(path):
                    os.remove(path)

    def test_ocel2_xml_gzip_import_export(self):
        input_path = os.path.join(INPUT_OCEL_DIR, "ocel20_example.xmlocel")
        output_paths = [
            os.path.join(OUTPUT_DIR, "ocel20_example.xml.gz"),
            os.path.join(OUTPUT_DIR, "ocel20_example.xmlocel.gz"),
        ]

        try:
            ocel = pm4py.read_ocel2(input_path)
            for output_path in output_paths:
                self._assert_gzip_roundtrip(ocel, output_path)
        finally:
            for path in output_paths:
                if os.path.exists(path):
                    os.remove(path)

    def test_ocel2_validation_accepts_gzip_input(self):
        json_input_path = os.path.join(INPUT_OCEL_DIR, "ocel20_example.jsonocel")
        json_validation_path = os.path.join(INPUT_OCEL_DIR, "schema_ocel2.json")
        json_gzip_path = os.path.join(OUTPUT_DIR, "ocel20_validation.json.gz")

        xml_input_path = os.path.join(INPUT_OCEL_DIR, "ocel20_example.xmlocel")
        xml_validation_path = os.path.join(INPUT_OCEL_DIR, "ocel2-validation.xsd")
        xml_gzip_path = os.path.join(OUTPUT_DIR, "ocel20_validation.xml.gz")

        try:
            self._gzip_copy(json_input_path, json_gzip_path)
            self._gzip_copy(xml_input_path, xml_gzip_path)

            if importlib.util.find_spec("jsonschema"):
                self.assertEqual(
                    jsonocel.apply(json_input_path, json_validation_path),
                    jsonocel.apply(json_gzip_path, json_validation_path),
                )
            self.assertEqual(
                xmlocel.apply(xml_input_path, xml_validation_path),
                xmlocel.apply(xml_gzip_path, xml_validation_path),
            )
        finally:
            for path in (json_gzip_path, xml_gzip_path):
                if os.path.exists(path):
                    os.remove(path)


if __name__ == "__main__":
    unittest.main()
