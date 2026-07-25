import importlib.util
import os
import random
import unittest
from unittest import mock

import numpy as np

import pm4py
from pm4py.algo.clustering.trace_attribute_driven.linkage_method import (
    linkage_avg,
)
from pm4py.algo.clustering.trace_attribute_driven.util import filter_subsets
from pm4py.algo.clustering.trace_attribute_driven.variants import (
    act_dist_calc,
    sim_calc,
    suc_dist_calc,
)
from pm4py.algo.evaluation.earth_mover_distance import algorithm as emd
from pm4py.algo.evaluation.earth_mover_distance.variants import pyemd
from pm4py.algo.anonymization.trace_variant_query import algorithm as trace_privacy
from pm4py.objects.bpmn import semantics as bpmn_semantics
from pm4py.objects.bpmn.obj import BPMN, Marking as BPMNMarking
from pm4py.objects.bpmn.util import bpmn_utils, reduction as bpmn_reduction
from pm4py.objects.conversion.powl import converter as powl_to_petri
from pm4py.objects.conversion.powl.variants import to_process_tree
from pm4py.objects.log.obj import Event, EventLog, Trace
from pm4py.objects.ocel.importer.jsonocel import importer as jsonocel_importer
from pm4py.objects.ocel.importer.xmlocel import importer as xmlocel_importer
from pm4py.objects.powl.obj import (
    FrequentTransition,
    OperatorPOWL,
    Sequence,
    SilentTransition,
    StrictPartialOrder,
    Transition,
)
from pm4py.objects.process_tree.obj import Operator


