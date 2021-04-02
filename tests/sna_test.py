import os
import unittest

from pm4py.algo.enhancement.sna import algorithm as sna_alg
from pm4py.objects.log.importer.xes import importer as xes_importer
import pandas as pd
from pm4py.objects.log.util import dataframe_utils


class SnaTests(unittest.TestCase):
    def test_1(self):
        # to avoid static method warnings in tests,
        # that by construction of the unittest package have to be expressed in such way
        self.dummy_variable = "dummy_value"

        log = xes_importer.apply(os.path.join("..", "tests", "input_data", "running-example.xes"))

        hw_values = sna_alg.apply(log, variant=sna_alg.Variants.HANDOVER_LOG)
        wt_values = sna_alg.apply(log, variant=sna_alg.Variants.WORKING_TOGETHER_LOG)
        sub_values = sna_alg.apply(log, variant=sna_alg.Variants.SUBCONTRACTING_LOG)
        ja_values = sna_alg.apply(log, variant=sna_alg.Variants.JOINTACTIVITIES_LOG)

    def test_pandas(self):
        # to avoid static method warnings in tests,
        # that by construction of the unittest package have to be expressed in such way
        self.dummy_variable = "dummy_value"

        log = pd.read_csv(os.path.join("..", "tests", "input_data", "running-example.csv"))
        log = dataframe_utils.convert_timestamp_columns_in_df(log)

        hw_values = sna_alg.apply(log, variant=sna_alg.Variants.HANDOVER_PANDAS)
        wt_values = sna_alg.apply(log, variant=sna_alg.Variants.WORKING_TOGETHER_PANDAS)
        sub_values = sna_alg.apply(log, variant=sna_alg.Variants.SUBCONTRACTING_PANDAS)

    def test_log_orgmining_local_attr(self):
        from pm4py.algo.enhancement.organizational_mining.local_diagnostics import algorithm
        log = xes_importer.apply(os.path.join("input_data", "receipt.xes"))
        algorithm.apply_from_group_attribute(log)

    def test_log_orgmining_local_clustering(self):
        from pm4py.algo.enhancement.organizational_mining.local_diagnostics import algorithm
        from pm4py.algo.enhancement.sna.variants.log import jointactivities
        from pm4py.algo.enhancement.sna import util
        log = xes_importer.apply(os.path.join("input_data", "receipt.xes"))
        ja = jointactivities.apply(log)
        clustering = util.cluster_affinity_propagation(ja)
        algorithm.apply_from_clustering_or_roles(log, clustering)

    def test_log_orgmining_local_roles(self):
        from pm4py.algo.enhancement.organizational_mining.local_diagnostics import algorithm
        from pm4py.algo.enhancement.roles import algorithm as roles_detection
        log = xes_importer.apply(os.path.join("input_data", "receipt.xes"))
        roles = roles_detection.apply(log)
        algorithm.apply_from_clustering_or_roles(log, roles)


if __name__ == "__main__":
    unittest.main()
