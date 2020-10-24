import unittest
from pm4py.objects.log.importer.xes import importer as xes_importer
import pandas as pd
from pm4py.objects.log.util import dataframe_utils
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.statistics.variants.log import get as log_variants
from pm4py.statistics.variants.pandas import get as pd_variants
import os


class InductiveMinerOtherTests(unittest.TestCase):
    def test_dataframe_dfg_based(self):
        df = pd.read_csv(os.path.join("input_data", "running-example.csv"))
        df = dataframe_utils.convert_timestamp_columns_in_df(df)
        net, im, fm = inductive_miner.apply(df, variant=inductive_miner.IMd)

    def test_log_variants_dfg_based(self):
        log = xes_importer.apply(os.path.join("input_data", "running-example.xes"))
        net, im, fm = inductive_miner.apply_variants(log_variants.get_variants(log),
                                                     variant=inductive_miner.IMd)

    def test_log_tree_variants_dfg_based(self):
        log = xes_importer.apply(os.path.join("input_data", "running-example.xes"))
        tree = inductive_miner.apply_tree_variants(log_variants.get_variants(log),
                                                   variant=inductive_miner.IMd)

    def test_df_variants_dfg_based(self):
        df = pd.read_csv(os.path.join("input_data", "running-example.csv"))
        df = dataframe_utils.convert_timestamp_columns_in_df(df)
        net, im, fm = inductive_miner.apply_variants(pd_variants.get_variants_set(df),
                                                     variant=inductive_miner.IMd)

    def test_df_tree_variants_dfg_based(self):
        df = pd.read_csv(os.path.join("input_data", "running-example.csv"))
        df = dataframe_utils.convert_timestamp_columns_in_df(df)
        tree = inductive_miner.apply_tree_variants(pd_variants.get_variants_set(df),
                                                   variant=inductive_miner.IMd)


if __name__ == "__main__":
    unittest.main()
