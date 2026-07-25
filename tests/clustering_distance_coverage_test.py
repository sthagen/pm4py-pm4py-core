import unittest
from unittest import mock

import numpy as np
import pandas as pd

from pm4py.algo.clustering.trace_attribute_driven.util import evaluation, filter_subsets
from pm4py.algo.clustering.trace_attribute_driven.variants import (
    act_dist_calc,
    logslice_dist,
    sim_calc,
    suc_dist_calc,
)
from pm4py.objects.log.obj import Event, EventLog, Trace


class ClusteringDistanceCoverageTest(unittest.TestCase):
    @staticmethod
    def _log(variants, group):
        log = EventLog()
        index = 0
        for activities, count in variants:
            for _ in range(count):
                index += 1
                log.append(
                    Trace(
                        [Event({"concept:name": activity}) for activity in activities],
                        attributes={"concept:name": f"{group}-{index}", "AMOUNT_REQ": group},
                    )
                )
        return log

    @classmethod
    def _logs(cls):
        return (
            cls._log([(("A", "B", "C"), 3), (("A", "C"), 2)], "one"),
            cls._log([(("A", "B", "D"), 2), (("B", "D"), 2)], "two"),
        )

    def test_filter_subset_helpers(self):
        log1, _ = self._logs()
        self.assertEqual(
            len(log1),
            len(
                filter_subsets.apply_trace_attributes(
                    log1,
                    ["one"],
                    parameters={filter_subsets.Parameters.ATTRIBUTE_KEY: "AMOUNT_REQ"},
                )
            ),
        )
        self.assertEqual(
            0,
            len(
                filter_subsets.apply_trace_attributes(
                    log1,
                    ["one"],
                    parameters={
                        filter_subsets.Parameters.ATTRIBUTE_KEY: "AMOUNT_REQ",
                        filter_subsets.Parameters.POSITIVE: False,
                    },
                )
            ),
        )
        variants = filter_subsets.sublog2varlist(log1, 2, 1)
        self.assertEqual(2, len(variants))
        for helper in (
            filter_subsets.sublog_percent,
            filter_subsets.sublog_percent2actlist,
            filter_subsets.sublog_percent2varlist,
        ):
            dataframe, values = helper(log1, 1.0, parameters={"lower_percent": 0})
            self.assertEqual(2, len(dataframe))
            self.assertEqual(2, len(values))
        self.assertTrue(filter_subsets.logslice_percent_act(log1, 0.5)[0])
        sliced_logs, frequencies = filter_subsets.logslice_percent(log1, 0.5)
        self.assertEqual(len(sliced_logs), len(frequencies))
        admitted = next(iter(filter_subsets.sublog_percent2varlist(log1, 1.0)[1:]))
        self.assertTrue(filter_subsets.apply_variants_filter(log1, admitted))
        self.assertIsInstance(filter_subsets.sublog2df_num(log1, 1), pd.DataFrame)
        self.assertIsInstance(filter_subsets.sublog2df(log1, 2, 1), pd.DataFrame)

    def test_activity_distance_variants(self):
        log1, log2 = self._logs()
        variants1 = filter_subsets.sublog2varlist(log1, 1, 10)
        variants2 = filter_subsets.sublog2varlist(log2, 1, 10)
        self.assertEqual(3, len(act_dist_calc.occu_var_act(variants1[0])))
        original_sublog2df = filter_subsets.sublog2df
        with mock.patch.object(
            filter_subsets,
            "sublog2df",
            side_effect=lambda log, threshold: original_sublog2df(log, threshold, 10),
        ):
            legacy_distance = filter_subsets.act_dist(
                variants1, variants2, log1, log2, 1
            )
        results = [
            act_dist_calc.act_sim(variants1, variants2, log1, log2, 1, 10),
            act_dist_calc.act_sim(variants1, variants2, log1, log2, 1, 10, parameters={"single": True}),
            act_dist_calc.act_sim_med(variants1, variants2, log1, log2, 1, 10),
            act_dist_calc.act_sim_dual(variants1, variants2, log1, log2, 1, 10, parameters={"single": True}),
            act_dist_calc.act_sim_dual(variants1, variants2, log1, log2, 1, 10, parameters={"single": False}),
            act_dist_calc.act_sim_percent(log1, log2, 1.0, 1.0),
            act_dist_calc.act_sim_percent_avg(log1, log2, 1.0, 1.0),
            act_dist_calc.act_sim_percent_avg_actset(
                log1, log2, 1.0, 1.0, pd.DataFrame({"var": ["A", "B", "C", "D"]})
            ),
            legacy_distance,
        ]
        self.assertTrue(all(value is not None for value in results))

    def test_succession_and_combined_distance_variants(self):
        log1, log2 = self._logs()
        variants1 = filter_subsets.sublog2varlist(log1, 1, 10)
        variants2 = filter_subsets.sublog2varlist(log2, 1, 10)
        self.assertFalse(suc_dist_calc.occu_suc({("A", "B"): 3, ("B", "C"): 1}, 0.5).empty)
        self.assertFalse(suc_dist_calc.occu_var_suc(["A", "B", "A"], parameters={"binarize": True}).empty)
        self.assertFalse(suc_dist_calc.occu_var_suc(["A", "B", "A"], parameters={"binarize": False}).empty)
        results = [
            suc_dist_calc.suc_sim(variants1, variants2, log1, log2, 1, 10),
            suc_dist_calc.suc_sim(variants1, variants2, log1, log2, 1, 10, parameters={"single": True}),
            suc_dist_calc.suc_sim_dual(variants1, variants2, log1, log2, 1, 10, parameters={"single": True}),
            suc_dist_calc.suc_sim_dual(variants1, variants2, log1, log2, 1, 10),
            suc_dist_calc.suc_sim_percent(log1, log2, 1.0, 1.0),
            suc_dist_calc.suc_sim_percent_avg(log1, log2, 1.0, 1.0),
            sim_calc.dist_calc(variants1, variants2, log1, log2, 1, 10, 0.5),
            sim_calc.dist_calc(variants1, variants2, log1, log2, 1, 10, 0.5, parameters={"single": True}),
        ]
        self.assertTrue(all(np.isscalar(value) for value in results))

    def test_log_slice_and_evaluation_distances(self):
        log1, log2 = self._logs()
        self.assertEqual(len(log1), len(logslice_dist.log2sublog(log1, "one")))
        distances = [
            logslice_dist.slice_dist_suc(log1, log2, 0.5),
            logslice_dist.slice_dist_act(log1, log2, 0.5),
        ]
        self.assertTrue(all(np.isscalar(value) for value in distances))
        logs = [log1, log2]
        condensed = [
            evaluation.dfg_dis(logs, 1.0, 0.5),
            evaluation.eval_avg_variant(logs, 1.0, 0.5),
            evaluation.eval_DMM_variant(logs, 1.0, 0.5),
            evaluation.eval_avg_leven(logs, 1.0, 0.5),
            evaluation.eval_DMM_leven(logs, 1.0, 0.5),
        ]
        self.assertTrue(all(value.shape == (1,) for value in condensed))


if __name__ == "__main__":
    unittest.main()
