import copy
import datetime
import unittest
from collections import Counter
from unittest import mock

import numpy as np

from pm4py.objects.log.obj import Event, EventLog, Trace
from pm4py.objects.petri_net import properties
from pm4py.objects.petri_net.exporter.variants import pnml as pnml_exporter
from pm4py.objects.petri_net.importer.variants import pnml as pnml_importer
from pm4py.objects.petri_net.obj import Marking, PetriNet, ResetInhibitorNet
from pm4py.objects.petri_net.utils import (
    check_soundness,
    decomposition,
    performance_map,
    petri_utils,
    reduction,
)
from pm4py.objects.random_variables import random_variable
from pm4py.objects.stochastic_petri import ctmc
from pm4py.objects.transition_system.obj import TransitionSystem
from pm4py.util import constants


class PetriStochasticSerializationCoverageTest(unittest.TestCase):
    @staticmethod
    def _series_net(labels=("A", "B")):
        net = PetriNet("series")
        p0, p1, p2 = (PetriNet.Place(name) for name in ("p0", "p1", "p2"))
        a = PetriNet.Transition("a", labels[0])
        b = PetriNet.Transition("b", labels[1])
        net.places.update({p0, p1, p2})
        net.transitions.update({a, b})
        for source, target in ((p0, a), (a, p1), (p1, b), (b, p2)):
            petri_utils.add_arc_from_to(source, target, net)
        return net, Marking({p0: 1}), Marking({p2: 1}), (p0, p1, p2), (a, b)

    @staticmethod
    def _rv(kind="EXPONENTIAL", parameters_string="0.5"):
        value = random_variable.RandomVariable()
        value.read_from_string(kind, parameters_string)
        value.set_priority(3)
        value.set_weight(2.5)
        return value

    def test_random_variable_facade_and_distribution_selection(self):
        uninitialized = random_variable.RandomVariable()
        self.assertEqual(str(uninitialized), "UNINITIALIZED")
        self.assertEqual(repr(uninitialized), "UNINITIALIZED")
        self.assertIsNone(uninitialized.get_distribution_type())
        self.assertIsNone(uninitialized.get_transition_type())
        self.assertIsNone(uninitialized.get_distribution_parameters())
        self.assertIsNone(uninitialized.calculate_loglikelihood([1, 2]))
        self.assertIsNone(uninitialized.get_value())
        self.assertIsNone(uninitialized.get_values(2))
        self.assertIsNone(uninitialized.get_weight())
        self.assertIsNone(uninitialized.get_priority())
        uninitialized.set_weight(1)
        uninitialized.set_priority(1)

        specifications = (
            ("NORMAL", "1;2"),
            ("UNIFORM", "0;3"),
            ("EXPONENTIAL", "0.5"),
            ("LOGNORMAL", "1;0;2"),
            ("GAMMA", "2;0;1"),
            ("DETERMINISTIC", "4"),
            ("IMMEDIATE", None),
        )
        for kind, parameters_string in specifications:
            with self.subTest(kind=kind):
                rv = random_variable.RandomVariable()
                rv.read_from_string(kind, parameters_string)
                self.assertEqual(rv.get_distribution_type(), kind)
                self.assertIsNotNone(rv.get_transition_type())
                self.assertIsNotNone(rv.get_distribution_parameters())
                rv.set_weight(2.0)
                rv.set_priority(4)
                self.assertEqual(rv.get_weight(), 2.0)
                self.assertEqual(rv.get_priority(), 4)
                self.assertIsNotNone(str(rv))
                self.assertIsNotNone(repr(rv))
                if kind in {"NORMAL", "UNIFORM", "EXPONENTIAL", "LOGNORMAL", "GAMMA"}:
                    rv.calculate_parameters([1.0, 2.0, 3.0])
                self.assertEqual(len(rv.get_values(2)), 2)

        existing = self._rv()
        existing.calculate_parameters([1.0, 2.0, 3.0])
        self.assertIsInstance(existing.calculate_loglikelihood([1.0, 2.0]), float)

        inferred = random_variable.RandomVariable()
        inferred.calculate_parameters([1.0, 1.5, 2.0], {"debug": True})
        self.assertIsNotNone(inferred.random_variable)
        forced = random_variable.RandomVariable()
        forced.calculate_parameters([1.0, 2.0], force_distribution="EXPONENTIAL")
        self.assertEqual(forced.get_distribution_type(), "EXPONENTIAL")
        zero = random_variable.RandomVariable()
        zero.calculate_parameters([], force_distribution="EXPONENTIAL")
        self.assertEqual(zero.get_distribution_type(), "IMMEDIATE")
        for kind in ("NORMAL", "UNIFORM"):
            selected = random_variable.RandomVariable()
            selected.calculate_parameters([1.0, 2.0, 3.0], force_distribution=kind)
            self.assertEqual(selected.get_distribution_type(), kind)

    def test_rich_pnml_export_import_stochastic_data_layout_and_special_arcs(self):
        net = ResetInhibitorNet("rich")
        p0, p1, p2 = (PetriNet.Place(name) for name in ("p0", "p1", "p2"))
        p0.properties[constants.PLACE_NAME_TAG] = "Start"
        p0.properties[constants.LAYOUT_INFORMATION_PETRI] = ((1.0, 2.0), (3.0, 4.0))
        visible = PetriNet.Transition("visible", "A+start")
        silent = PetriNet.Transition("silent", None)
        visible.properties[constants.LAYOUT_INFORMATION_PETRI] = ((5.0, 6.0), (7.0, 8.0))
        visible.properties[constants.STOCHASTIC_DISTRIBUTION] = self._rv()
        visible.properties[properties.TRANS_GUARD] = "x > 0"
        visible.properties[properties.READ_VARIABLE] = ["x", "y"]
        visible.properties[properties.WRITE_VARIABLE] = ["z"]
        silent.properties[constants.STOCHASTIC_DISTRIBUTION] = self._rv("IMMEDIATE", None)
        net.places.update({p0, p1, p2})
        net.transitions.update({visible, silent})
        reset_arc = petri_utils.add_arc_from_to(
            p0, visible, net, weight=2, type=properties.RESET_ARC
        )
        reset_arc.properties["custom"] = "value"
        petri_utils.add_arc_from_to(visible, p1, net)
        petri_utils.add_arc_from_to(
            p1, silent, net, type=properties.INHIBITOR_ARC
        )
        petri_utils.add_arc_from_to(silent, p2, net)
        net.properties[properties.VARIABLES] = [
            {"type": "java.lang.Integer", "name": "x"},
            {"type": "java.lang.String", "name": "z"},
        ]
        initial = Marking({p0: 2})
        final = Marking({p2: 1})

        standard = pnml_exporter.export_petri_as_string(net, initial, final)
        prom5 = pnml_exporter.export_petri_as_string(
            net, initial, final, export_prom5=True
        )
        self.assertIn(b"StochasticPetriNet", standard)
        self.assertIn(b"logevent", prom5)
        imported, imported_im, imported_fm, stochastic = pnml_importer.import_net_from_string(
            standard,
            {pnml_importer.Parameters.RETURN_STOCHASTIC_MAP: True},
        )
        self.assertEqual(sum(imported_im.values()), 2)
        self.assertEqual(sum(imported_fm.values()), 1)
        self.assertEqual(len(stochastic), 2)
        self.assertEqual(len(imported.properties[properties.VARIABLES]), 2)
        self.assertTrue(any(properties.TRANS_GUARD in t.properties for t in imported.transitions))
        self.assertTrue(any(constants.LAYOUT_INFORMATION_PETRI in p.properties for p in imported.places))
        self.assertIsInstance(imported, ResetInhibitorNet)

        # The importer also accepts legacy PNML files that place nodes directly
        # under <net>, without a <page> wrapper.
        legacy = b"""<pnml><net id='legacy'>
            <place id='p0'><initialMarking><text>1</text></initialMarking></place>
            <place id='p1'/><transition id='t'><name><text>A</text></name></transition>
            <arc id='a1' source='p0' target='t'/><arc id='a2' source='t' target='p1'/>
        </net></pnml>"""
        imported_prom, prom_im, prom_fm = pnml_importer.import_net_from_string(legacy)
        self.assertEqual(len(imported_prom.transitions), 1)
        self.assertEqual(sum(prom_im.values()), 1)
        self.assertEqual(sum(prom_fm.values()), 1)

        without_final = pnml_exporter.export_petri_as_string(net, initial)
        guessed = pnml_importer.import_net_from_string(without_final)
        self.assertEqual(len(guessed), 3)
        no_guess = pnml_importer.import_net_from_string(
            without_final,
            {pnml_importer.Parameters.AUTO_GUESS_FINAL_MARKING: False},
        )
        self.assertIsNone(no_guess[2])

    def test_workflow_soundness_positive_negative_and_structural_conditions(self):
        net, initial, final, places, _ = self._series_net()
        self.assertIs(check_soundness.check_source_place_presence(net), places[0])
        self.assertIs(check_soundness.check_sink_place_presence(net), places[2])
        self.assertTrue(
            check_soundness.check_source_and_sink_reachability(net, places[0], places[2])
        )
        self.assertTrue(check_soundness.check_wfnet(net))
        self.assertTrue(check_soundness.check_source_sink_place_conditions(net))
        self.assertTrue(
            check_soundness.check_easy_soundness_net_in_fin_marking(net, initial, final)
        )
        self.assertTrue(check_soundness.check_easy_soundness_of_wfnet(net))

        disconnected = copy.deepcopy(net)
        disconnected.places.add(PetriNet.Place("orphan"))
        self.assertIsNone(check_soundness.check_source_place_presence(disconnected))
        self.assertIsNone(check_soundness.check_sink_place_presence(disconnected))
        self.assertFalse(check_soundness.check_wfnet(disconnected))
        self.assertFalse(
            check_soundness.check_source_and_sink_reachability(disconnected, None, None)
        )

        source_net = PetriNet("source fan-in")
        s, helper, sink = (PetriNet.Place(x) for x in ("s", "helper", "sink"))
        prepare = PetriNet.Transition("prepare", "prepare")
        join = PetriNet.Transition("join", "join")
        source_net.places.update({s, helper, sink})
        source_net.transitions.update({prepare, join})
        for edge in ((s, prepare), (prepare, helper), (s, join), (helper, join), (join, sink)):
            petri_utils.add_arc_from_to(*edge, source_net)
        self.assertFalse(check_soundness.check_source_sink_place_conditions(source_net))

        sink_net = PetriNet("sink fan-out")
        s, helper, sink = (PetriNet.Place(x) for x in ("s", "helper", "sink"))
        split = PetriNet.Transition("split", "split")
        finish = PetriNet.Transition("finish", "finish")
        sink_net.places.update({s, helper, sink})
        sink_net.transitions.update({split, finish})
        for edge in ((s, split), (split, sink), (split, helper), (helper, finish), (finish, sink)):
            petri_utils.add_arc_from_to(*edge, sink_net)
        self.assertFalse(check_soundness.check_source_sink_place_conditions(sink_net))

        with mock.patch.object(check_soundness.explore_path, "__search", side_effect=RuntimeError):
            self.assertFalse(
                check_soundness.check_easy_soundness_net_in_fin_marking(net, initial, final)
            )

    def test_decomposition_component_creation_merge_and_sublist(self):
        net = PetriNet("decomposition")
        p0, p1, p2, p3 = (PetriNet.Place("p%d" % i) for i in range(4))
        a1 = PetriNet.Transition("a1", "A")
        a2 = PetriNet.Transition("a2", "A")
        tau = PetriNet.Transition("tau", None)
        b = PetriNet.Transition("b", "B")
        net.places.update({p0, p1, p2, p3})
        net.transitions.update({a1, a2, tau, b})
        for edge in (
            (p0, a1), (a1, p1), (p1, tau), (tau, p2),
            (p2, a2), (a2, p3), (p0, b), (b, p3),
        ):
            petri_utils.add_arc_from_to(*edge, net)
        components = decomposition.decompose(net, Marking({p0: 1}), Marking({p3: 1}))
        self.assertGreaterEqual(len(components), 1)
        first = components[0]
        merged = decomposition.merge_comp(first, first)
        self.assertTrue(merged[0].places)
        self.assertTrue(hasattr(merged[0], "lvis_labels"))
        merged_list = decomposition.merge_sublist_nets([first, first, first])
        self.assertTrue(merged_list[0].transitions)

    def test_ctmc_colors_q_matrix_transient_nullspace_and_steady_state(self):
        expected = "0123456789ABCDEF"
        self.assertEqual("".join(ctmc.get_corr_hex(i) for i in range(16)), expected)

        transition_system = TransitionSystem("two states")
        first = TransitionSystem.State("s0")
        second = TransitionSystem.State("s1")
        forward = TransitionSystem.Transition("forward", first, second)
        backward = TransitionSystem.Transition("backward", second, first)
        first.outgoing.add(forward)
        second.incoming.add(forward)
        second.outgoing.add(backward)
        first.incoming.add(backward)
        transition_system.states.update({first, second})
        transition_system.transitions.update({forward, backward})

        model_forward = PetriNet.Transition("forward", "F")
        model_backward = PetriNet.Transition("backward", "B")
        stochastic = {
            model_forward: self._rv("EXPONENTIAL", "0.5"),
            model_backward: self._rv("EXPONENTIAL", "0.25"),
        }
        q_matrix = ctmc.get_q_matrix_from_tangible_exponential(
            transition_system, stochastic
        )
        self.assertEqual(q_matrix.shape, (2, 2))
        self.assertTrue(np.allclose(q_matrix.sum(axis=1), 0))
        transient = ctmc.transient_analysis_from_tangible_q_matrix_and_single_state(
            transition_system, q_matrix, first, 2.0
        )
        self.assertAlmostEqual(sum(transient.values()), 1.0)
        vector_transient = ctmc.transient_analysis_from_tangible_q_matrix_and_states_vector(
            transition_system, q_matrix, np.array([[0.5, 0.5]]), 1.0
        )
        self.assertAlmostEqual(sum(vector_transient.values()), 1.0)
        colors = ctmc.get_color_from_probabilities(vector_transient)
        self.assertEqual(set(colors), {first, second})
        self.assertEqual(ctmc.nullspace(q_matrix.T).shape[0], 2)
        steady = ctmc.perform_steadystate(q_matrix, transition_system)
        self.assertEqual(len(steady), 2)
        no_steady = ctmc.perform_steadystate(np.eye(2), transition_system)
        self.assertIsInstance(no_steady, Counter)

        dfg_graph, tangible, stochastic_map, dfg_q = (
            ctmc.get_tangible_reachability_and_q_matrix_from_dfg_performance(
                {("A", "B"): 2.0},
                parameters={"start_activities": {"A": 1}, "end_activities": {"B": 1}},
            )
        )
        self.assertIs(dfg_graph, tangible)
        self.assertEqual(dfg_q.shape[0], len(tangible.states))
        self.assertTrue(stochastic_map)

    def test_performance_annotations_statistics_aggregation_and_case_filter(self):
        net, initial, final, _, transitions = self._series_net()
        start = datetime.datetime(2024, 1, 1, 8, tzinfo=datetime.timezone.utc)
        trace = Trace(
            [
                Event({"concept:name": "A", "time:timestamp": start}),
                Event({"concept:name": "B", "time:timestamp": start + datetime.timedelta(seconds=5)}),
            ]
        )
        annotations, arc_annotations = performance_map.calculate_annotation_for_trace(
            trace, net, initial, list(transitions), "concept:name", ht_perf_method="first"
        )
        self.assertIn(transitions[0], annotations)
        self.assertTrue(arc_annotations)

        variants = {("A", "B"): [0]}
        aligned = [{"activated_transitions": [transitions[0], transitions[0], transitions[1]]}]
        statistics = performance_map.single_element_statistics(
            EventLog([trace]),
            net,
            initial,
            aligned,
            variants,
            parameters={"count_once_per_trace": True, "business_hours": True},
        )
        self.assertTrue(statistics)

        missing_time = Trace([Event({"concept:name": "A"}), Event({"concept:name": "B"})])
        zero_statistics = performance_map.single_element_statistics(
            EventLog([missing_time]),
            net,
            initial,
            [{"activated_transitions": list(transitions)}],
            variants,
        )
        self.assertTrue(zero_statistics)

        stats = {
            transitions[0]: {"count": 2, "performance": [1.0, 3.0]},
            transitions[1]: {"count": 5, "performance": [2.0, 4.0]},
        }
        for arc in net.arcs:
            stats[arc] = {"count": 1 + len(stats), "performance": [1.0, 2.0, 4.0]}
        self.assertEqual(performance_map.find_min_max_trans_frequency(stats), (2, 5))
        self.assertGreater(performance_map.find_min_max_arc_frequency(stats)[1], 0)
        for aggregation in (None, "mean", "median", "stdev", "sum", "min", "max"):
            self.assertGreaterEqual(
                performance_map.aggregate_stats(stats, next(iter(net.arcs)), aggregation), 0
            )
        self.assertGreaterEqual(
            performance_map.find_min_max_arc_performance(stats, "mean")[1], 0
        )
        self.assertTrue(performance_map.aggregate_statistics(stats, measure="frequency"))
        self.assertTrue(
            performance_map.aggregate_statistics(
                stats, measure="performance", aggregation_measure="median"
            )
        )

        transition_performance = {
            str(transitions[0]): {
                "case_association": {0: [2.0], 1: [0.5]},
                "all_values": [0.5, 2.0],
            }
        }
        log = EventLog([trace, trace])
        indices = performance_map.get_idx_exceeding_specified_acti_performance(
            log, transition_performance, str(transitions[0]), 1.0
        )
        self.assertEqual(indices, [0])
        filtered = performance_map.filter_cases_exceeding_specified_acti_performance(
            log, transition_performance, str(transitions[0]), 1.0
        )
        self.assertEqual(len(filtered), 1)
        measured = performance_map.get_transition_performance_with_token_replay(
            EventLog([trace]), net, initial, final
        )
        self.assertIsInstance(measured, dict)

    def test_remaining_reset_inhibitor_reduction_rules(self):
        # Parallel places share exactly the same preset and postset.
        parallel = PetriNet("parallel places")
        source, p, q, sink = (PetriNet.Place(x) for x in ("source", "p", "q", "sink"))
        split = PetriNet.Transition("split", None)
        join = PetriNet.Transition("join", None)
        parallel.places.update({source, p, q, sink})
        parallel.transitions.update({split, join})
        for edge in ((source, split), (split, p), (split, q), (p, join), (q, join), (join, sink)):
            petri_utils.add_arc_from_to(*edge, parallel)
        reduction.apply_fpp_rule(parallel)
        self.assertEqual(len(parallel.places), 3)

        loop_net = PetriNet("loop place")
        loop_place = PetriNet.Place("loop")
        loop_transition = PetriNet.Transition("loop transition", "A")
        loop_net.places.add(loop_place)
        loop_net.transitions.add(loop_transition)
        petri_utils.add_arc_from_to(loop_place, loop_transition, loop_net)
        petri_utils.add_arc_from_to(loop_transition, loop_place, loop_net)
        reduction.apply_elp_rule(loop_net, Marking({loop_place: 1}))
        self.assertNotIn(loop_place, loop_net.places)

        reset_net = ResetInhibitorNet("reset and inhibitor")
        place = PetriNet.Place("p")
        transition = PetriNet.Transition("t")
        reset_net.places.add(place)
        reset_net.transitions.add(transition)
        reset_arc = petri_utils.add_arc_from_to(
            place, transition, reset_net, type=properties.RESET_ARC
        )
        inhibitor_arc = petri_utils.add_arc_from_to(
            place, transition, reset_net, type=properties.INHIBITOR_ARC
        )
        # The reduction implementation exposes this historical public field.
        reset_arc.arc_type = properties.RESET_ARC
        inhibitor_arc.arc_type = properties.INHIBITOR_ARC
        reduction.apply_r_rule(reset_net)
        self.assertEqual(len(transition.in_arcs), 1)

        series, im, fm, _, _ = self._series_net(labels=(None, "B"))
        reduction.apply_fsp_rule(series)
        reduced, reduced_im, reduced_fm = reduction.apply_reset_inhibitor_net_reduction(
            *self._series_net(labels=(None, "B"))[:3]
        )
        self.assertIsInstance(reduced, PetriNet)
        self.assertIsInstance(reduced_im, Marking)
        self.assertIsInstance(reduced_fm, Marking)


if __name__ == "__main__":
    unittest.main()