class ModelUtilitiesCoverageTest(unittest.TestCase):
    @staticmethod
    def _input_path(*parts):
        return os.path.join(os.path.dirname(__file__), "input_data", *parts)

    @staticmethod
    def _trace(*activities, group="group"):
        trace = Trace(attributes={"concept:name": group, "AMOUNT_REQ": group})
        for activity in activities:
            trace.append(Event({"concept:name": activity}))
        return trace

    @staticmethod
    def _connect(graph, source, target):
        graph.add_flow(BPMN.SequenceFlow(source, target))

    def test_forced_ocel_20_import_variants(self):
        xml_ocel = xmlocel_importer.apply(
            self._input_path("ocel", "ocel20_example.xmlocel"),
            variant=xmlocel_importer.Variants.OCEL20,
        )
        json_ocel = jsonocel_importer.apply(
            self._input_path("ocel", "ocel20_example.jsonocel"),
            variant=jsonocel_importer.Variants.OCEL20_STANDARD,
        )

        self.assertFalse(xml_ocel.events.empty)
        self.assertFalse(xml_ocel.objects.empty)
        self.assertFalse(json_ocel.events.empty)
        self.assertFalse(json_ocel.relations.empty)
        self.assertEqual(
            set(xml_ocel.objects["ocel:type"].unique()),
            set(json_ocel.objects["ocel:type"].unique()),
        )

    def test_earth_mover_distance_implementations(self):
        first = {("A", "B"): 0.5, ("A", "C"): 0.5}
        second = {("A", "B"): 0.25, ("A", "D"): 0.75}

        slow = emd.apply(first, second, parameters={"use_fast_emd": False})
        automatic = emd.apply(first, second, parameters={"use_fast_emd": True})
        encoded_first, encoded_second = pyemd.encode_two_languages(first, second)
        direct = pyemd.EMDCalculator.emd(
            np.array([0.5, 0.5]),
            np.array([0.25, 0.75]),
            np.array([[0.0, 1.0], [1.0, 0.0]]),
        )

        self.assertGreater(slow, 0)
        self.assertAlmostEqual(slow, automatic)
        self.assertEqual(len(encoded_first), len(encoded_second))
        self.assertAlmostEqual(0.25, direct)
        with self.assertRaises(ValueError):
            pyemd.EMDCalculator.emd(
                np.array([1.0]), np.array([0.5]), np.array([[0.0]])
            )

    def test_trace_variant_privacy_variants(self):
        log = EventLog(
            [
                self._trace("A", "B", "C", group="1"),
                self._trace("A", "B", "C", group="2"),
                self._trace("A", "C", group="3"),
                self._trace("B", "C", group="4"),
            ]
        )
        random.seed(7)
        np.random.seed(7)
        parameters = {
            "epsilon": 10,
            "k": 4,
            "p": 0,
            "show_progress_bar": False,
        }

        with mock.patch.object(
            importlib.util, "find_loader", return_value=None, create=True
        ):
            laplace = trace_privacy.apply(
                log,
                variant=trace_privacy.Variants.LAPLACE,
                parameters=parameters,
            )
        sacofa = trace_privacy.apply(
            log,
            variant=trace_privacy.Variants.SACOFA,
            parameters=parameters,
        )

        self.assertFalse(laplace.empty)
        self.assertFalse(sacofa.empty)
        self.assertIn("case:concept:name", laplace.columns)

    def test_powl_objects_and_process_tree_conversion(self):
        a, b, c = Transition("A"), Transition("B"), Transition("C")
        choice = OperatorPOWL(Operator.XOR, [b, SilentTransition()])
        loop = OperatorPOWL(Operator.LOOP, [c, SilentTransition()])
        model = Sequence([a, choice, loop])

        model.validate_partial_orders()
        copied = model.copy()
        simplified = model.simplify_using_frequent_transitions()
        tree = to_process_tree.apply(model)
        net, initial_marking, final_marking = powl_to_petri.apply(model)

        self.assertTrue(model.equal_content(copied))
        self.assertIsInstance(simplified.children[1], FrequentTransition)
        self.assertIn("A", str(tree))
        self.assertTrue(net.transitions)
        self.assertTrue(initial_marking)
        self.assertTrue(final_marking)

        parallel = StrictPartialOrder([Transition("X"), Transition("Y")])
        parallel_tree = to_process_tree.apply(parallel)
        self.assertEqual(Operator.PARALLEL, parallel_tree.operator)
        with self.assertRaises(Exception):
            OperatorPOWL(Operator.XOR, [Transition("only")])

    def test_bpmn_semantics_and_gateway_reduction(self):
        graph = BPMN(process_id="main")
        start = BPMN.NormalStartEvent(id="start", process="main")
        split = BPMN.ExclusiveGateway(
            id="split",
            gateway_direction=BPMN.Gateway.Direction.DIVERGING,
            process="main",
        )
        nested = BPMN.ExclusiveGateway(
            id="nested",
            gateway_direction=BPMN.Gateway.Direction.DIVERGING,
            process="main",
        )
        tasks = [BPMN.Task(id=f"t{i}", name=f"T{i}", process="main") for i in range(3)]
        for node in [start, split, nested, *tasks]:
            graph.add_node(node)
        self._connect(graph, start, split)
        self._connect(graph, split, tasks[0])
        self._connect(graph, split, nested)
        self._connect(graph, nested, tasks[1])
        self._connect(graph, nested, tasks[2])

        marking = BPMNMarking({split: 1})
        choices = bpmn_semantics.weak_execute(split, marking, graph)
        self.assertEqual(2, len(choices))
        self.assertFalse(bpmn_semantics.is_enabled(BPMN.Task(id="outside"), graph, marking))
        self.assertEqual({split}, bpmn_semantics.enabled_nodes(graph, marking))

        before = len(graph.get_nodes())
        bpmn_reduction.apply(graph, parameters={"collapse_gateways": True})
        self.assertLess(len(graph.get_nodes()), before)
        self.assertIs(start, bpmn_utils.get_node_by_id("start", graph))
        self.assertEqual([start], bpmn_utils.get_global_start_events(graph))
        self.assertEqual(1, bpmn_utils.get_initial_marking(graph)[start])

        for gateway_class, expected_minimum in (
            (BPMN.ParallelGateway, 1),
            (BPMN.InclusiveGateway, 3),
        ):
            branch_graph = BPMN(process_id="branch")
            gateway = gateway_class(
                gateway_direction=BPMN.Gateway.Direction.DIVERGING,
                process="branch",
            )
            left = BPMN.Task(name="left", process="branch")
            right = BPMN.Task(name="right", process="branch")
            for node in (gateway, left, right):
                branch_graph.add_node(node)
            self._connect(branch_graph, gateway, left)
            self._connect(branch_graph, gateway, right)
            results = bpmn_semantics.weak_execute(
                gateway, BPMNMarking({gateway: 1}), branch_graph
            )
            self.assertGreaterEqual(len(results), expected_minimum)

        trivial = BPMN(process_id="trivial")
        source = BPMN.Task(name="source", process="trivial")
        gateway = BPMN.InclusiveGateway(process="trivial")
        target = BPMN.Task(name="target", process="trivial")
        for node in (source, gateway, target):
            trivial.add_node(node)
        self._connect(trivial, source, gateway)
        self._connect(trivial, gateway, target)
        bpmn_reduction.remove_trivial_gateways(trivial)
        self.assertNotIn(gateway, trivial.get_nodes())

    def test_deprecated_clustering_distance_utilities(self):
        logs = [
            EventLog([self._trace("A", "B", "C", group="g1")]),
            EventLog([self._trace("A", "C", group="g2")]),
            EventLog([self._trace("A", "D", "C", group="g3")]),
            EventLog([self._trace("D", "B", "C", group="g4")]),
        ]
        combined = EventLog()
        for index, log in enumerate(logs):
            for _ in range(index + 1):
                for trace in log:
                    combined.append(trace)

        variants = filter_subsets.sublog2varlist(combined, 1, 10)
        dataframe, percent_variants = filter_subsets.sublog_percent(
            combined, 1.01
        )
        _, activities = filter_subsets.sublog_percent2actlist(combined, 1.01)
        _, raw_variants = filter_subsets.sublog_percent2varlist(combined, 1.01)
        slices, frequencies = filter_subsets.logslice_percent(combined, 0.5)
        activity_slices, activity_frequencies = filter_subsets.logslice_percent_act(
            combined, 0.5
        )

        self.assertTrue(variants)
        self.assertFalse(dataframe.empty)
        self.assertTrue(percent_variants)
        self.assertTrue(activities)
        self.assertTrue(raw_variants)
        self.assertEqual(len(slices), len(frequencies))
        self.assertEqual(len(activity_slices), len(activity_frequencies))

        first_variants = filter_subsets.sublog2varlist(logs[0], 1, 10)
        second_variants = filter_subsets.sublog2varlist(logs[1], 1, 10)
        self.assertGreaterEqual(
            act_dist_calc.act_sim(
                first_variants, second_variants, logs[0], logs[1], 1, 10
            ),
            0,
        )
        self.assertGreaterEqual(
            suc_dist_calc.suc_sim(
                first_variants, second_variants, logs[0], logs[1], 1, 10
            ),
            0,
        )
        self.assertGreaterEqual(
            sim_calc.dist_calc(
                first_variants,
                second_variants,
                logs[0],
                logs[1],
                1,
                10,
                0.5,
            ),
            0,
        )

        distance_matrix = np.array(
            [
                [0.0, 0.2, 0.5, 0.8],
                [0.2, 0.0, 0.4, 0.7],
                [0.5, 0.4, 0.0, 0.3],
                [0.8, 0.7, 0.3, 0.0],
            ]
        )
        self.assertEqual(
            (3, 4), linkage_avg.linkage_avg(list(logs), distance_matrix, 0.5, 1).shape
        )
        self.assertEqual(
            (3, 4),
            linkage_avg.linkage_dfg_update(
                list(logs), distance_matrix, 0.5, 1
            ).shape,
        )
        self.assertEqual(
            (3, 4),
            linkage_avg.linkage_DMM_update(
                list(logs), distance_matrix, 0.5, 1
            ).shape,
        )
        self.assertEqual(
            (3, 4),
            linkage_avg.linkage_DMM_update_leven(
                list(logs), distance_matrix, 0.5, 1
            ).shape,
        )


if __name__ == "__main__":
    unittest.main()
