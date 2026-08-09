import datetime
import unittest

from pm4py.util import constants
from pm4py.util.dt_parsing.variants import strpfromiso


class StrpFromIsoTest(unittest.TestCase):
    """Regression tests for the strpfromiso date parser (the default ISO8601
    parser for Python >= 3.7). Covers the timezone-conversion bug where a
    non-UTC offset was silently relabeled as UTC instead of being converted,
    shifting the represented instant by the source offset."""

    def setUp(self):
        self._original_aware = constants.ENABLE_DATETIME_COLUMNS_AWARE

    def tearDown(self):
        constants.ENABLE_DATETIME_COLUMNS_AWARE = self._original_aware

    def test_non_utc_offset_is_converted_not_relabeled(self):
        constants.ENABLE_DATETIME_COLUMNS_AWARE = True

        parsed = strpfromiso.apply("2026-07-23T10:00:00+05:00")

        expected = datetime.datetime(
            2026, 7, 23, 10, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=5))
        ).astimezone(datetime.timezone.utc)

        self.assertEqual(parsed, expected)
        self.assertEqual(parsed.hour, 5)
        self.assertEqual(parsed.utcoffset(), datetime.timedelta(0))

    def test_negative_utc_offset_is_converted_not_relabeled(self):
        constants.ENABLE_DATETIME_COLUMNS_AWARE = True

        parsed = strpfromiso.apply("2026-07-23T10:00:00-08:00")

        self.assertEqual(parsed.hour, 18)
        self.assertEqual(parsed.utcoffset(), datetime.timedelta(0))

    def test_z_suffix_still_parses_as_utc(self):
        constants.ENABLE_DATETIME_COLUMNS_AWARE = True

        parsed = strpfromiso.apply("2026-07-23T10:00:00Z")

        self.assertEqual(parsed.hour, 10)
        self.assertEqual(parsed.utcoffset(), datetime.timedelta(0))

    def test_naive_input_is_treated_as_already_utc(self):
        # No offset in the source string at all: there is nothing to convert
        # from, so the value should be labeled UTC as-is, not reinterpreted
        # through the host machine's local timezone.
        constants.ENABLE_DATETIME_COLUMNS_AWARE = True

        parsed = strpfromiso.apply("2026-07-23T10:00:00")

        self.assertEqual(parsed.hour, 10)
        self.assertEqual(parsed.utcoffset(), datetime.timedelta(0))

    def test_aware_disabled_keeps_local_wall_clock_naive(self):
        constants.ENABLE_DATETIME_COLUMNS_AWARE = False

        parsed = strpfromiso.apply("2026-07-23T10:00:00+05:00")

        self.assertIsNone(parsed.tzinfo)
        self.assertEqual(parsed.hour, 10)


if __name__ == "__main__":
    unittest.main()
