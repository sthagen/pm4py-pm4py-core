import unittest
from collections import Counter
from unittest import mock

from pm4py.algo.discovery.inductive.dtypes.im_ds import IMDataStructureUVCL
from pm4py.algo.discovery.powl import algorithm
from pm4py.algo.discovery.powl.inductive.utils import filtering
from pm4py.algo.discovery.powl.inductive.variants.brute_force import bf_partial_order_cut
from pm4py.algo.discovery.powl.inductive.variants.maximal import maximal_partial_order_cut
from pm4py.algo.discovery.powl.inductive.variants.powl_discovery_varaints import (
    POWLDiscoveryVariant,
)
from pm4py.objects.powl.BinaryRelation import BinaryRelation
from pm4py.util.compression.dtypes import UVCL


class PowlDiscoveryCoverageTest(unittest.TestCase):
    def test_all_discovery_variants_across_cut_and_fallthrough_patterns(self):
        logs = (
            UVCL(),
            UVCL({(): 1, ("A",): 2}),
            UVCL({("A",): 2, ("B",): 1}),
            UVCL({("A", "B", "C"): 2}),
            UVCL({("A", "B"): 2, ("B", "A"): 2}),
            UVCL({("A", "B", "A"): 2, ("A", "C", "A"): 1}),
            UVCL({("A", "B", "C"): 3, ("A", "C", "B"): 2, ("D",): 1}),
        )
        # UVCL is a typing alias in this release, so expose its concrete
        # Counter runtime type while exercising the compressed-log API.
        with mock.patch.object(algorithm, "UVCL", Counter):
            for variant in POWLDiscoveryVariant:
                self.assertIsNotNone(algorithm.get_variant(variant))
                for log in logs:
                    model = algorithm.apply(log, variant=variant)
                    self.assertIsNotNone(model)
                    self.assertEqual(model, model.simplify())
        with self.assertRaises(Exception):
            algorithm.get_variant(object())

    def test_filtering_helpers(self):
        log = Counter({("A",): 5, ("B",): 3, ("C",): 1})
        filtered = filtering.filter_most_frequent_variants(log)
        self.assertEqual({("A",), ("B",)}, set(filtered.data_structure))
        decreasing = filtering.filter_most_frequent_variants_with_decreasing_factor(log, 0.5)
        self.assertEqual({("A",), ("B",)}, set(decreasing.data_structure))

    def test_brute_force_partition_and_order_helpers(self):
        nodes = ["A", "B", "C"]
        all_partitions = list(bf_partial_order_cut.get_partitions_of_size_k(nodes))
        self.assertEqual(5, len(all_partitions))
        self.assertEqual(3, len(list(bf_partial_order_cut.get_partitions_of_size_k(nodes, 2))))
        self.assertEqual([], list(bf_partial_order_cut.get_partitions_of_size_k(nodes, 4)))
        with self.assertRaises(ValueError):
            list(bf_partial_order_cut.get_partitions_of_size_k(nodes, 0))
        self.assertTrue(list(bf_partial_order_cut.partition(nodes)))
        self.assertTrue(bf_partial_order_cut.xor(True, False))
        self.assertFalse(bf_partial_order_cut.xor(True, True))

        order = bf_partial_order_cut.generate_order(
            [("A",), ("B",), ("C",)],
            {("A", "B"), ("A", "C"), ("B", "C")},
        )
        self.assertTrue(order.is_strict_partial_order())
        self.assertTrue(bf_partial_order_cut.contains(order.nodes, ("A",)))
        self.assertEqual(2, len(bf_partial_order_cut.remove(order.nodes, ("A",))))

        data = IMDataStructureUVCL(Counter({("A", "B", "C"): 2}))
        projected = bf_partial_order_cut.BruteForcePartialOrderCutUVCL.project(
            data, [("A", "B"), ("C",)]
        )
        self.assertEqual(2, len(projected))
        with self.assertRaises(Exception):
            bf_partial_order_cut.BruteForcePartialOrderCut.operator()

    def test_maximal_order_helpers(self):
        nodes = ["A", "B", "C"]
        efg = {("A", "B"), ("A", "C"), ("B", "C")}
        initial = maximal_partial_order_cut.generate_initial_order(nodes, efg)
        self.assertTrue(initial.is_strict_partial_order())
        clustered = maximal_partial_order_cut.cluster_order(initial)
        self.assertTrue(clustered.is_strict_partial_order())
        self.assertTrue(
            maximal_partial_order_cut.is_valid_order(
                clustered, efg, {"A"}, {"C"}
            )
        )
        self.assertFalse(maximal_partial_order_cut.is_valid_order(None, efg, {"A"}, {"C"}))
        singleton = BinaryRelation([("A",)])
        self.assertFalse(maximal_partial_order_cut.is_valid_order(singleton, efg, {"A"}, {"A"}))

        data = IMDataStructureUVCL(Counter({("A", "B", "C"): 2}))
        projected = maximal_partial_order_cut.project_on_groups_with_unique_activities(
            data.data_structure, [("A", "B"), ("C",)]
        )
        self.assertEqual(2, len(projected))
        with self.assertRaises(Exception):
            maximal_partial_order_cut.MaximalPartialOrderCut.operator()


if __name__ == "__main__":
    unittest.main()
