import copy
import importlib
import importlib.machinery
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import pandas as pd

from pm4py.objects.log.obj import Event, EventLog, Trace


class _IdentityMechanism:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def randomise(self, value):
        return value


class PrivacyCoverageTest(unittest.TestCase):
    @staticmethod
    def _logs():
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        original = EventLog()
        query = EventLog()
        for index, activities in enumerate((("A", "B"), ("A", "C"))):
            trace = Trace(attributes={"concept:name": f"original-{index}", "secret": "remove"})
            query_trace = Trace(attributes={"concept:name": f"query-{index}"})
            for pos, activity in enumerate(activities):
                timestamp = base + timedelta(hours=index, minutes=pos + 1)
                trace.append(
                    Event(
                        {
                            "concept:name": activity,
                            "time:timestamp": timestamp,
                            "amount": pos + 1,
                            "ratio": float(pos + 1),
                            "flag": bool(pos),
                            "category": "x" if pos == 0 else "y",
                            "blocked": "remove",
                            "nullable": None,
                        }
                    )
                )
                query_trace.append(Event({"concept:name": activity, "time:timestamp": timestamp}))
            original.append(trace)
            query.append(query_trace)
        return original, query

    @staticmethod
    def _fake_diffprivlib():
        mechanisms = types.ModuleType("diffprivlib.mechanisms")
        mechanisms.Binary = _IdentityMechanism
        mechanisms.LaplaceBoundedDomain = _IdentityMechanism
        mechanisms.ExponentialCategorical = _IdentityMechanism
        mechanisms.__spec__ = importlib.machinery.ModuleSpec(
            "diffprivlib.mechanisms", loader=None
        )
        package = types.ModuleType("diffprivlib")
        package.mechanisms = mechanisms
        package.__spec__ = importlib.machinery.ModuleSpec("diffprivlib", loader=None)
        return package, mechanisms

    def test_trace_matching_and_attribute_anonymization(self):
        package, mechanisms = self._fake_diffprivlib()
        with mock.patch.dict(
            sys.modules,
            {"diffprivlib": package, "diffprivlib.mechanisms": mechanisms},
        ):
            attribute_module = importlib.import_module(
                "pm4py.algo.anonymization.pripel.util.AttributeAnonymizer"
            )
            matcher_module = importlib.import_module(
                "pm4py.algo.anonymization.pripel.util.TraceMatcher"
            )
            pripel = importlib.import_module(
                "pm4py.algo.anonymization.pripel.variants.pripel"
            )

            original, query = self._logs()
            matcher = matcher_module.TraceMatcher(copy.deepcopy(query), copy.deepcopy(original))
            matched = matcher.matchQueryToLog(greedy=False)
            self.assertEqual(2, len(matched))
            distribution = matcher.getAttributeDistribution()
            timestamps, differences = matcher.getTimeStampData()
            self.assertIn("amount", distribution)
            self.assertEqual(2, len(differences))

            anonymizer = attribute_module.AttributeAnonymizer()
            anonymized = anonymizer.anonymize(
                matched,
                distribution,
                epsilon=1.0,
                allTimestampDifferences=differences,
                allTimestamps=timestamps,
            )
            self.assertEqual(2, len(anonymized))
            self.assertIsInstance(anonymized[0][0]["amount"], int)
            self.assertIsInstance(anonymized[0][0]["flag"], bool)

            original, query = self._logs()
            dataframe = pripel.apply(
                original,
                query,
                1.0,
                parameters={"blocklist": ["secret", "blocked"]},
            )
            self.assertIsInstance(dataframe, pd.DataFrame)
            self.assertNotIn("blocked", dataframe.columns)
            self.assertNotIn("nullable", dataframe.columns)
            self.assertEqual({"0", "1"}, set(dataframe["case:concept:name"]))

            with self.assertRaises(ValueError):
                pripel.apply_pripel(original, EventLog(), 1.0, None)

    def test_greedy_trace_matching_variants_and_private_helpers(self):
        package, mechanisms = self._fake_diffprivlib()
        with mock.patch.dict(
            sys.modules,
            {"diffprivlib": package, "diffprivlib.mechanisms": mechanisms},
        ):
            matcher_module = importlib.import_module(
                "pm4py.algo.anonymization.pripel.util.TraceMatcher"
            )
            original, query = self._logs()
            matcher = matcher_module.TraceMatcher(copy.deepcopy(query), copy.deepcopy(original))
            matched = matcher.matchQueryToLog(greedy=True)
            self.assertEqual(2, len(matched))

            original, query = self._logs()
            query.append(copy.deepcopy(query[0]))
            query[-1].attributes["concept:name"] = "query-extra"
            original.append(copy.deepcopy(original[1]))
            original[-1].attributes["concept:name"] = "original-extra"
            matcher = matcher_module.TraceMatcher(query, original)
            partial = matcher.matchQueryToLog(fillUp=False, greedy=True)
            self.assertGreaterEqual(len(partial), 2)


if __name__ == "__main__":
    unittest.main()
