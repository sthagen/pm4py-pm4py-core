import os
import unittest

import polars as pl

import pm4py


class TestPolarsProcessConformance(unittest.TestCase):
    DATA_DIR = os.path.join(os.path.dirname(__file__), "input_data")
    LOG_PATH = os.path.join(DATA_DIR, "running-example.csv")

    @classmethod
    def setUpClass(cls):
        df = pl.read_csv(cls.LOG_PATH)
        cls._base_df = df.with_columns(
            pl.col("time:timestamp").str.strptime(
                pl.Datetime, "%Y-%m-%d %H:%M:%S%z"
            ),
            pl.col("case:concept:name").cast(pl.Utf8),
            pl.col("concept:name").cast(pl.Utf8),
            pl.col("org:resource").cast(pl.Utf8),
        )

    @classmethod
    def _lazy_log(cls) -> pl.LazyFrame:
        return cls._base_df.lazy()

    def test_conformance_diagnostics_token_based_replay(self):
        log_for_model = self._lazy_log()
        net, im, fm = pm4py.discover_petri_net_inductive(log_for_model)
        log_for_conformance = self._lazy_log()
        diagnostics = pm4py.conformance_diagnostics_token_based_replay(
            log_for_conformance, net, im, fm
        )
        self.assertIsInstance(diagnostics, list)
        self.assertTrue(diagnostics)
        self.assertIsInstance(diagnostics[0], dict)

    def test_conformance_diagnostics_alignments_petri_net(self):
        log_for_model = self._lazy_log()
        net, im, fm = pm4py.discover_petri_net_inductive(log_for_model)
        log_for_conformance = self._lazy_log()
        try:
            diagnostics = pm4py.conformance_diagnostics_alignments(
                log_for_conformance, net, im, fm
            )
        except (ImportError, ModuleNotFoundError) as exc:
            self.skipTest(f"Alignments optional dependency missing: {exc}")
        self.assertIsInstance(diagnostics, list)
        if diagnostics:
            self.assertIsInstance(diagnostics[0], dict)

    def test_fitness_token_based_replay(self):
        log_for_model = self._lazy_log()
        net, im, fm = pm4py.discover_petri_net_inductive(log_for_model)
        log_for_fitness = self._lazy_log()
        fitness = pm4py.fitness_token_based_replay(log_for_fitness, net, im, fm)
        self.assertIn("log_fitness", fitness)

    def test_fitness_alignments(self):
        log_for_model = self._lazy_log()
        net, im, fm = pm4py.discover_petri_net_inductive(log_for_model)
        log_for_fitness = self._lazy_log()
        try:
            fitness = pm4py.fitness_alignments(log_for_fitness, net, im, fm)
        except (ImportError, ModuleNotFoundError) as exc:
            self.skipTest(f"Alignments optional dependency missing: {exc}")
        self.assertIn("averageFitness", fitness)

    def test_precision_token_based_replay(self):
        log_for_model = self._lazy_log()
        net, im, fm = pm4py.discover_petri_net_inductive(log_for_model)
        log_for_precision = self._lazy_log()
        precision = pm4py.precision_token_based_replay(
            log_for_precision, net, im, fm
        )
        self.assertIsInstance(precision, float)

    def test_precision_alignments(self):
        log_for_model = self._lazy_log()
        net, im, fm = pm4py.discover_petri_net_inductive(log_for_model)
        log_for_precision = self._lazy_log()
        try:
            precision = pm4py.precision_alignments(log_for_precision, net, im, fm)
        except (ImportError, ModuleNotFoundError) as exc:
            self.skipTest(f"Alignments optional dependency missing: {exc}")
        self.assertIsInstance(precision, float)

    def test_generalization_token_based_replay(self):
        log_for_model = self._lazy_log()
        net, im, fm = pm4py.discover_petri_net_inductive(log_for_model)
        log_for_generalization = self._lazy_log()
        generalization = pm4py.generalization_tbr(
            log_for_generalization, net, im, fm
        )
        self.assertIsInstance(generalization, float)

    def test_alignments_diagnostics_process_tree(self):
        log_for_model = self._lazy_log()
        process_tree = pm4py.discover_process_tree_inductive(log_for_model)
        log_for_conformance = self._lazy_log()
        try:
            diagnostics = pm4py.conformance_diagnostics_alignments(
                log_for_conformance, process_tree
            )
        except (ImportError, ModuleNotFoundError) as exc:
            self.skipTest(f"Alignments optional dependency missing: {exc}")
        self.assertIsInstance(diagnostics, list)

    def test_alignments_diagnostics_dfg(self):
        log_for_model = self._lazy_log()
        dfg, start_activities, end_activities = pm4py.discover_dfg(log_for_model)
        log_for_conformance = self._lazy_log()
        try:
            diagnostics = pm4py.conformance_diagnostics_alignments(
                log_for_conformance, dfg, start_activities, end_activities
            )
        except (ImportError, ModuleNotFoundError) as exc:
            self.skipTest(f"Alignments optional dependency missing: {exc}")
        self.assertIsInstance(diagnostics, list)

    def test_fitness_footprints(self):
        log = self._lazy_log()
        net_log = self._lazy_log()
        net, im, fm = pm4py.discover_petri_net_inductive(net_log)
        fitness = pm4py.fitness_footprints(log, net, im, fm)
        self.assertIsInstance(fitness, float)

    def test_precision_footprints(self):
        log = self._lazy_log()
        net_log = self._lazy_log()
        net, im, fm = pm4py.discover_petri_net_inductive(net_log)
        precision = pm4py.precision_footprints(log, net, im, fm)
        self.assertIsInstance(precision, float)

    def test_conformance_diagnostics_footprints(self):
        log = self._lazy_log()
        net_log = self._lazy_log()
        net, im, fm = pm4py.discover_petri_net_inductive(net_log)
        diagnostics = pm4py.conformance_diagnostics_footprints(log, net, im, fm)
        self.assertIsInstance(diagnostics, dict)

    def test_conformance_log_skeleton(self):
        log_for_model = self._lazy_log()
        skeleton = pm4py.discover_log_skeleton(log_for_model)
        log_for_conformance = self._lazy_log()
        result = pm4py.conformance_log_skeleton(log_for_conformance, skeleton)
        self.assertIsInstance(result, list)

    def test_conformance_declare(self):
        log_for_model = self._lazy_log()
        declare_model = pm4py.discover_declare(log_for_model)
        log_for_conformance = self._lazy_log()
        try:
            result = pm4py.conformance_declare(log_for_conformance, declare_model)
        except (ImportError, ModuleNotFoundError) as exc:
            self.skipTest(f"DECLARE optional dependency missing: {exc}")
        self.assertIsInstance(result, list)

    def test_conformance_temporal_profile(self):
        log_for_model = self._lazy_log()
        temporal_profile = pm4py.discover_temporal_profile(log_for_model)
        log_for_conformance = self._lazy_log()
        result = pm4py.conformance_temporal_profile(
            log_for_conformance, temporal_profile, zeta=1.5
        )
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
