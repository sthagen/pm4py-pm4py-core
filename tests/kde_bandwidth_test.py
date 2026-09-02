import datetime
import unittest
from unittest import mock

import numpy as np

from pm4py.statistics.attributes.common import get as attribute_statistics
from pm4py.statistics.traces.generic.common import case_duration


class KDEBandwidthTest(unittest.TestCase):
    @staticmethod
    def _density(values):
        return np.ones(len(values))

    def test_numeric_attribute_forwards_bandwidth(self):
        with mock.patch(
            "scipy.stats.gaussian_kde", return_value=self._density
        ) as gaussian_kde:
            attribute_statistics.get_kde_numeric_attribute(
                [1, 2, 4], parameters={"bw_method": 0.1}
            )

        self.assertEqual(0.1, gaussian_kde.call_args.kwargs["bw_method"])

    def test_date_attribute_forwards_bandwidth(self):
        first = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
        values = [first, first + datetime.timedelta(days=1)]

        with mock.patch(
            "scipy.stats.gaussian_kde", return_value=self._density
        ) as gaussian_kde:
            attribute_statistics.get_kde_date_attribute(
                values, parameters={"bw_method": 0.1}
            )

        self.assertEqual(0.1, gaussian_kde.call_args.kwargs["bw_method"])

    def test_case_duration_forwards_bandwidth(self):
        with mock.patch(
            "scipy.stats.gaussian_kde", return_value=self._density
        ) as gaussian_kde:
            case_duration.get_kde_caseduration(
                [1, 2, 4], parameters={"bw_method": 0.1}
            )

        self.assertEqual(0.1, gaussian_kde.call_args.kwargs["bw_method"])


if __name__ == "__main__":
    unittest.main()
